"""Producer-free replay of the positive promoted-model campaign directory.

This module imports neither the positive campaign nor its occurrence/stage
producers.  It independently validates the positive model/plan bytes, replays
the five owner-bound stage documents, reconstructs all nine shared receipts,
the 202-record abstract-only WorkVector, its eight-axis projection, physical
output fixed-point equality, the occurrence bundle, and the three campaign
denominators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    derive_comparison_vector_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_positive_promoted_overlay_independent_verifier_v1 as positive_verifier_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_positive_promoted_campaign_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("positive campaign independent domain is not central")

OUTPUT_ROLES = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
SHARED_PATHS = shared_v1.SHARED_RESOURCE_PATHS
STAGE_KINDS = (
    "PREOPEN_COMMON_PREFIX",
    "INITIAL_ACQUISITION",
    "INITIAL_MODEL_BUILD",
    "OPEN_CHECKPOINT_REPLANNING",
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION",
)
INTEGRITY_OBLIGATIONS = (
    "typed-positive-input-identity-graph",
    "v6-profile-chain",
    "open-boundary-manifest",
    "operational-plan-byte-identity",
    "five-stage-event-replay",
    "route-reconciliation",
)
PROTOCOL_OBLIGATIONS = (
    "single-owner-accounting-scope",
    "promoted-model-reuse-before-planning",
    "one-fresh-planner-call",
    "no-operational-exact-lift-replay",
    "abstract-route-family-exclusivity",
)


class ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
    RuntimeError
):
    """The committed positive campaign bytes do not replay exactly."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _exact(document: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != keys:
        _fail(f"{label} field set changed")
    return document


def _read_canonical(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        info = path.stat()
        raw = path.read_bytes()
    except OSError as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            f"{label} is unreadable"
        ) from error
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or not raw
    ):
        _fail(f"{label} is not one private regular file")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _content_document(
    document: dict[str, Any], *, id_field: str, domain: str, label: str
) -> tuple[str, dict[str, Any]]:
    if id_field not in document:
        _fail(f"{label} content ID is absent")
    payload = dict(document)
    observed = _cid(payload.pop(id_field), f"{label} content ID")
    if content_id(domain, payload) != observed:
        _fail(f"{label} content ID mismatch")
    return observed, payload


def _verify_preregistration(
    document: dict[str, Any],
    *,
    positive: positive_verifier_v1.PositivePromotedOverlayIndependentVerificationV1,
    positive_document: dict[str, Any],
    expected_id: str,
) -> str:
    query = positive_document["fresh_query"]
    expected_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_campaign_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.118",
        "profile_key": "construction_k7_positive_promoted_campaign_v1",
        "logical_occurrence_specs": [
            {
                "occurrence_id": query["logical_occurrence_id"],
                "query_ordinal": query["query_ordinal"],
                "threshold_profile_id": query["threshold_profile_id"],
                "positive_promoted_overlay_result_id": positive.result_id,
                "promoted_epoch_id": positive.epoch_id,
                "promoted_model_id": positive.numerical_model_id,
                "fresh_query_id": positive.query_id,
                "fresh_plan_id": positive.plan_id,
                "expected_route_kind": "ABSTRACT_ONLY_CERTIFICATE",
                "expected_terminal_class": "PLAN_CERTIFICATE",
                "expected_terminal_code": "ABSTRACT_CERTIFIED",
            }
        ],
        "registered_logical_occurrence_count": 1,
        "preregistration_committed_before_planner_execution": True,
        "denominator_row_deletion_allowed": False,
        "rebuild_allowed": False,
        "max_route_attempts_per_logical_occurrence": 1,
        "official_execution_allowed": False,
    }
    observed, payload = _content_document(
        document,
        id_field="campaign_preregistration_id",
        domain=CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
        label="positive campaign preregistration",
    )
    if payload != expected_payload or observed != _cid(expected_id, "expected preregistration"):
        _fail("positive campaign preregistration differs from independent replay")
    return observed


def _replay_stage_trace(
    trace_document: dict[str, Any],
    *,
    positive_result_id: str,
    occurrence_id: str,
) -> tuple[
    str,
    int,
    tuple[live_v3.RecordedStageWorkV3, ...],
    Any,
    Any,
    Any,
]:
    _exact(
        trace_document,
        {
            "artifact_role",
            "schema",
            "schema_version",
            "profile_key",
            "positive_promoted_stage_accounting",
            "independent_evaluation_replay_included",
        },
        "positive operational trace",
    )
    if (
        trace_document["artifact_role"] != "OPERATIONAL_TRACE"
        or trace_document["schema"]
        != "acfqp.construction_k7_positive_promoted_operational_trace.v1"
        or trace_document["independent_evaluation_replay_included"] is not False
    ):
        _fail("positive operational trace locks changed")
    stage_document = trace_document["positive_promoted_stage_accounting"]
    if type(stage_document) is not dict:
        _fail("positive stage accounting is absent")
    payload = dict(stage_document)
    try:
        stage_id = _cid(
            payload.pop("positive_promoted_stage_accounting_id"),
            "positive stage accounting",
        )
        stage_documents = payload.pop("recorded_stages")
    except KeyError as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            "positive stage accounting graph is incomplete"
        ) from error
    if content_id(CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN, payload) != stage_id:
        _fail("positive stage-accounting content ID mismatch")
    if (
        payload.get("positive_promoted_overlay_result_id") != positive_result_id
        or payload.get("logical_occurrence_id") != occurrence_id
        or payload.get("stage_plan") != list(STAGE_KINDS)
        or payload.get("stage_local_counter_record_count") != 1_010
        or payload.get("named_integrity_obligations") != list(INTEGRITY_OBLIGATIONS)
        or payload.get("named_protocol_obligations") != list(PROTOCOL_OBLIGATIONS)
        or type(payload.get("business_hash_invocations")) is not int
        or payload["business_hash_invocations"] <= 0
        or payload.get("fresh_planner_called_exactly_once") is not True
        or payload.get("promoted_model_reused_without_rebuild") is not True
        or payload.get("fresh_ground_or_observer_event_count") != 0
        or payload.get("local_fallback_rebuild_native_zero") is not True
        or payload.get("nine_shared_paths_are_stage_placeholders") is not True
        or payload.get("shared_resource_receipts_issued") is not False
        or payload.get("occurrence_work_vector_issued") is not False
        or payload.get("official_execution_allowed") is not False
    ):
        _fail("positive stage-accounting claim or obligation changed")
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry, comparison_profile
    )
    if (
        payload.get("counter_registry_id") != registry.registry_id
        or payload.get("stage_profile_id") != stage_profile.stage_profile_id
        or payload.get("comparison_profile_id")
        != comparison_profile.comparison_profile_id
        or payload.get("actual_projection_profile_id")
        != actual_profile.actual_projection_profile_id
        or type(stage_documents) is not list
        or len(stage_documents) != 5
    ):
        _fail("positive stage profile chain changed")
    stages = tuple(
        live_v3.RecordedStageWorkV3.from_document(
            row,
            registry,
            stage_profile,
            comparison_profile,
            actual_profile,
        )
        for row in stage_documents
    )
    if (
        tuple(row.stage_start.stage_kind.value for row in stages) != STAGE_KINDS
        or any(row.work_vector.subject_id != occurrence_id for row in stages)
        or any(
            row.work_vector.values[path] != 0
            for row in stages
            for path in SHARED_PATHS
        )
        or payload.get("stage_work_vector_ids")
        != [row.work_vector.work_vector_id for row in stages]
        or payload.get("stage_comparison_vector_ids")
        != [row.comparison_vector.comparison_vector_id for row in stages]
        or payload.get("stage_projection_proof_ids")
        != [row.actual_projection_proof.actual_projection_proof_id for row in stages]
    ):
        _fail("positive five-stage transcript changed")
    return (
        stage_id,
        payload["business_hash_invocations"],
        stages,
        registry,
        comparison_profile,
        actual_profile,
    )


def _verify_occurrence(
    occurrence_directory: Path,
    *,
    positive_result_bytes: bytes,
    positive: positive_verifier_v1.PositivePromotedOverlayIndependentVerificationV1,
    positive_document: dict[str, Any],
    embedded_bundle: dict[str, Any],
    embedded_fixed: dict[str, Any],
    embedded_commit: dict[str, Any],
) -> dict[str, Any]:
    if (
        occurrence_directory.is_symlink()
        or not occurrence_directory.is_dir()
        or stat.S_IMODE(occurrence_directory.stat().st_mode) & 0o077
        or {path.name for path in occurrence_directory.iterdir()}
        != {f"{role}.json" for role in OUTPUT_ROLES}
    ):
        _fail("positive occurrence output inventory changed")
    role_raw: dict[str, bytes] = {}
    role_docs: dict[str, dict[str, Any]] = {}
    for role in OUTPUT_ROLES:
        raw, document = _read_canonical(
            occurrence_directory / f"{role}.json", f"positive role {role}"
        )
        if document.get("artifact_role") != role:
            _fail(f"positive role {role} relabelled itself")
        role_raw[role] = raw
        role_docs[role] = document
    output_bytes = sum(len(raw) for raw in role_raw.values())
    manifest = role_docs["OUTPUT_MANIFEST"]
    if (
        manifest.get("required_role_order") != list(OUTPUT_ROLES)
        or manifest.get("io.output_bytes") != output_bytes
        or manifest.get("ordered_preceding_roles")
        != [
            {
                "artifact_role": role,
                "byte_count": len(role_raw[role]),
                "bytes_sha256": hashlib.sha256(role_raw[role]).hexdigest(),
            }
            for role in OUTPUT_ROLES[:-1]
        ]
    ):
        _fail("positive output manifest or fixed-point equality changed")

    query = positive_document["fresh_query"]
    occurrence_id = query["logical_occurrence_id"]
    business = role_docs["BUSINESS_RESULT"]
    expected_business = {
        "artifact_role": "BUSINESS_RESULT",
        "schema": "acfqp.construction_k7_positive_promoted_business_result.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
        "occurrence_id": occurrence_id,
        "positive_promoted_overlay_result_id": positive.result_id,
        "promoted_epoch_id": positive.epoch_id,
        "fresh_query_id": positive.query_id,
        "fresh_abstract_plan_id": positive.plan_id,
        "fresh_numerical_proof_id": positive.numerical_proof_id,
        "exact_lift_binding_id": positive.exact_lift_binding_id,
        "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "fresh_ground_or_observer_event_count": 0,
        "construction_only": True,
        "official_execution_allowed": False,
    }
    if business != expected_business:
        _fail("positive business result changed")
    (
        stage_id,
        business_hashes,
        stages,
        registry,
        comparison_profile,
        actual_profile,
    ) = _replay_stage_trace(
        role_docs["OPERATIONAL_TRACE"],
        positive_result_id=positive.result_id,
        occurrence_id=occurrence_id,
    )

    counter = role_docs["COUNTER_RECORD_SET"]
    measurement = counter.get("shared_measurement")
    if type(measurement) is not dict:
        _fail("positive shared measurement is absent")
    measurement_id, measurement_payload = _content_document(
        measurement,
        id_field="shared_measurement_id",
        domain=CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_MEASUREMENT_V1_DOMAIN,
        label="positive shared measurement",
    )
    if (
        measurement_payload.get("occurrence_id") != occurrence_id
        or measurement_payload.get("positive_promoted_overlay_result_id")
        != positive.result_id
        or measurement_payload.get("positive_promoted_stage_accounting_id")
        != stage_id
        or measurement_payload.get("input_bytes_sha256")
        != hashlib.sha256(positive_result_bytes).hexdigest()
        or measurement_payload.get("io.read_bytes") != len(positive_result_bytes)
        or measurement_payload.get("common.hash_invocations") != business_hashes
        or measurement_payload.get("common.integrity_checks")
        != len(INTEGRITY_OBLIGATIONS)
        or measurement_payload.get("common.protocol_checks")
        != len(PROTOCOL_OBLIGATIONS)
        or measurement_payload.get("pre_output_mounted_bytes")
        != len(positive_result_bytes)
        or type(measurement_payload.get("pre_output_working_bytes_peak")) is not int
        or measurement_payload["pre_output_working_bytes_peak"] <= 0
        or measurement_payload.get("io.staged_bytes") != 0
        or measurement_payload.get("process.launches") != 0
        or measurement_payload.get("complete_window_closed") is not True
        or measurement_payload.get("official_execution_allowed") is not False
    ):
        _fail("positive shared measurement changed")

    renderer_id = content_id(
        CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_RENDERER_V1_DOMAIN,
        {
            "positive_promoted_stage_accounting_id": stage_id,
            "shared_measurement_id": measurement_id,
            "required_roles": list(OUTPUT_ROLES),
        },
    )
    fixed_profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=stage_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={role: 256 * 1024 * 1024 for role in OUTPUT_ROLES},
        max_iterations=32,
    )
    if manifest.get("output_bytes_fixed_point_profile_id") != fixed_profile.profile_id:
        _fail("positive output renderer/profile identity changed")

    records_by_path = tuple(
        {record.path: record for record in row.work_vector.records} for row in stages
    )
    shared_values = {
        "common.hash_invocations": business_hashes,
        "common.integrity_checks": len(INTEGRITY_OBLIGATIONS),
        "common.protocol_checks": len(PROTOCOL_OBLIGATIONS),
        "io.mounted_bytes_peak": len(positive_result_bytes) + output_bytes,
        "io.output_bytes": output_bytes,
        "io.read_bytes": len(positive_result_bytes),
        "io.staged_bytes": 0,
        "memory.working_bytes_peak": max(
            measurement_payload["pre_output_working_bytes_peak"],
            len(positive_result_bytes) + output_bytes,
        ),
        "process.launches": 0,
    }
    receipt_documents: list[dict[str, Any]] = []
    receipt_ids: list[str] = []
    for path in SHARED_PATHS:
        payload = {
            "schema": "acfqp.construction_k7_positive_promoted_shared_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
            "occurrence_id": occurrence_id,
            "shared_measurement_id": measurement_id,
            "path": path,
            "reducer": registry.by_path[path].reducer.value,
            "value": shared_values[path],
            "source_kind": (
                "OUTPUT_FIXED_POINT" if path == "io.output_bytes" else "COMPLETE_WINDOW_MEASUREMENT"
            ),
            "source_evidence_id": (
                fixed_profile.profile_id if path == "io.output_bytes" else measurement_id
            ),
            "stage_placeholder_record_ids": [
                rows[path].record_id for rows in records_by_path
            ],
            "output_fixed_point_profile_id": (
                fixed_profile.profile_id if path == "io.output_bytes" else None
            ),
            "stage_placeholders_replaced_not_summed": True,
            "official_execution_allowed": False,
        }
        receipt_id = content_id(
            CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_V1_DOMAIN, payload
        )
        receipt_ids.append(receipt_id)
        receipt_documents.append({**payload, "shared_resource_receipt_id": receipt_id})
    receipt_set_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_shared_receipt_set.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
        "occurrence_id": occurrence_id,
        "shared_measurement_id": measurement_id,
        "shared_resource_paths": list(SHARED_PATHS),
        "shared_resource_receipt_ids": receipt_ids,
        "receipt_count": 9,
        "all_nine_shared_paths_complete": True,
        "official_execution_allowed": False,
    }
    receipt_set_id = content_id(
        CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_SET_V1_DOMAIN,
        receipt_set_payload,
    )
    receipt_set_document = {
        **receipt_set_payload,
        "shared_resource_receipt_set_id": receipt_set_id,
    }
    if (
        counter.get("shared_resource_receipts") != receipt_documents
        or counter.get("shared_resource_receipt_set") != receipt_set_document
    ):
        _fail("positive nine-receipt set changed")

    receipt_by_path = dict(zip(SHARED_PATHS, zip(receipt_ids, shared_values.values()), strict=True))
    aggregation_documents: list[dict[str, Any]] = []
    aggregation_ids: list[str] = []
    expected_values: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        stage_records = tuple(rows[path] for rows in records_by_path)
        if path in receipt_by_path:
            source_id, value = receipt_by_path[path]
            source_kind = "SHARED_RECEIPT"
        elif leaf.reducer is ReducerEnum.SUM:
            value = sum(row.value for row in stage_records)
            source_id = stage_id
            source_kind = "STAGE_SUM"
        else:
            value = max(row.value for row in stage_records)
            source_id = stage_id
            source_kind = "STAGE_MAX"
        payload = {
            "schema": "acfqp.construction_k7_positive_promoted_path_aggregation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
            "occurrence_id": occurrence_id,
            "path": path,
            "reducer": leaf.reducer.value,
            "value": value,
            "stage_record_ids": [row.record_id for row in stage_records],
            "source_kind": source_kind,
            "source_evidence_id": source_id,
            "shared_stage_placeholders_replaced_not_summed": path in SHARED_PATHS,
        }
        aggregation_id = content_id(
            CONSTRUCTION_K7_POSITIVE_PROMOTED_PATH_AGGREGATION_V1_DOMAIN, payload
        )
        aggregation_ids.append(aggregation_id)
        aggregation_documents.append({**payload, "path_aggregation_id": aggregation_id})
        expected_values[path] = value
    if counter.get("path_aggregations") != aggregation_documents:
        _fail("positive 202-path aggregation changed")

    work_artifact = role_docs["WORK_VECTOR"]
    comparison_artifact = role_docs["COMPARISON_VECTOR"]
    proof_artifact = role_docs["ACTUAL_PROJECTION_PROOF"]
    try:
        vector = WorkVectorV1.from_dict(work_artifact["work_vector"], registry)
        comparison = ComparisonVectorV1.from_dict(
            comparison_artifact["comparison_vector"]
        )
        proof = ActualProjectionProofV1.from_dict(
            proof_artifact["actual_projection_proof"]
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            "positive formal accounting artifact failed typed replay"
        ) from error
    derived = derive_comparison_vector_v1(vector, registry, comparison_profile)
    verify_actual_projection_v1(
        proof, vector, comparison, registry, comparison_profile, actual_profile
    )
    if (
        vector.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        or vector.subject_id != occurrence_id
        or len(vector.records) != 202
        or vector.values != expected_values
        or comparison != derived
        or proof.work_scope is not ActualWorkScope.COMMON_PREFIX
        or proof.source_lane is not LaneEnum.OPERATIONAL
        or proof.projection_term_count != 182
        or counter.get("counter_record_count") != 202
        or counter.get("counter_records") != [row.to_dict() for row in vector.records]
        or any(
            value != 0
            for path, value in vector.values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )
    ):
        _fail("positive formal abstract-only accounting chain changed")
    if (
        work_artifact
        != {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.construction_k7_positive_promoted_work_vector_artifact.v1",
            "io.output_bytes": output_bytes,
            "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
            "local_fallback_rebuild_native_zero": True,
            "work_vector": vector.to_dict(),
        }
        or comparison_artifact
        != {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.construction_k7_positive_promoted_comparison_vector_artifact.v1",
            "io.output_bytes": output_bytes,
            "route_choice_authority": False,
            "comparison_vector": comparison.to_dict(),
        }
        or proof_artifact
        != {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.construction_k7_positive_promoted_projection_artifact.v1",
            "io.output_bytes": output_bytes,
            "actual_projection_proof": proof.to_dict(),
            "all_operational_leaves_projected_exactly_once": True,
        }
    ):
        _fail("positive formal role wrappers changed")
    terminal = role_docs["TERMINAL_ARTIFACT"]
    if terminal != {
        "artifact_role": "TERMINAL_ARTIFACT",
        "schema": "acfqp.construction_k7_positive_promoted_terminal_artifact.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
        "occurrence_id": occurrence_id,
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison.comparison_vector_id,
        "actual_projection_proof_id": proof.actual_projection_proof_id,
        "io.output_bytes": output_bytes,
        "terminal_scope": "LOGICAL_OCCURRENCE_CONSTRUCTION",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "ABSTRACT_CERTIFIED",
        "fresh_abstract_plan_certified": True,
        "local_recovery_executed": False,
        "direct_ground_fallback_executed": False,
        "campaign_closure_issued": False,
        "official_certificate_coverage_authority": False,
        "official_execution_allowed": False,
    }:
        _fail("positive terminal artifact changed")

    fixed_id, fixed_payload = _content_document(
        embedded_fixed,
        id_field="output_bytes_fixed_point_result_id",
        domain=fixed_v1.OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN,
        label="embedded positive fixed-point result",
    )
    if (
        fixed_payload.get("output_bytes_fixed_point_profile_id") != fixed_profile.profile_id
        or fixed_payload.get("renderer_id") != renderer_id
        or fixed_payload.get("execution_identity_id") != stage_id
        or fixed_payload.get("io.output_bytes") != output_bytes
        or fixed_payload.get("exact_fixed_point_verified") is not True
        or fixed_payload.get("operational_artifact_role_semantics_verified") is not False
        or type(fixed_payload.get("iteration_ids")) is not list
        or not fixed_payload["iteration_ids"]
        or any(_cid(item, "fixed-point iteration") != item for item in fixed_payload["iteration_ids"])
    ):
        _fail("embedded fixed-point result changed")
    role_commits = [
        {
            "artifact_role": role,
            "filename": f"{role}.json",
            "byte_count": len(role_raw[role]),
            "bytes_sha256": hashlib.sha256(role_raw[role]).hexdigest(),
            "regular_file": True,
            "file_fsync_completed": True,
        }
        for role in OUTPUT_ROLES
    ]
    output_commit_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_output_commit.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
        "occurrence_id": occurrence_id,
        "output_bytes_fixed_point_result_id": fixed_id,
        "shared_measurement_id": measurement_id,
        "role_commits": role_commits,
        "io.output_bytes": output_bytes,
        "directory_fsync_completed": True,
        "single_write_per_role": True,
        "official_execution_allowed": False,
    }
    output_commit_id = content_id(
        CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_COMMIT_V1_DOMAIN,
        output_commit_payload,
    )
    if embedded_commit != {**output_commit_payload, "output_commit_id": output_commit_id}:
        _fail("embedded positive output commit changed")
    bundle_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_occurrence_accounting.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.117",
        "profile_key": "construction_k7_positive_promoted_occurrence_accounting_v1",
        "occurrence_id": occurrence_id,
        "positive_promoted_overlay_result_id": positive.result_id,
        "positive_promoted_stage_accounting_id": stage_id,
        "shared_measurement_id": measurement_id,
        "shared_resource_receipt_set_id": receipt_set_id,
        "shared_resource_receipt_ids": receipt_ids,
        "path_aggregation_ids": aggregation_ids,
        "counter_record_ids": [row.record_id for row in vector.records],
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison.comparison_vector_id,
        "actual_projection_proof_id": proof.actual_projection_proof_id,
        "output_bytes_fixed_point_result_id": fixed_id,
        "output_commit_id": output_commit_id,
        "shared_resource_path_count": 9,
        "complete_202_counter_record_chain_present": True,
        "all_182_operational_leaves_projected_exactly_once": True,
        "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "ABSTRACT_CERTIFIED",
        "fresh_ground_or_observer_event_count": 0,
        "local_fallback_rebuild_native_zero": True,
        "eight_operational_roles_committed_once": True,
        "logical_occurrence_campaign_closed": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    bundle_id = content_id(
        CONSTRUCTION_K7_POSITIVE_PROMOTED_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
        bundle_payload,
    )
    if embedded_bundle != {
        **bundle_payload,
        "occurrence_accounting_bundle_id": bundle_id,
    }:
        _fail("embedded positive occurrence bundle changed")
    return {
        "occurrence_id": occurrence_id,
        "bundle_id": bundle_id,
        "fixed_id": fixed_id,
        "output_commit_id": output_commit_id,
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison.comparison_vector_id,
        "projection_proof_id": proof.actual_projection_proof_id,
        "comparison_values": comparison.values,
        "output_bytes": output_bytes,
    }


@dataclass(frozen=True, slots=True)
class PositivePromotedCampaignDirectoryVerificationV1:
    positive_verification_id: str
    preregistration_id: str
    occurrence_bundle_id: str
    occurrence_row_id: str
    closure_id: str
    work_vector_id: str
    comparison_vector_id: str
    output_bytes: int
    comparison_values: tuple[tuple[str, int], ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.positive_verification_id, "positive verification"),
            (self.preregistration_id, "campaign preregistration"),
            (self.occurrence_bundle_id, "occurrence bundle"),
            (self.occurrence_row_id, "occurrence row"),
            (self.closure_id, "campaign closure"),
            (self.work_vector_id, "campaign WorkVector"),
            (self.comparison_vector_id, "campaign ComparisonVector"),
        ):
            _cid(value, label)
        if (
            type(self.output_bytes) is not int
            or self.output_bytes <= 0
            or tuple(axis for axis, _value in self.comparison_values) != SHARED_AXES
        ):
            _fail("positive campaign verification values changed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_positive_promoted_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_independent_verification_id": self.positive_verification_id,
            "campaign_preregistration_id": self.preregistration_id,
            "occurrence_accounting_bundle_id": self.occurrence_bundle_id,
            "campaign_occurrence_row_id": self.occurrence_row_id,
            "campaign_closure_id": self.closure_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "io.output_bytes": self.output_bytes,
            "comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.comparison_values
            ],
            "registered_logical_occurrence_count": 1,
            "closed_logical_occurrence_count": 1,
            "closure_denominator": 1,
            "certificate_coverage_denominator": 1,
            "future_economics_cost_denominator": 1,
            "plan_certificate_count": 1,
            "noncertificate_count": 0,
            "producer_modules_imported": False,
            "physical_output_fixed_point_equality_replayed": True,
            "historical_fixed_point_iteration_trace_replayed": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("positive campaign independent verification changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "positive_promoted_campaign_independent_verification_id": self.verification_id,
        }


def verify_positive_promoted_campaign_directory_bytes_v1(
    *,
    source: Any,
    lineage: Any,
    exact_replay: Any,
    source_verification: Any,
    positive_result_bytes: bytes,
    campaign_directory: str | Path,
    expected_preregistration_id: str,
    expected_closure_id: str,
) -> PositivePromotedCampaignDirectoryVerificationV1:
    root = Path(campaign_directory)
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) & 0o077
        or {path.name for path in root.iterdir()}
        != {
            "0001_PREREGISTRATION.json",
            "0002_OCCURRENCE_ROW.json",
            "0003_CAMPAIGN_CLOSURE.json",
            "occurrence-0001",
        }
    ):
        _fail("positive campaign directory inventory changed")
    _prereg_raw, prereg_document = _read_canonical(
        root / "0001_PREREGISTRATION.json", "positive campaign preregistration"
    )
    _row_raw, row_document = _read_canonical(
        root / "0002_OCCURRENCE_ROW.json", "positive campaign occurrence row"
    )
    _closure_raw, closure_document = _read_canonical(
        root / "0003_CAMPAIGN_CLOSURE.json", "positive campaign closure"
    )
    occurrence_directory = root / "occurrence-0001"
    if (
        occurrence_directory.is_symlink()
        or not occurrence_directory.is_dir()
        or {path.name for path in occurrence_directory.iterdir()}
        != {f"{role}.json" for role in OUTPUT_ROLES}
    ):
        _fail("positive occurrence output inventory changed")
    if (
        prereg_document.get("registered_logical_occurrence_count") != 1
        or prereg_document.get("official_execution_allowed") is not False
        or row_document.get("route_kind") != "ABSTRACT_ONLY_CERTIFICATE"
        or row_document.get("terminal_class") != "PLAN_CERTIFICATE"
        or row_document.get("terminal_code") != "ABSTRACT_CERTIFIED"
        or row_document.get("official_execution_allowed") is not False
        or closure_document.get("registered_logical_occurrence_count") != 1
        or closure_document.get("closed_logical_occurrence_count") != 1
        or closure_document.get("closure_denominator") != 1
        or closure_document.get("certificate_coverage_denominator") != 1
        or closure_document.get("future_economics_cost_denominator") != 1
        or closure_document.get("plan_certificate_count") != 1
        or closure_document.get("infeasibility_certificate_count") != 0
        or closure_document.get("noncertificate_count") != 0
        or closure_document.get("official_execution_allowed") is not False
    ):
        _fail("positive campaign cheap claim or denominator gate changed")
    positive = positive_verifier_v1.verify_positive_promoted_overlay_bytes_independently_v1(
        source=source,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=source_verification,
        result_bytes=positive_result_bytes,
    )
    positive_document = loads_canonical_json(positive_result_bytes)
    preregistration_id = _verify_preregistration(
        prereg_document,
        positive=positive,
        positive_document=positive_document,
        expected_id=expected_preregistration_id,
    )
    row_id, row_payload = _content_document(
        row_document,
        id_field="campaign_occurrence_row_id",
        domain=CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
        label="positive campaign occurrence row",
    )
    try:
        embedded_bundle = row_payload["occurrence_accounting_bundle"]
        embedded_fixed = row_payload["output_bytes_fixed_point_result"]
        embedded_commit = row_payload["output_commit"]
    except KeyError as error:
        raise ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error(
            "positive campaign occurrence evidence is incomplete"
        ) from error
    occurrence = _verify_occurrence(
        occurrence_directory,
        positive_result_bytes=positive_result_bytes,
        positive=positive,
        positive_document=positive_document,
        embedded_bundle=embedded_bundle,
        embedded_fixed=embedded_fixed,
        embedded_commit=embedded_commit,
    )
    expected_row_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_campaign_occurrence_row.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_positive_promoted_campaign_v1",
        "campaign_preregistration_id": preregistration_id,
        "occurrence_id": occurrence["occurrence_id"],
        "occurrence_accounting_bundle_id": occurrence["bundle_id"],
        "output_commit_id": occurrence["output_commit_id"],
        "work_vector_id": occurrence["work_vector_id"],
        "comparison_vector_id": occurrence["comparison_vector_id"],
        "actual_projection_proof_id": occurrence["projection_proof_id"],
        "occurrence_accounting_bundle": embedded_bundle,
        "output_bytes_fixed_point_result": embedded_fixed,
        "output_commit": embedded_commit,
        "comparison_values": [
            {"axis": axis, "value": value}
            for axis, value in occurrence["comparison_values"]
        ],
        "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "ABSTRACT_CERTIFIED",
        "closure_denominator_contribution": 1,
        "certificate_coverage_denominator_contribution": 1,
        "future_economics_denominator_contribution": 1,
        "plan_certificate_count_contribution": 1,
        "infeasibility_certificate_count_contribution": 0,
        "noncertificate_count_contribution": 0,
        "official_execution_allowed": False,
    }
    if row_payload != expected_row_payload:
        _fail("positive campaign occurrence row differs from independent replay")
    closure_id, closure_payload = _content_document(
        closure_document,
        id_field="campaign_closure_id",
        domain=CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN,
        label="positive campaign closure",
    )
    expected_closure_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_campaign_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.118",
        "profile_key": "construction_k7_positive_promoted_campaign_v1",
        "campaign_preregistration_id": preregistration_id,
        "ordered_occurrence_row_ids": [row_id],
        "registered_logical_occurrence_count": 1,
        "closed_logical_occurrence_count": 1,
        "closure_denominator": 1,
        "certificate_coverage_denominator": 1,
        "future_economics_cost_denominator": 1,
        "plan_certificate_count": 1,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": 0,
        "cumulative_comparison_values": [
            {"axis": axis, "value": value}
            for axis, value in occurrence["comparison_values"]
        ],
        "all_registered_occurrences_retained": True,
        "campaign_construction_closed": True,
        "official_certificate_coverage_authority": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if (
        closure_payload != expected_closure_payload
        or closure_id != _cid(expected_closure_id, "expected campaign closure")
    ):
        _fail("positive campaign closure differs from independent replay")
    return PositivePromotedCampaignDirectoryVerificationV1(
        positive.verification_id,
        preregistration_id,
        occurrence["bundle_id"],
        row_id,
        closure_id,
        occurrence["work_vector_id"],
        occurrence["comparison_vector_id"],
        occurrence["output_bytes"],
        occurrence["comparison_values"],
    )


__all__ = (
    "ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "PositivePromotedCampaignDirectoryVerificationV1",
    "verify_positive_promoted_campaign_directory_bytes_v1",
)
