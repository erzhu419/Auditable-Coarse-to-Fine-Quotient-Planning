"""Producer-free replay of every V24 CounterRecord, vector, and receipt."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
EXPECTED_CAMPAIGN_ID = "3eba16cb6db6d0797991acbde6103d423741668730313385e404949b5907ab72"
EXPECTED_CANONICAL_BYTE_COUNT = 443508
EXPECTED_CANONICAL_SHA256 = "e43c8fa9f5281b89525249a34c48a2f5351b0d46f9c946bfd3f7a187d45d91f2"
EXPECTED_VERIFICATION_ID = "79749d6a1d689ee4cb8740d2b20393d11403d29471f9a218e4a4a5b36720aca7"
EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT = 3004
EXPECTED_VERIFICATION_CANONICAL_SHA256 = "bed223adf17c30d3d11f714f254a5f165e9186c84501ebd674abd4fdefabe9ce"


class ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
    RuntimeError
):
    """The campaign bytes, bundle DAG, or accounting projection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
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
    try:
        identity = parse_content_id(document[id_key])
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
            f"{label} identity changed"
        ) from error
    payload = {key: value for key, value in document.items() if key != id_key}
    if content_id(domain, payload) != identity:
        _fail(f"{label} content identity changed")
    return identity


_OPERATIONAL_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "expression_accounted_preregistration_id",
    "subject_id",
    "window_role",
    "measurement",
    "work_vector",
    "comparison_vector",
    "actual_projection_proof",
    "native_zero_attestation",
    "evidence",
    "output_bytes_fixed_point",
    "fixed_point_iteration",
    "evaluation_work_in_operational_vector",
    "official_execution_allowed",
    "expression_accounted_counter_bundle_id",
}

_EVALUATION_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "expression_accounted_preregistration_id",
    "subject_id",
    "window_role",
    "measurement",
    "work_vector",
    "comparison_vector",
    "actual_projection_proof",
    "native_zero_attestation",
    "evidence",
    "output_bytes_fixed_point",
    "fixed_point_iteration",
    "evaluation_lane_excluded_from_operational_comparison",
    "official_execution_allowed",
    "expression_accounted_counter_bundle_id",
}

_MEASUREMENT_FIELDS = {
    "schema",
    "schema_version",
    "expression_accounted_preregistration_id",
    "subject_id",
    "window_role",
    "lane",
    "measured_values",
    "native_measurement_not_legacy_summary_translation",
    "expression_accounting_measurement_id",
}

_SUMMARY_FIELDS = {
    "counter_bundle_id",
    "window_role",
    "work_vector_id",
    "comparison_vector_id",
    "actual_projection_proof_id",
    "native_zero_attestation_id",
    "output_key",
    "canonical_byte_count",
    "canonical_sha256",
    "charged_output_bytes",
}


def _measurement(
    document: Mapping[str, Any],
    *,
    subject_id: str,
    window_role: str,
    lane: str,
    vector: WorkVectorV1,
) -> str:
    if type(document) is not dict or set(document) != _MEASUREMENT_FIELDS:
        _fail("measurement exact field set changed")
    identity = _document_id(
        document,
        id_key="expression_accounting_measurement_id",
        domain=pre.FUTURE_DOMAINS["measurement"],
        label="accounting measurement",
    )
    if (
        document["schema"]
        != "acfqp.standard_2048_expression_accounting_measurement.v24"
        or document["schema_version"] != SCHEMA_VERSION
        or document["expression_accounted_preregistration_id"]
        != pre.PREREGISTRATION_ID
        or document["subject_id"] != subject_id
        or document["window_role"] != window_role
        or document["lane"] != lane
        or document["native_measurement_not_legacy_summary_translation"]
        is not True
    ):
        _fail("measurement semantic binding changed")
    expected_paths = (
        pre.SHARED_RESOURCE_PATHS
        if lane == "OPERATIONAL"
        else (
            "evaluation.hash_invocations",
            "evaluation.io_mounted_bytes_peak",
            "evaluation.io_output_bytes",
            "evaluation.io_read_bytes",
            "evaluation.io_staged_bytes",
            "evaluation.memory_working_bytes_peak",
            "evaluation.process_launches",
            "evaluation.semantic_integrity_checks",
            "evaluation.semantic_protocol_checks",
        )
    )
    expected_rows = [
        {"path": path, "value": vector.value(path)} for path in expected_paths
    ]
    if document["measured_values"] != expected_rows:
        _fail("measurement values differ from native CounterRecords")
    if any(record.recorder_id != identity for record in vector.records):
        _fail("CounterRecord recorder identity differs from its measurement")
    return identity


@dataclass(frozen=True, slots=True)
class _VerifiedBundleV24:
    summary: Mapping[str, Any]
    document: Mapping[str, Any]
    vector: WorkVectorV1
    comparison: ComparisonVectorV1 | None
    raw: bytes


def _expected_route_binding(
    window_role: str,
) -> tuple[RouteKindEnum, ActualWorkScope]:
    if window_role == "ABSTRACT_CERTIFICATE_AND_SELECTED_TARGET_EXECUTION":
        return (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
        )
    if window_role in {
        "MODEL_ACQUISITION_AND_SELECTION",
        "MODEL_PROOF_AND_FREEZE",
        "EPISODE_WORKER_PROCESS_AND_TRANSPORT",
        "CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
    }:
        return RouteKindEnum.ABSTRACT_FAILED_PREFIX, ActualWorkScope.COMMON_PREFIX
    _fail("unknown operational accounting window role")


def _verify_summary(
    summary: Mapping[str, Any], *, root: Path
) -> _VerifiedBundleV24:
    if type(summary) is not dict or set(summary) != _SUMMARY_FIELDS:
        _fail("bundle summary exact field set changed")
    if (
        type(summary["output_key"]) is not str
        or not summary["output_key"]
        or Path(summary["output_key"]).is_absolute()
        or ".." in Path(summary["output_key"]).parts
    ):
        _fail("bundle output key changed")
    path = root / summary["output_key"]
    if not path.is_file() or path.is_symlink():
        _fail("bundle output file is absent or indirect")
    raw = path.read_bytes()
    document = _object(raw, summary["output_key"])
    identity = _document_id(
        document,
        id_key="expression_accounted_counter_bundle_id",
        domain=pre.FUTURE_DOMAINS["counter_bundle"],
        label="counter bundle",
    )
    if (
        summary["counter_bundle_id"] != identity
        or summary["window_role"] != document.get("window_role")
        or summary["canonical_byte_count"] != len(raw)
        or summary["canonical_sha256"] != hashlib.sha256(raw).hexdigest()
        or summary["charged_output_bytes"]
        != document.get("output_bytes_fixed_point")
    ):
        _fail("bundle summary differs from retained canonical bytes")
    registry = registry_v9.official_counter_registry_v9()
    try:
        vector = WorkVectorV1.from_dict(document["work_vector"], registry)
        zero = NativeZeroAttestationV1.from_dict(
            document["native_zero_attestation"]
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
            "retained WorkVector or native-zero attestation is invalid"
        ) from error
    if zero != NativeZeroAttestationV1.derive(vector, registry):
        _fail("native-zero attestation was not derived from exact records")
    if (
        vector.subject_id != document.get("subject_id")
        or summary["work_vector_id"] != vector.work_vector_id
        or summary["native_zero_attestation_id"]
        != zero.native_zero_attestation_id
        or len(vector.records) != len(registry.leaves)
        or document.get("expression_accounted_preregistration_id")
        != pre.PREREGISTRATION_ID
        or document.get("official_execution_allowed") is not False
        or type(document.get("fixed_point_iteration")) is not int
        or not 0 <= document["fixed_point_iteration"] < 16
    ):
        _fail("counter bundle identity or native completeness changed")
    role = document["window_role"]
    charged = document["output_bytes_fixed_point"]
    external = 0
    if role == "EPISODE_WORKER_PROCESS_AND_TRANSPORT":
        evidence = document.get("evidence")
        if (
            type(evidence) is not dict
            or type(evidence.get("worker_reply_byte_count")) is not int
            or evidence["worker_reply_byte_count"] <= 0
            or type(evidence.get("worker_reply_sha256")) is not str
        ):
            _fail("worker transport external bytes evidence changed")
        external = evidence["worker_reply_byte_count"]
    if charged != len(raw) + external:
        _fail("bundle output-byte fixed point changed")
    lane = document.get("measurement", {}).get("lane")
    _measurement(
        document["measurement"],
        subject_id=vector.subject_id,
        window_role=role,
        lane=lane,
        vector=vector,
    )
    if lane == "OPERATIONAL":
        if set(document) != _OPERATIONAL_BUNDLE_FIELDS:
            _fail("operational counter bundle exact field set changed")
        if (
            document["schema"]
            != "acfqp.standard_2048_expression_operational_counter_bundle.v24"
            or document["evaluation_work_in_operational_vector"] is not False
        ):
            _fail("operational bundle lane claim changed")
        try:
            comparison = ComparisonVectorV1.from_dict(
                document["comparison_vector"]
            )
            proof = ActualProjectionProofV1.from_dict(
                document["actual_projection_proof"]
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
                "retained comparison or projection proof is invalid"
            ) from error
        comparison_profile = registry_v9.official_comparison_profile_v9(registry)
        actual_profile = registry_v9.official_actual_projection_profile_v9(
            registry, comparison_profile
        )
        try:
            recomputed = verify_actual_projection_v1(
                proof,
                vector,
                comparison,
                registry,
                comparison_profile,
                actual_profile,
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7Standard2048ExpressionAccountedIndependentVerifierV24Error(
                "actual comparison is not the exact projection"
            ) from error
        route_kind, work_scope = _expected_route_binding(role)
        if (
            vector.route_kind is not route_kind
            or proof.work_scope is not work_scope
            or proof.source_lane is not LaneEnum.OPERATIONAL
            or recomputed != comparison
            or summary["comparison_vector_id"]
            != comparison.comparison_vector_id
            or summary["actual_projection_proof_id"]
            != proof.actual_projection_proof_id
        ):
            _fail("operational route/scope/projection binding changed")
        return _VerifiedBundleV24(summary, document, vector, comparison, raw)
    if lane == "EVALUATION":
        if set(document) != _EVALUATION_BUNDLE_FIELDS:
            _fail("evaluation counter bundle exact field set changed")
        if (
            document["schema"]
            != "acfqp.standard_2048_expression_evaluation_counter_bundle.v24"
            or document["comparison_vector"] is not None
            or document["actual_projection_proof"] is not None
            or document[
                "evaluation_lane_excluded_from_operational_comparison"
            ]
            is not True
            or summary["comparison_vector_id"] is not None
            or summary["actual_projection_proof_id"] is not None
            or any(vector.value(leaf.path) for leaf in registry.operational_leaves)
        ):
            _fail("evaluation work entered operational comparison")
        return _VerifiedBundleV24(summary, document, vector, None, raw)
    _fail("counter bundle lane changed")


def _campaign_summaries(document: Mapping[str, Any]) -> tuple[
    tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]
]:
    operational = list(document["model_operational_bundles"])
    evaluation = [document["model_evaluation_bundle"]]
    for episode in document["episodes"]:
        operational.append(episode["worker_bundle"])
        for decision in episode["decisions"]:
            operational.append(decision["operational_bundle"])
            if decision["evaluation_bundle"] is not None:
                evaluation.append(decision["evaluation_bundle"])
    operational.append(document["campaign_bundle"])
    return tuple(operational), tuple(evaluation)


def _accumulate(
    totals: dict[str, int], values: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    profile = registry_v9.official_comparison_profile_v9()
    reducers = {row.name: row.reducer for row in profile.axes}
    result = dict(totals)
    for axis, value in values:
        if reducers[axis] is ReducerEnum.SUM:
            result[axis] += value
        else:
            result[axis] = max(result[axis], value)
    return result


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionAccountedIndependentVerificationV24:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounting verification is not an object")
        return document


_ISSUER = object()


def verify_standard_2048_expression_accounting_bytes_independently_v24(
    campaign_bytes: bytes,
    output_root: Path,
) -> Standard2048ExpressionAccountedIndependentVerificationV24:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("accounting output root is absent")
    campaign = _object(campaign_bytes, "accounted campaign")
    campaign_id = _document_id(
        campaign,
        id_key="expression_accounted_campaign_id",
        domain=pre.FUTURE_DOMAINS["campaign"],
        label="accounted campaign",
    )
    if (
        (EXPECTED_CAMPAIGN_ID != "0" * 64 and campaign_id != EXPECTED_CAMPAIGN_ID)
        or (EXPECTED_CANONICAL_BYTE_COUNT and len(campaign_bytes) != EXPECTED_CANONICAL_BYTE_COUNT)
        or (
            EXPECTED_CANONICAL_SHA256 != "0" * 64
            and hashlib.sha256(campaign_bytes).hexdigest()
            != EXPECTED_CANONICAL_SHA256
        )
        or campaign.get("expression_accounted_preregistration")
        != pre.freeze_standard_2048_expression_accounted_preregistration_v24().to_document()
    ):
        _fail("frozen full accounted campaign bytes changed")
    operational_summaries, evaluation_summaries = _campaign_summaries(campaign)
    if (
        len(operational_summaries) != 135
        or len(evaluation_summaries) != 13
        or campaign.get("operational_work_vector_count")
        != len(operational_summaries)
        or campaign.get("evaluation_work_vector_count")
        != len(evaluation_summaries)
    ):
        _fail("campaign WorkVector inventory changed")
    all_summaries = (*operational_summaries, *evaluation_summaries)
    output_keys = [row.get("output_key") for row in all_summaries]
    if (
        len(set(output_keys)) != len(output_keys)
        or {path.relative_to(output_root).as_posix() for path in output_root.rglob("*.json")}
        != set(output_keys)
    ):
        _fail("retained bundle file inventory changed")
    operational = tuple(
        _verify_summary(summary, root=output_root)
        for summary in operational_summaries
    )
    evaluation = tuple(
        _verify_summary(summary, root=output_root)
        for summary in evaluation_summaries
    )
    totals = {axis: 0 for axis in SHARED_AXES}
    prefix = []
    for sequence_index, bundle in enumerate(operational):
        if bundle.comparison is None:
            raise AssertionError("operational bundle lost comparison")
        totals = _accumulate(totals, bundle.comparison.values)
        prefix.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": bundle.vector.work_vector_id,
                "comparison_vector_id": bundle.comparison.comparison_vector_id,
                "subject_id": bundle.vector.subject_id,
                "route_kind": bundle.vector.route_kind.value,
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    final_totals = [
        {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
    ]
    registry = registry_v9.official_counter_registry_v9()
    evaluation_totals = {
        path: sum(bundle.vector.value(path) for bundle in evaluation)
        for path in registry.by_path
        if path.startswith("evaluation.")
    }
    model_events = sum(
        bundle.vector.value(path)
        for bundle in operational
        for path in pre.MODEL_OPERATIONAL_PATHS
    )
    label_queries = sum(
        bundle.vector.value("model.target_probability_labels_acquired")
        for bundle in operational
    )
    planning_rows = sum(
        bundle.vector.value("common.abstract_bellman_backups")
        for bundle in operational
    )
    planning_outcomes = sum(
        bundle.vector.value("common.abstract_support_outcome_evaluations")
        for bundle in operational
    )
    target_steps = sum(
        bundle.vector.value("target.execution_ground_steps")
        for bundle in operational
    )
    if (
        campaign.get("vector_prefix_totals") != prefix
        or campaign.get("final_operational_comparison_totals") != final_totals
        or campaign.get("evaluation_lane_totals") != evaluation_totals
        or campaign.get("model_operational_nonkernel_event_count") != model_events
        or campaign.get("operational_target_probability_label_query_count")
        != label_queries
        or campaign.get("unique_operational_target_probability_label_count")
        != 4
        or campaign.get("duplicate_operational_label_query_count") != 0
        or campaign.get("operational_abstract_bellman_backup_count")
        != planning_rows
        or campaign.get("operational_abstract_support_outcome_evaluation_count")
        != planning_outcomes
        or campaign.get("operational_target_execution_ground_step_count")
        != target_steps
        or campaign.get("episode_count") != 4
        or campaign.get("decision_count") != 128
        or campaign.get("model_certificate_count") != 128
        or campaign.get("local_ground_recovery_count") != 0
        or campaign.get("cold_evaluation_checkpoint_count") != 12
        or label_queries != 4
        or target_steps != 128
    ):
        _fail("campaign aggregate differs from independently replayed vectors")
    if any(
        campaign.get(key) is not expected
        for key, expected in {
            "all_registered_decisions_use_synthesized_world_model": True,
            "all_registered_decisions_certificate_before_target_execution": True,
            "all_required_counter_leaves_have_explicit_native_records": True,
            "all_nine_shared_resource_paths_have_measurement_receipts": True,
            "evaluation_replay_excluded_from_operational_comparison": True,
            "measurement_replays_revealed_target_not_fresh_blind_science": True,
            "total_operational_work_saving_claimed": False,
            "full_standard_2048_game_completed": False,
            "official_execution_allowed": False,
        }.items()
    ) or (
        campaign.get("official_scalar_cost") is not None
        or campaign.get("official_N_break_even") is not None
        or campaign.get("counter_completeness_gate_status") != "NOT_RUN"
        or campaign.get("workload_economics_gate_status") != "NOT_RUN"
    ):
        _fail("campaign claim locks changed")
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_independent_verification.v24",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_accounted_campaign_id": campaign_id,
        "counter_registry_id": profiles["counter_registry"]["counter_registry_id"],
        "stage_profile_id": profiles["stage_profile"]["stage_profile_id"],
        "comparison_profile_id": profiles["comparison_profile"]["comparison_profile_id"],
        "actual_projection_profile_id": profiles["actual_projection_profile"]["actual_projection_profile_id"],
        "operational_work_vector_count": len(operational),
        "evaluation_work_vector_count": len(evaluation),
        "counter_record_count": sum(len(bundle.vector.records) for bundle in (*operational, *evaluation)),
        "every_counter_record_and_native_zero_replayed": True,
        "every_operational_comparison_recomputed": True,
        "every_output_byte_fixed_point_replayed": True,
        "all_nine_shared_resource_receipts_replayed": True,
        "evaluation_excluded_from_operational_comparison": True,
        "final_operational_comparison_totals": final_totals,
        "evaluation_lane_totals": evaluation_totals,
        "four_actual_probability_queries_replayed": label_queries == 4,
        "one_hundred_twenty_eight_target_execution_steps_replayed": target_steps == 128,
        "semantic_planning_replay_in_this_verifier": False,
        "accounting_bundle_replay_result": "PASS",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(pre.FUTURE_DOMAINS["verification"], payload)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen accounting verification identity changed")
    raw = canonical_json_bytes(
        {
            **payload,
            "expression_accounted_verification_id": verification_id,
        }
    )
    if (
        len(raw) != EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest()
        != EXPECTED_VERIFICATION_CANONICAL_SHA256
    ):
        _fail("frozen accounting verification bytes changed")
    return Standard2048ExpressionAccountedIndependentVerificationV24(
        _ISSUER, raw, campaign_id, verification_id
    )


__all__ = (
    "EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_VERIFICATION_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExpressionAccountedIndependentVerificationV24",
    "verify_standard_2048_expression_accounting_bytes_independently_v24",
)
