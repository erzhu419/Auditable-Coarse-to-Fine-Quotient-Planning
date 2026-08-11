"""Bytes-only verifier for recovery-eligible preregistered campaigns.

The verifier imports no recovery campaign, occurrence, supervisor, runtime, or
planner producer.  It starts from two externally retained content IDs and the
committed directory bytes, then replays the campaign DAG, all three formal
accounting chains per occurrence, output manifests, commit chain, vector
prefixes, and the complete denominator closure.
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
    derive_comparison_vector_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_recovery_eligible_campaign_independent_verifier_v1"
INPUT_ROLES = (
    "SOURCE_BUNDLE_BINDING",
    "REUSABLE_RAPM_SNAPSHOT",
    "PROOF_DEPENDENCY_TRANSITION",
)
OUTPUT_ROLES = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
ROUTE_KEYS = (
    ("supervised_wrapper_work_vector", "supervised_wrapper_comparison_vector", "supervised_wrapper_actual_projection_proof", RouteKindEnum.ABSTRACT_FAILED_PREFIX, ActualWorkScope.COMMON_PREFIX),
    ("local_recovery_work_vector", "local_recovery_comparison_vector", "local_recovery_actual_projection_proof", RouteKindEnum.LOCAL_ATTEMPT, ActualWorkScope.MARGINAL_ROUTE_AGGREGATE),
    ("direct_fallback_work_vector", "direct_fallback_comparison_vector", "direct_fallback_actual_projection_proof", RouteKindEnum.DIRECT_FALLBACK, ActualWorkScope.MARGINAL_ROUTE_AGGREGATE),
)
PEAK_AXES = frozenset({"peak_mounted_bytes", "peak_working_bytes"})
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
LOCAL_RECOVERY_PATH_PREFIXES = ("local.", "acquisition.", "build.")
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)


class ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(RuntimeError):
    """Committed campaign bytes do not replay to the expected identities."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(
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
        raise ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(
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
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(
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
    document: dict[str, Any], expected_id: str
) -> tuple[str, dict[str, Any], tuple[dict[str, Any], ...]]:
    _exact(
        document,
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "runtime_preparation", "input_blobs", "workload", "registration_stage",
            "campaign_preregistration_present", "execution_started_by_this_artifact",
            "campaign_result_present", "official_scalar_cost", "official_N_break_even",
            "official_execution_allowed", "campaign_preregistration_id",
        },
        "campaign preregistration",
    )
    observed, _payload = _content_document(
        document,
        id_field="campaign_preregistration_id",
        domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
        label="campaign preregistration",
    )
    if observed != _cid(expected_id, "expected campaign preregistration"):
        _fail("campaign preregistration is not the externally expected identity")
    if (
        document["schema"] != "acfqp.construction_k7_recovery_eligible_campaign_preregistration.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["registration_stage"] != "BEFORE_FIRST_OCCURRENCE_WORKER_LAUNCH"
        or document["campaign_preregistration_present"] is not True
        or document["execution_started_by_this_artifact"] is not False
        or document["campaign_result_present"] is not False
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["official_execution_allowed"] is not False
    ):
        _fail("campaign preregistration locks changed")

    runtime = document["runtime_preparation"]
    if type(runtime) is not dict:
        _fail("campaign runtime preparation is not an object")
    runtime_id, _runtime_payload = _content_document(
        runtime,
        id_field="recovery_eligible_runtime_preparation_id",
        domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN,
        label="campaign runtime preparation",
    )
    if (
        runtime.get("private_runtime_lease_required") is not True
        or runtime.get("construction_only") is not True
        or runtime.get("official_execution_allowed") is not False
    ):
        _fail("campaign runtime preparation locks changed")

    blobs = document["input_blobs"]
    if type(blobs) is not list or len(blobs) != len(INPUT_ROLES):
        _fail("campaign input blob inventory changed")
    verified_blobs: list[dict[str, Any]] = []
    for role, blob in zip(INPUT_ROLES, blobs, strict=True):
        _exact(
            blob,
            {
                "schema", "schema_version", "profile_key", "role",
                "canonical_json_bytes_hex", "byte_count", "sha256",
                "campaign_input_blob_id",
            },
            f"campaign input blob {role}",
        )
        blob_id, _blob_payload = _content_document(
            blob,
            id_field="campaign_input_blob_id",
            domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
            label=f"campaign input blob {role}",
        )
        try:
            raw = bytes.fromhex(blob["canonical_json_bytes_hex"])
        except (TypeError, ValueError) as error:
            raise ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error(
                "campaign input blob hex is invalid"
            ) from error
        if (
            blob["role"] != role
            or blob["byte_count"] != len(raw)
            or blob["sha256"] != hashlib.sha256(raw).hexdigest()
            or canonical_json_bytes(loads_canonical_json(raw)) != raw
        ):
            _fail("campaign input blob bytes or role changed")
        verified_blobs.append({"role": role, "blob_id": blob_id, "raw": raw})

    workload = document["workload"]
    _exact(
        workload,
        {
            "schema", "schema_version", "profile_key", "runtime_preparation_id",
            "runtime_tree_id", "source_closure_id", "shared_input_blob_ids",
            "ordered_occurrence_spec_ids", "ordered_logical_occurrence_ids",
            "ordered_query_ordinals", "registered_logical_occurrence_count",
            "denominator_frozen_before_execution", "shared_rapm_and_proof_cache_inputs_required",
            "occurrence_deletion_allowed", "official_execution_allowed", "campaign_workload_id",
        },
        "campaign workload",
    )
    workload_id, _workload_payload = _content_document(
        workload,
        id_field="campaign_workload_id",
        domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN,
        label="campaign workload",
    )
    count = workload["registered_logical_occurrence_count"]
    logical_ids = workload["ordered_logical_occurrence_ids"]
    ordinals = workload["ordered_query_ordinals"]
    spec_ids = workload["ordered_occurrence_spec_ids"]
    blob_ids = [row["blob_id"] for row in verified_blobs]
    if (
        workload["runtime_preparation_id"] != runtime_id
        or workload["runtime_tree_id"] != runtime["runtime_manifest"]["runtime_tree_id"]
        or workload["source_closure_id"] != runtime["source_closure"]["closure_id"]
        or workload["shared_input_blob_ids"] != blob_ids
        or type(count) is not int
        or not (2 <= count <= 32)
        or not all(type(rows) is list and len(rows) == count for rows in (logical_ids, ordinals, spec_ids))
        or len(set(logical_ids)) != count
        or len(set(ordinals)) != count
        or workload["denominator_frozen_before_execution"] is not True
        or workload["shared_rapm_and_proof_cache_inputs_required"] is not True
        or workload["occurrence_deletion_allowed"] is not False
        or workload["official_execution_allowed"] is not False
    ):
        _fail("campaign workload identity or denominator changed")
    for index, (logical_id, ordinal, spec_id) in enumerate(
        zip(logical_ids, ordinals, spec_ids, strict=True), start=1
    ):
        _cid(logical_id, "registered logical occurrence")
        if type(ordinal) is not int or ordinal <= 1:
            _fail("registered query ordinal changed")
        spec_payload = {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_occurrence_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": "construction_k7_recovery_eligible_preregistered_campaign_v1",
            "occurrence_index": index,
            "logical_occurrence_id": logical_id,
            "query_ordinal": ordinal,
            "input_blob_ids_by_role": [
                {"role": role, "campaign_input_blob_id": blob_id}
                for role, blob_id in zip(INPUT_ROLES, blob_ids, strict=True)
            ],
            "execution_result_present": False,
            "registered_before_first_worker_launch": True,
            "official_execution_allowed": False,
        }
        if content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN,
            spec_payload,
        ) != spec_id:
            _fail("campaign occurrence spec ID does not replay")
    return workload_id, runtime, tuple(verified_blobs)


def _verify_event(
    document: dict[str, Any],
    *,
    sequence: int,
    previous_id: str | None,
    subject_id: str,
    subject_filename: str,
    subject_raw: bytes,
    logical_occurrence_id: str | None,
) -> str:
    _exact(
        document,
        {
            "schema", "schema_version", "profile_key", "sequence", "event_kind",
            "previous_event", "subject_id", "subject_filename", "subject_byte_count",
            "subject_sha256", "occurrence_index", "logical_occurrence_id",
            "file_fsync_completed", "directory_fsync_completed", "construction_only",
            "official_execution_allowed", "campaign_commit_event_id",
        },
        "campaign commit event",
    )
    event_id, _payload = _content_document(
        document,
        id_field="campaign_commit_event_id",
        domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
        label="campaign commit event",
    )
    expected_previous = (
        {"kind": "GENESIS", "reason": "PREREGISTRATION_IS_FIRST"}
        if previous_id is None
        else {"kind": "PREVIOUS_EVENT", "campaign_commit_event_id": previous_id}
    )
    expected_kind = "PREREGISTRATION_COMMITTED" if sequence == 0 else "OCCURRENCE_BUNDLE_COMMITTED"
    if (
        document["sequence"] != sequence
        or document["event_kind"] != expected_kind
        or document["previous_event"] != expected_previous
        or document["subject_id"] != subject_id
        or document["subject_filename"] != subject_filename
        or document["subject_byte_count"] != len(subject_raw)
        or document["subject_sha256"] != hashlib.sha256(subject_raw).hexdigest()
        or document["occurrence_index"] != (None if sequence == 0 else sequence)
        or document["logical_occurrence_id"] != logical_occurrence_id
        or document["file_fsync_completed"] is not True
        or document["directory_fsync_completed"] is not True
        or document["construction_only"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _fail("campaign commit event semantics changed")
    return event_id


def _replay_simple_id(document: dict[str, Any], id_field: str, domain: str, label: str) -> str:
    value, _payload = _content_document(document, id_field=id_field, domain=domain, label=label)
    return value


def _verify_occurrence_output(
    directory: Path,
    *,
    logical_occurrence_id: str,
    prereg_runtime: dict[str, Any],
) -> dict[str, Any]:
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or stat.S_IMODE(directory.stat().st_mode) & 0o077
        or {path.name for path in directory.iterdir()} != {f"{role}.json" for role in OUTPUT_ROLES}
    ):
        _fail("occurrence output inventory changed")
    role_raw: dict[str, bytes] = {}
    role_docs: dict[str, dict[str, Any]] = {}
    for role in OUTPUT_ROLES:
        raw, document = _read_canonical(directory / f"{role}.json", f"occurrence {role}")
        if document.get("artifact_role") != role:
            _fail("occurrence artifact role changed")
        role_raw[role] = raw
        role_docs[role] = document
    output_bytes = sum(len(raw) for raw in role_raw.values())

    manifest = role_docs["OUTPUT_MANIFEST"]
    _exact(
        manifest,
        {
            "artifact_role", "schema", "occurrence_id", "output_bytes_fixed_point_profile_id",
            "io.output_bytes", "ordered_preceding_roles",
            "output_manifest_self_extent_excluded_from_preceding_rows", "required_role_order",
        },
        "occurrence output manifest",
    )
    preceding = [
        {
            "artifact_role": role,
            "byte_count": len(role_raw[role]),
            "bytes_sha256": hashlib.sha256(role_raw[role]).hexdigest(),
        }
        for role in OUTPUT_ROLES[:-1]
    ]
    if (
        manifest["occurrence_id"] != logical_occurrence_id
        or manifest["io.output_bytes"] != output_bytes
        or manifest["ordered_preceding_roles"] != preceding
        or manifest["required_role_order"] != list(OUTPUT_ROLES)
        or manifest["output_manifest_self_extent_excluded_from_preceding_rows"] is not True
    ):
        _fail("occurrence output fixed point or manifest changed")

    business = role_docs["BUSINESS_RESULT"]
    if (
        business.get("schema") != "acfqp.construction_k7_recovery_eligible_business_result.v1"
        or business.get("occurrence_id") != logical_occurrence_id
        or business.get("runtime_preparation") != prereg_runtime
        or business.get("terminal_class") != "PLAN_CERTIFICATE"
        or business.get("terminal_code") != "FULL_GROUND_FALLBACK"
        or business.get("construction_only") is not True
        or business.get("official_execution_allowed") is not False
    ):
        _fail("occurrence business result changed")
    request = business["supervised_request"]
    request_id = _replay_simple_id(
        request,
        "supervised_request_id",
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN,
        "occurrence supervised request",
    )
    if request["logical_occurrence_id"] != logical_occurrence_id:
        _fail("occurrence supervised request identity changed")
    measurement = business["shared_measurement"]
    measurement_id = _replay_simple_id(
        measurement,
        "shared_measurement_id",
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN,
        "occurrence shared measurement",
    )
    if (
        measurement["supervised_request_id"] != request_id
        or measurement["occurrence_id"] != logical_occurrence_id
        or measurement["process_exit_successes"] != 1
        or measurement["process_exit_failures"] != 0
        or measurement["formal_counter_records_issued_here"] is not False
        or measurement["official_execution_allowed"] is not False
    ):
        _fail("occurrence shared measurement changed")
    science = business["science_summary"]
    if (
        science["occurrence_id"] != logical_occurrence_id
        or science["terminal_class"] != "PLAN_CERTIFICATE"
        or science["terminal_code"] != "FULL_GROUND_FALLBACK"
        or science["proof_node_reuse_count"] != 41
        or science["requested_frontier_row_count"] != 6
        or science["local_ground_draw_count"] != 12_672
        or science["fallback_states_expanded"] != 30
        or science["fallback_actions_evaluated"] != 96
        or science["fallback_ground_steps"] != 96
        or science["fallback_outcome_rows"] != 1_440
        or science["fallback_bellman_backups"] != 102
    ):
        _fail("occurrence scientific summary changed")

    trace = role_docs["OPERATIONAL_TRACE"]
    trace_id = _replay_simple_id(
        trace,
        "operational_trace_id",
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN,
        "occurrence operational trace",
    )
    if (
        trace["supervised_request_id"] != request_id
        or trace["science_summary"] != science
        or trace["full_planner_replayed_for_operational_validation"] is not False
        or trace["standalone_verifier_work_included"] is not False
        or trace["formal_occurrence_counter_records_issued_by_worker"] is not False
    ):
        _fail("occurrence operational trace semantics changed")

    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry, comparison_profile
    )
    stages = tuple(
        live_v3.RecordedStageWorkV3.from_document(
            row, registry, stage_profile, comparison_profile, actual_profile
        )
        for row in trace["recorded_stages"]
    )
    if len(stages) != 3:
        _fail("occurrence operational stage count changed")
    for row in stages:
        live_v3.verify_recorded_stage_work_v3(
            row, registry, stage_profile, comparison_profile, actual_profile
        )

    renderer_id = content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN,
        {
            "supervised_execution_id": measurement_id,
            "occurrence_id": logical_occurrence_id,
            "shared_measurement_id": measurement_id,
            "operational_trace_id": trace_id,
            "required_roles": list(OUTPUT_ROLES),
        },
    )
    fixed_profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=measurement_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={role: 256 * 1024 * 1024 for role in OUTPUT_ROLES},
        max_iterations=32,
    )
    if fixed_profile.profile_id != manifest["output_bytes_fixed_point_profile_id"]:
        _fail("occurrence fixed-point profile does not replay")
    records_by_path = tuple(
        {record.path: record for record in row.work_vector.records} for row in stages
    )
    fixed_pre_output = {
        row["path"]: row["value"] for row in measurement["fixed_pre_output_values"]
    }
    derived_reconciliation = {
        "process.exit_failures": 0,
        "process.exit_successes": 1,
        "route.attempts": science["route_attempts"],
        "route.failures": science["route_failures"],
        "route.successes": science["route_successes"],
        "solver.attempts": science["solver_attempts"],
        "solver.failures": science["solver_failures"],
        "solver.successes": science["solver_successes"],
    }
    if (
        derived_reconciliation["route.attempts"]
        != derived_reconciliation["route.successes"]
        + derived_reconciliation["route.failures"]
        or derived_reconciliation["solver.attempts"]
        != derived_reconciliation["solver.successes"]
        + derived_reconciliation["solver.failures"]
        or fixed_pre_output["process.launches"] != 1
    ):
        _fail("occurrence reconciliation facts changed")

    def render_candidate(candidate: int) -> dict[str, bytes]:
        shared_values = dict(fixed_pre_output)
        shared_values["io.mounted_bytes_peak"] = max(
            measurement["pre_output_mounted_bytes_peak"], candidate
        )
        shared_values["io.output_bytes"] = candidate
        receipt_docs: list[dict[str, Any]] = []
        receipt_ids: list[str] = []
        for path in SHARED_PATHS:
            payload = {
                "schema": "acfqp.construction_k7_recovery_eligible_shared_receipt.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": "2.0.116",
                "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
                "occurrence_id": logical_occurrence_id,
                "supervised_execution_id": measurement_id,
                "shared_measurement_id": measurement_id,
                "path": path,
                "reducer": registry.by_path[path].reducer.value,
                "value": shared_values[path],
                "source_kind": (
                    "OUTPUT_FIXED_POINT" if path == "io.output_bytes"
                    else "TRUSTED_SUPERVISOR_MEASUREMENT"
                ),
                "source_evidence_id": (
                    fixed_profile.profile_id if path == "io.output_bytes" else measurement_id
                ),
                "stage_placeholder_record_ids": [rows[path].record_id for rows in records_by_path],
                "output_fixed_point_profile_id": (
                    fixed_profile.profile_id if path == "io.output_bytes" else None
                ),
                "complete_window_closed": True,
                "stage_placeholders_replaced_not_summed": True,
                "official_execution_allowed": False,
            }
            receipt_id = content_id(
                CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
                payload,
            )
            receipt_ids.append(receipt_id)
            receipt_docs.append({**payload, "shared_resource_receipt_id": receipt_id})
        receipt_set_payload = {
            "schema": "acfqp.construction_k7_recovery_eligible_shared_receipt_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
            "occurrence_id": logical_occurrence_id,
            "supervised_execution_id": measurement_id,
            "shared_measurement_id": measurement_id,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_receipt_ids": receipt_ids,
            "receipt_count": 9,
            "all_nine_shared_paths_semantically_replayed": True,
            "official_execution_allowed": False,
        }
        receipt_set_id = content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
            receipt_set_payload,
        )
        receipt_set_doc = {
            **receipt_set_payload,
            "shared_resource_receipt_set_id": receipt_set_id,
        }
        receipt_by_path = dict(zip(SHARED_PATHS, receipt_docs, strict=True))
        aggregation_docs: list[dict[str, Any]] = []
        aggregation_values: dict[str, int] = {}
        aggregation_ids: dict[str, str] = {}
        for path in registry.required_paths:
            stage_records = tuple(rows[path] for rows in records_by_path)
            if path in receipt_by_path:
                value = receipt_by_path[path]["value"]
                source_kind = "SHARED_RESOURCE_RECEIPT"
                source_id = receipt_by_path[path]["shared_resource_receipt_id"]
            elif path in derived_reconciliation:
                value = derived_reconciliation[path]
                source_kind = "SEMANTIC_DERIVED_RECONCILIATION"
                source_id = trace_id
            elif registry.by_path[path].reducer is ReducerEnum.SUM:
                value = sum(row.value for row in stage_records)
                source_kind = "STAGE_SUM"
                source_id = measurement_id
            else:
                value = max(row.value for row in stage_records)
                source_kind = "STAGE_MAX"
                source_id = measurement_id
            payload = {
                "schema": "acfqp.construction_k7_recovery_eligible_path_aggregation.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
                "occurrence_id": logical_occurrence_id,
                "supervised_execution_id": measurement_id,
                "path": path,
                "reducer": registry.by_path[path].reducer.value,
                "value": value,
                "stage_record_ids": [row.record_id for row in stage_records],
                "source_kind": source_kind,
                "source_evidence_id": source_id,
                "all_stage_instances_retained": True,
                "shared_stage_placeholders_replaced_not_summed": path in SHARED_PATHS,
            }
            aggregation_id = content_id(
                CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN,
                payload,
            )
            aggregation_docs.append({**payload, "path_aggregation_id": aggregation_id})
            aggregation_values[path] = value
            aggregation_ids[path] = aggregation_id

        components = (
            ("SUPERVISED_OCCURRENCE_WRAPPER", RouteKindEnum.ABSTRACT_FAILED_PREFIX),
            ("LOCAL_RECOVERY_AGGREGATE", RouteKindEnum.LOCAL_ATTEMPT),
            ("DIRECT_FALLBACK", RouteKindEnum.DIRECT_FALLBACK),
        )
        component_values = {
            name: {path: 0 for path in registry.required_paths}
            for name, _route in components
        }
        for path in registry.required_paths:
            if path.startswith(LOCAL_RECOVERY_PATH_PREFIXES):
                component_values["LOCAL_RECOVERY_AGGREGATE"][path] = aggregation_values[path]
            elif path.startswith(("fallback.", "route.", "solver.")):
                component_values["DIRECT_FALLBACK"][path] = aggregation_values[path]
            elif path.startswith("control."):
                first_two = tuple(records_by_path[index][path].value for index in (0, 1))
                last = (records_by_path[2][path].value,)
                if registry.by_path[path].reducer is ReducerEnum.SUM:
                    component_values["LOCAL_RECOVERY_AGGREGATE"][path] = sum(first_two)
                    component_values["DIRECT_FALLBACK"][path] = sum(last)
                else:
                    component_values["LOCAL_RECOVERY_AGGREGATE"][path] = max(first_two)
                    component_values["DIRECT_FALLBACK"][path] = max(last)
            else:
                component_values["SUPERVISED_OCCURRENCE_WRAPPER"][path] = aggregation_values[path]
        candidate_vectors: list[WorkVectorV1] = []
        candidate_comparisons: list[ComparisonVectorV1] = []
        candidate_proofs: list[ActualProjectionProofV1] = []
        for name, route_kind in components:
            records = tuple(
                CounterRecordV1(
                    registry.registry_id,
                    path,
                    component_values[name][path],
                    True,
                    content_id(
                        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN,
                        {
                            "occurrence_path_aggregation_id": aggregation_ids[path],
                            "component_name": name,
                            "route_kind": route_kind.value,
                            "component_value": component_values[name][path],
                        },
                    ),
                    registry.by_path[path].semantics_id,
                    registry.by_path[path].owner,
                    registry.by_path[path].unit,
                    registry.by_path[path].lane,
                    registry.by_path[path].scope,
                    registry.by_path[path].reducer,
                )
                for path in registry.required_paths
            )
            vector = WorkVectorV1(
                registry.registry_id, logical_occurrence_id, route_kind, records
            )
            comparison = derive_comparison_vector_v1(
                vector, registry, comparison_profile
            )
            proof = ActualProjectionProofV1(
                actual_profile.actual_projection_profile_id,
                registry.registry_id,
                comparison_profile.comparison_profile_id,
                vector.work_vector_id,
                comparison.comparison_vector_id,
                LaneEnum.OPERATIONAL,
                (
                    ActualWorkScope.COMMON_PREFIX
                    if route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
                    else ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
                ),
                len(actual_profile.terms),
            )
            verify_actual_projection_v1(
                proof, vector, comparison, registry, comparison_profile, actual_profile
            )
            candidate_vectors.append(vector)
            candidate_comparisons.append(comparison)
            candidate_proofs.append(proof)
        axis_reducers = {row.name: row.reducer for row in comparison_profile.axes}
        occurrence_values = tuple(
            (
                axis,
                (
                    sum(dict(row.values)[axis] for row in candidate_comparisons)
                    if axis_reducers[axis] is ReducerEnum.SUM
                    else max(dict(row.values)[axis] for row in candidate_comparisons)
                ),
            )
            for axis in SHARED_AXES
        )
        wrapper, local, fallback = candidate_vectors
        wrapper_comparison, local_comparison, fallback_comparison = candidate_comparisons
        wrapper_proof, local_proof, fallback_proof = candidate_proofs
        roles: dict[str, bytes] = {
            "BUSINESS_RESULT": role_raw["BUSINESS_RESULT"],
            "OPERATIONAL_TRACE": role_raw["OPERATIONAL_TRACE"],
        }
        roles["TERMINAL_ARTIFACT"] = canonical_json_bytes(
            {
                "artifact_role": "TERMINAL_ARTIFACT",
                "schema": "acfqp.construction_k7_recovery_eligible_terminal_artifact.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
                "occurrence_id": logical_occurrence_id,
                "native_accounting_id": measurement["native_accounting_id"],
                "direct_ground_fallback_id": science["direct_ground_fallback_id"],
                "component_work_vector_ids": [row.work_vector_id for row in candidate_vectors],
                "component_comparison_vector_ids": [row.comparison_vector_id for row in candidate_comparisons],
                "component_actual_projection_proof_ids": [row.actual_projection_proof_id for row in candidate_proofs],
                "io.output_bytes": candidate,
                "terminal_scope": "LOGICAL_OCCURRENCE_CONSTRUCTION",
                "terminal_class": "PLAN_CERTIFICATE",
                "terminal_code": "FULL_GROUND_FALLBACK",
                "scientific_plan_certificate_preserved": True,
                "official_certificate_coverage_authority": False,
                "campaign_closure_issued": False,
                "official_execution_allowed": False,
            }
        )
        roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
            {
                "artifact_role": "COUNTER_RECORD_SET",
                "schema": "acfqp.construction_k7_recovery_eligible_counter_record_set.v1",
                "occurrence_id": logical_occurrence_id,
                "io.output_bytes": candidate,
                "shared_resource_receipt_set": receipt_set_doc,
                "shared_resource_receipts": receipt_docs,
                "component_counter_record_count": 3 * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT,
                "counter_records_per_component": registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT,
                "path_aggregations": aggregation_docs,
                "component_counter_records": [
                    {
                        "route_kind": row.route_kind.value,
                        "counter_records": [item.to_dict() for item in row.records],
                    }
                    for row in candidate_vectors
                ],
            }
        )
        roles["WORK_VECTOR"] = canonical_json_bytes(
            {
                "artifact_role": "WORK_VECTOR",
                "schema": "acfqp.construction_k7_recovery_eligible_work_vector_artifact.v1",
                "io.output_bytes": candidate,
                "route_family_vectors_remain_separate": True,
                "marginal_route_upper_compliance_authority": False,
                "supervised_wrapper_work_vector": wrapper.to_dict(),
                "local_recovery_work_vector": local.to_dict(),
                "direct_fallback_work_vector": fallback.to_dict(),
            }
        )
        roles["COMPARISON_VECTOR"] = canonical_json_bytes(
            {
                "artifact_role": "COMPARISON_VECTOR",
                "schema": "acfqp.construction_k7_recovery_eligible_comparison_vector_artifact.v1",
                "io.output_bytes": candidate,
                "route_choice_authority": False,
                "supervised_wrapper_comparison_vector": wrapper_comparison.to_dict(),
                "local_recovery_comparison_vector": local_comparison.to_dict(),
                "direct_fallback_comparison_vector": fallback_comparison.to_dict(),
                "occurrence_reducer_exact_comparison_values": [
                    {"axis": axis, "value": value} for axis, value in occurrence_values
                ],
            }
        )
        roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
            {
                "artifact_role": "ACTUAL_PROJECTION_PROOF",
                "schema": "acfqp.construction_k7_recovery_eligible_projection_artifact.v1",
                "io.output_bytes": candidate,
                "supervised_wrapper_actual_projection_proof": wrapper_proof.to_dict(),
                "local_recovery_actual_projection_proof": local_proof.to_dict(),
                "direct_fallback_actual_projection_proof": fallback_proof.to_dict(),
            }
        )
        preceding = [
            {
                "artifact_role": role,
                "byte_count": len(raw),
                "bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
            for role, raw in roles.items()
        ]
        roles["OUTPUT_MANIFEST"] = canonical_json_bytes(
            {
                "artifact_role": "OUTPUT_MANIFEST",
                "schema": "acfqp.construction_k7_recovery_eligible_output_manifest.v1",
                "occurrence_id": logical_occurrence_id,
                "output_bytes_fixed_point_profile_id": fixed_profile.profile_id,
                "io.output_bytes": candidate,
                "ordered_preceding_roles": preceding,
                "output_manifest_self_extent_excluded_from_preceding_rows": True,
                "required_role_order": list(OUTPUT_ROLES),
            }
        )
        return roles

    fixed_result = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=fixed_profile, renderer=render_candidate
    )
    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=fixed_result, renderer=render_candidate
    )
    if fixed_result.artifact_bytes_by_role != role_raw:
        _fail("occurrence committed roles differ from independent fixed-point replay")

    work_artifact = role_docs["WORK_VECTOR"]
    comparison_artifact = role_docs["COMPARISON_VECTOR"]
    proof_artifact = role_docs["ACTUAL_PROJECTION_PROOF"]
    vectors: list[WorkVectorV1] = []
    comparisons: list[ComparisonVectorV1] = []
    proofs: list[ActualProjectionProofV1] = []
    for work_key, comparison_key, proof_key, route_kind, scope in ROUTE_KEYS:
        vector = WorkVectorV1.from_dict(work_artifact[work_key], registry)
        comparison = ComparisonVectorV1.from_dict(comparison_artifact[comparison_key])
        proof = ActualProjectionProofV1.from_dict(proof_artifact[proof_key])
        derived = derive_comparison_vector_v1(vector, registry, comparison_profile)
        if (
            vector.route_kind is not route_kind
            or vector.subject_id != logical_occurrence_id
            or len(vector.records) != registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
            or comparison != derived
            or proof.work_scope is not scope
            or proof.projection_term_count != registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
        ):
            _fail("occurrence formal accounting chain changed")
        verify_actual_projection_v1(
            proof, vector, comparison, registry, comparison_profile, actual_profile
        )
        vectors.append(vector)
        comparisons.append(comparison)
        proofs.append(proof)
    axis_reducers = {row.name: row.reducer for row in comparison_profile.axes}
    occurrence_values = tuple(
        (
            axis,
            (
                sum(dict(row.values)[axis] for row in comparisons)
                if axis_reducers[axis] is ReducerEnum.SUM
                else max(dict(row.values)[axis] for row in comparisons)
            ),
        )
        for axis in SHARED_AXES
    )
    if comparison_artifact["occurrence_reducer_exact_comparison_values"] != [
        {"axis": axis, "value": value} for axis, value in occurrence_values
    ]:
        _fail("occurrence comparison reduction changed")

    counter = role_docs["COUNTER_RECORD_SET"]
    receipt_set = counter["shared_resource_receipt_set"]
    receipt_set_id = _replay_simple_id(
        receipt_set,
        "shared_resource_receipt_set_id",
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
        "occurrence receipt set",
    )
    receipts = counter["shared_resource_receipts"]
    if type(receipts) is not list or len(receipts) != 9:
        _fail("occurrence shared receipt inventory changed")
    receipt_ids = tuple(
        _replay_simple_id(
            row,
            "shared_resource_receipt_id",
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
            "occurrence shared receipt",
        )
        for row in receipts
    )
    if receipt_set["shared_resource_receipt_ids"] != list(receipt_ids):
        _fail("occurrence receipt set membership changed")
    output_receipts = [row for row in receipts if row["path"] == "io.output_bytes"]
    if len(output_receipts) != 1 or output_receipts[0]["value"] != output_bytes:
        _fail("occurrence output receipt changed")
    fixed_point_id = fixed_result.result_id
    if output_receipts[0]["output_fixed_point_profile_id"] != manifest["output_bytes_fixed_point_profile_id"]:
        _fail("occurrence output fixed-point profile changed")
    aggregations = counter["path_aggregations"]
    if type(aggregations) is not list or len(aggregations) != registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT:
        _fail("occurrence path aggregation inventory changed")
    aggregation_ids = tuple(
        _replay_simple_id(
            row,
            "path_aggregation_id",
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN,
            "occurrence path aggregation",
        )
        for row in aggregations
    )
    component_records = counter["component_counter_records"]
    if (
        type(component_records) is not list
        or len(component_records) != 3
        or counter["component_counter_record_count"] != 3 * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
        or counter["counter_records_per_component"] != registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
    ):
        _fail("occurrence formal counter inventory changed")
    for item, vector in zip(component_records, vectors, strict=True):
        if item != {
            "route_kind": vector.route_kind.value,
            "counter_records": [row.to_dict() for row in vector.records],
        }:
            _fail("occurrence counter record set differs from WorkVector")

    terminal = role_docs["TERMINAL_ARTIFACT"]
    if (
        terminal["occurrence_id"] != logical_occurrence_id
        or terminal["component_work_vector_ids"] != [row.work_vector_id for row in vectors]
        or terminal["component_comparison_vector_ids"] != [row.comparison_vector_id for row in comparisons]
        or terminal["component_actual_projection_proof_ids"] != [row.actual_projection_proof_id for row in proofs]
        or terminal["io.output_bytes"] != output_bytes
        or terminal["terminal_class"] != "PLAN_CERTIFICATE"
        or terminal["terminal_code"] != "FULL_GROUND_FALLBACK"
        or terminal["campaign_closure_issued"] is not False
        or terminal["official_execution_allowed"] is not False
    ):
        _fail("occurrence terminal artifact changed")

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
        "schema": "acfqp.construction_k7_recovery_eligible_output_commit.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
        "occurrence_id": logical_occurrence_id,
        "output_bytes_fixed_point_result_id": fixed_point_id,
        "shared_measurement_id": measurement_id,
        "role_commits": role_commits,
        "io.output_bytes": output_bytes,
        "single_write_per_role": True,
        "directory_fsync_completed": True,
        "commit_receipt_is_provenance_not_an_extra_output_role": True,
        "construction_only": True,
        "official_execution_allowed": False,
    }
    output_commit_id = content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN,
        output_commit_payload,
    )
    bundle_payload = {
        "schema": "acfqp.construction_k7_recovery_eligible_occurrence_accounting.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.116",
        "profile_key": "construction_k7_recovery_eligible_occurrence_accounting_v1",
        "occurrence_id": logical_occurrence_id,
        "native_accounting_id": measurement["native_accounting_id"],
        "supervised_execution_id": measurement_id,
        "shared_measurement_id": measurement_id,
        "shared_resource_receipt_set_id": receipt_set_id,
        "shared_resource_receipt_ids": list(receipt_ids),
        "output_bytes_fixed_point_result_id": fixed_point_id,
        "output_commit_id": output_commit_id,
        "path_aggregation_ids": list(aggregation_ids),
        "component_counter_record_ids": [[item.record_id for item in row.records] for row in vectors],
        "component_work_vector_ids": [row.work_vector_id for row in vectors],
        "component_comparison_vector_ids": [row.comparison_vector_id for row in comparisons],
        "component_actual_projection_proof_ids": [row.actual_projection_proof_id for row in proofs],
        "occurrence_reducer_exact_comparison_values": [
            {"axis": axis, "value": value} for axis, value in occurrence_values
        ],
        "shared_resource_path_count": 9,
        "shared_resource_paths": [row["path"] for row in receipts],
        "shared_resource_receipts_complete": True,
        "three_complete_202_counter_record_chains_present": True,
        "route_family_work_vectors_issued": 3,
        "route_family_comparison_vectors_issued": 3,
        "route_family_actual_projection_proofs_issued": 3,
        "all_182_operational_leaves_projected_exactly_once_per_component": True,
        "stage_local_records_retained": 3 * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT,
        "eight_operational_roles_committed_once": True,
        "route_family_exclusivity_preserved": True,
        "occurrence_reducer_exact_comparison_aggregate_present": True,
        "marginal_route_upper_compliance_authority": False,
        "route_choice_authority": False,
        "scientific_terminal_class": "PLAN_CERTIFICATE",
        "scientific_terminal_code": "FULL_GROUND_FALLBACK",
        "official_certificate_coverage_authority": False,
        "logical_occurrence_campaign_closed": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    bundle_id = content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
        bundle_payload,
    )
    return {
        "bundle_id": bundle_id,
        "output_commit_id": output_commit_id,
        "persistent_proof_cache_id": science["persistent_proof_cache_id"],
        "recovery_eligible_checkpoint_id": science["recovery_eligible_checkpoint_id"],
        "comparison_values": occurrence_values,
        "output_bytes": output_bytes,
        "trace_id": trace_id,
    }


def _expected_row_payload(
    *,
    spec_id: str,
    index: int,
    logical_id: str,
    ordinal: int,
    occurrence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_recovery_eligible_campaign_occurrence_row.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_k7_recovery_eligible_preregistered_campaign_v1",
        "campaign_occurrence_spec_id": spec_id,
        "occurrence_index": index,
        "logical_occurrence_id": logical_id,
        "query_ordinal": ordinal,
        "occurrence_accounting_bundle_id": occurrence["bundle_id"],
        "output_commit_id": occurrence["output_commit_id"],
        "persistent_proof_cache_id": occurrence["persistent_proof_cache_id"],
        "recovery_eligible_checkpoint_id": occurrence["recovery_eligible_checkpoint_id"],
        "occurrence_comparison_values": [
            {"axis": axis, "value": value} for axis, value in occurrence["comparison_values"]
        ],
        "terminal_scope": "LOGICAL_OCCURRENCE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "FULL_GROUND_FALLBACK",
        "closure_denominator_included": True,
        "certification_coverage_denominator_included": True,
        "economics_cost_denominator_included": True,
        "abstract_plan_certificate_issued": False,
        "local_recovery_certificate_issued": False,
        "full_ground_fallback_certificate_issued": True,
        "official_execution_allowed": False,
    }


def _prefixes(rows: tuple[dict[str, Any], ...]) -> list[list[dict[str, Any]]]:
    running = {axis: 0 for axis in SHARED_AXES}
    result: list[list[dict[str, Any]]] = []
    for row in rows:
        for item in row["occurrence_comparison_values"]:
            axis, value = item["axis"], item["value"]
            running[axis] = max(running[axis], value) if axis in PEAK_AXES else running[axis] + value
        result.append([{"axis": axis, "value": running[axis]} for axis in SHARED_AXES])
    return result


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCampaignDirectoryVerificationV1:
    preregistration_id: str
    workload_id: str
    closure_id: str
    occurrence_row_ids: tuple[str, ...]
    occurrence_bundle_ids: tuple[str, ...]
    persistent_proof_cache_id: str
    recovery_eligible_checkpoint_id: str
    final_vector_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "verification preregistration"),
            (self.workload_id, "verification workload"),
            (self.closure_id, "verification closure"),
            (self.persistent_proof_cache_id, "verification proof cache"),
            (self.recovery_eligible_checkpoint_id, "verification checkpoint"),
        ):
            _cid(value, label)
        if (
            len(self.occurrence_row_ids) < 2
            or len(self.occurrence_bundle_ids) != len(self.occurrence_row_ids)
            or tuple(axis for axis, _value in self.final_vector_values) != SHARED_AXES
        ):
            _fail("campaign verification summary changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_id": self.workload_id,
            "campaign_closure_id": self.closure_id,
            "ordered_occurrence_row_ids": list(self.occurrence_row_ids),
            "ordered_occurrence_accounting_bundle_ids": list(self.occurrence_bundle_ids),
            "persistent_proof_cache_id": self.persistent_proof_cache_id,
            "recovery_eligible_checkpoint_id": self.recovery_eligible_checkpoint_id,
            "logical_occurrence_count": len(self.occurrence_row_ids),
            "final_vector_values": [
                {"axis": axis, "value": value} for axis, value in self.final_vector_values
            ],
            "bytes_only_replay": True,
            "producer_imported": False,
            "planner_or_ground_kernel_invoked": False,
            "full_registered_denominator_recomputed": True,
            "campaign_orchestration_work_vector_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return content_id(VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_independent_verification_id": self.verification_id}


def verify_recovery_eligible_campaign_directory_bytes_v1(
    campaign_directory: str | Path,
    *,
    expected_preregistration_id: str,
    expected_closure_id: str,
) -> RecoveryEligibleCampaignDirectoryVerificationV1:
    root = Path(campaign_directory).resolve(strict=True)
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        _fail("campaign directory is not private and real")
    prereg_raw, prereg = _read_canonical(
        root / "CAMPAIGN_PREREGISTRATION.json", "campaign preregistration"
    )
    workload_id, runtime, _blobs = _verify_preregistration(
        prereg, expected_preregistration_id
    )
    workload = prereg["workload"]
    count = workload["registered_logical_occurrence_count"]
    expected_root_files = {
        "CAMPAIGN_PREREGISTRATION.json",
        "0000_PREREGISTRATION_COMMITTED.json",
        "CAMPAIGN_CLOSURE.json",
        *(f"OCCURRENCE_{index:04d}_ROW.json" for index in range(1, count + 1)),
        *(f"{index:04d}_OCCURRENCE_BUNDLE_COMMITTED.json" for index in range(1, count + 1)),
    }
    if {path.name for path in root.iterdir() if path.is_file()} != expected_root_files or {
        path.name for path in root.iterdir() if path.is_dir()
    } != {f"occurrence-{index:04d}" for index in range(1, count + 1)}:
        _fail("campaign root inventory changed")

    event_raw, event_doc = _read_canonical(
        root / "0000_PREREGISTRATION_COMMITTED.json", "campaign genesis event"
    )
    del event_raw
    previous_event = _verify_event(
        event_doc,
        sequence=0,
        previous_id=None,
        subject_id=expected_preregistration_id,
        subject_filename="CAMPAIGN_PREREGISTRATION.json",
        subject_raw=prereg_raw,
        logical_occurrence_id=None,
    )
    event_ids = [previous_event]
    verified_rows: list[dict[str, Any]] = []
    row_ids: list[str] = []
    bundle_ids: list[str] = []
    cache_ids: set[str] = set()
    checkpoint_ids: set[str] = set()
    for index in range(1, count + 1):
        logical_id = workload["ordered_logical_occurrence_ids"][index - 1]
        ordinal = workload["ordered_query_ordinals"][index - 1]
        spec_id = workload["ordered_occurrence_spec_ids"][index - 1]
        occurrence = _verify_occurrence_output(
            root / f"occurrence-{index:04d}",
            logical_occurrence_id=logical_id,
            prereg_runtime=runtime,
        )
        row_name = f"OCCURRENCE_{index:04d}_ROW.json"
        row_raw, row_doc = _read_canonical(root / row_name, f"campaign occurrence row {index}")
        row_id, row_payload = _content_document(
            row_doc,
            id_field="campaign_occurrence_row_id",
            domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
            label="campaign occurrence row",
        )
        expected_row = _expected_row_payload(
            spec_id=spec_id,
            index=index,
            logical_id=logical_id,
            ordinal=ordinal,
            occurrence=occurrence,
        )
        if row_payload != expected_row:
            _fail("campaign occurrence row differs from independent replay")
        event_name = f"{index:04d}_OCCURRENCE_BUNDLE_COMMITTED.json"
        _event_raw, event_doc = _read_canonical(root / event_name, f"campaign event {index}")
        previous_event = _verify_event(
            event_doc,
            sequence=index,
            previous_id=previous_event,
            subject_id=row_id,
            subject_filename=row_name,
            subject_raw=row_raw,
            logical_occurrence_id=logical_id,
        )
        event_ids.append(previous_event)
        verified_rows.append(row_payload)
        row_ids.append(row_id)
        bundle_ids.append(occurrence["bundle_id"])
        cache_ids.add(occurrence["persistent_proof_cache_id"])
        checkpoint_ids.add(occurrence["recovery_eligible_checkpoint_id"])
    if len(cache_ids) != 1 or len(checkpoint_ids) != 1:
        _fail("campaign did not reuse one proof cache/checkpoint")

    _closure_raw, closure = _read_canonical(root / "CAMPAIGN_CLOSURE.json", "campaign closure")
    closure_id, closure_payload = _content_document(
        closure,
        id_field="campaign_closure_id",
        domain=CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN,
        label="campaign closure",
    )
    if closure_id != _cid(expected_closure_id, "expected campaign closure"):
        _fail("campaign closure is not the externally expected identity")
    prefixes = _prefixes(tuple(verified_rows))
    expected_closure = {
        "schema": "acfqp.construction_k7_recovery_eligible_campaign_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.117",
        "profile_key": "construction_k7_recovery_eligible_preregistered_campaign_v1",
        "campaign_preregistration_id": expected_preregistration_id,
        "campaign_workload_id": workload_id,
        "runtime_preparation_id": runtime["recovery_eligible_runtime_preparation_id"],
        "ordered_occurrence_row_ids": row_ids,
        "ordered_commit_event_ids": event_ids,
        "registered_logical_occurrence_ids": workload["ordered_logical_occurrence_ids"],
        "logical_occurrence_count": count,
        "closure_denominator": count,
        "certification_coverage_denominator": count,
        "economics_cost_denominator": count,
        "plan_certificate_count": count,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": 0,
        "abstract_plan_certificate_count": 0,
        "local_ground_recovery_certificate_count": 0,
        "full_ground_fallback_certificate_count": count,
        "vector_prefix_totals": prefixes,
        "full_registered_denominator_recomputed": True,
        "occurrence_deletion_observed": False,
        "shared_persistent_proof_cache_reused_across_all_occurrences": True,
        "campaign_denominator_closure_issued": True,
        "campaign_orchestration_work_vector_issued": False,
        "cross_occurrence_overlay_persistence_authority": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if closure_payload != expected_closure:
        _fail("campaign closure differs from independent denominator replay")
    final_values = tuple(
        (row["axis"], row["value"]) for row in prefixes[-1]
    )
    return RecoveryEligibleCampaignDirectoryVerificationV1(
        expected_preregistration_id,
        workload_id,
        closure_id,
        tuple(row_ids),
        tuple(bundle_ids),
        next(iter(cache_ids)),
        next(iter(checkpoint_ids)),
        final_values,
    )


__all__ = (
    "ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error",
    "RecoveryEligibleCampaignDirectoryVerificationV1",
    "verify_recovery_eligible_campaign_directory_bytes_v1",
)
