"""Producer-free replay of every V34 CounterRecord, vector, and receipt."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v26 as v26
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v27 as v27
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v28 as v28
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v29 as v29
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v30 as v30
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v31 as v31
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v32 as v32
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v33 as v33
from acfqp import construction_k7_standard_2048_expression_full_accounting_preregistration_v34 as pre
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
EXPECTED_CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT = 0
EXPECTED_VERIFICATION_CANONICAL_SHA256 = "0" * 64
_FINAL_EPISODE_IDS = (
    "43a946ba2fe68d3ae10a30fd36bf7fc28ff7cacb5c976c5c5febec1bfb04ed8b",
    "2e0b83e1ae2f1e154328b9644d337f43116803189f654f3182e7c60d2100a99f",
    "2a4a05215e21defb6949883af68f59d7af41dc0e56b229776fbb3312a277d089",
    "1c03b5d5bff535a2359b437a2cfad8d91c35af8c5c69282ba90b31f924e2f229",
)
_SOURCE_EPISODE_IDS = (
    (None,) * 4,
    v26.CHECKPOINT_EPISODE_IDS,
    v27.CHECKPOINT_EPISODE_IDS,
    v28.CHECKPOINT_EPISODE_IDS,
    v29.CHECKPOINT_EPISODE_IDS,
    v30.CHECKPOINT_EPISODE_IDS,
    v31.CHECKPOINT_EPISODE_IDS,
    v32.CHECKPOINT_EPISODE_IDS,
    v33.CHECKPOINT_EPISODE_IDS,
)
_OUTPUT_EPISODE_IDS = (
    v26.CHECKPOINT_EPISODE_IDS,
    v27.CHECKPOINT_EPISODE_IDS,
    v28.CHECKPOINT_EPISODE_IDS,
    v29.CHECKPOINT_EPISODE_IDS,
    v30.CHECKPOINT_EPISODE_IDS,
    v31.CHECKPOINT_EPISODE_IDS,
    v32.CHECKPOINT_EPISODE_IDS,
    v33.CHECKPOINT_EPISODE_IDS,
    _FINAL_EPISODE_IDS,
)


class ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
    RuntimeError
):
    """The campaign bytes, bundle DAG, or accounting projection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
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
        raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
            f"{label} identity changed"
        ) from error
    payload = {key: value for key, value in document.items() if key != id_key}
    if content_id(domain, payload) != identity:
        _fail(f"{label} content identity changed")
    return identity


_OPERATIONAL_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "expression_full_accounting_preregistration_id",
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
    "expression_full_accounting_counter_bundle_id",
}

_EVALUATION_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "expression_full_accounting_preregistration_id",
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
    "expression_full_accounting_counter_bundle_id",
}

_MEASUREMENT_FIELDS = {
    "schema",
    "schema_version",
    "expression_full_accounting_preregistration_id",
    "subject_id",
    "window_role",
    "lane",
    "measured_values",
    "native_measurement_not_legacy_summary_translation",
    "expression_full_accounting_measurement_id",
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

_CAMPAIGN_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "expression_full_accounting_preregistration",
    "model_operational_bundles",
    "model_evaluation_bundle",
    "segments",
    "segment_count",
    "logical_occurrence_count",
    "complete_decision_count",
    "model_certificate_count",
    "won_occurrence_count",
    "lost_occurrence_count",
    "terminal_occurrence_count",
    "operational_work_vector_count",
    "evaluation_work_vector_count",
    "campaign_bundle",
    "vector_prefix_totals",
    "final_operational_comparison_totals",
    "evaluation_lane_totals",
    "operational_target_probability_label_query_count",
    "unique_operational_target_probability_label_count",
    "additional_operational_target_probability_label_count",
    "strict_no_prior_target_probability_label_count",
    "target_probability_label_fraction_of_no_prior",
    "certified_decisions_per_acquired_target_label",
    "all_3187_decisions_rerun_under_native_counter_windows",
    "all_required_counter_leaves_have_explicit_native_records",
    "all_nine_shared_resource_paths_have_measurement_receipts",
    "evaluation_replay_excluded_from_operational_comparison",
    "terminal_occurrences_retained_in_denominator",
    "summary_to_counter_translation_used",
    "registered_profile_counter_completeness_candidate",
    "full_standard_2048_campaign_terminalized",
    "tile_2048_reached",
    "sample_tax_reduced_on_registered_label_axis",
    "broad_iid_sample_efficiency_claimed",
    "total_operational_work_saving_claimed",
    "official_execution_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "expression_full_accounted_campaign_id",
}

_SEGMENT_FIELDS = {
    "segment_ordinal",
    "profile",
    "active_worker_count",
    "terminal_carry_forward_count",
    "terminal_carry_forward",
    "decision_count",
    "cold_evaluation_checkpoint_count",
    "process_bundle",
    "episodes",
}

_EPISODE_FIELDS = {
    "episode_index",
    "episode_id",
    "source_episode_id",
    "decision_count",
    "closure_reason",
    "final_state",
    "tile_2048_reached",
    "operational_bundle",
    "evaluation_bundle",
}

_TERMINAL_FIELDS = {
    "episode_index",
    "source_episode_id",
    "output_episode_id",
    "source_status",
    "source_board_ranks",
    "cumulative_decision_count",
    "decision_count",
    "route_work_vector_id",
    "zero_decision_work",
    "retained_in_campaign_denominator",
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
        id_key="expression_full_accounting_measurement_id",
        domain=pre.FUTURE_DOMAINS["measurement"],
        label="accounting measurement",
    )
    if (
        document["schema"]
        != "acfqp.standard_2048_expression_accounting_measurement.v34"
        or document["schema_version"] != SCHEMA_VERSION
        or document["expression_full_accounting_preregistration_id"]
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
class _VerifiedBundleV34:
    summary: Mapping[str, Any]
    document: Mapping[str, Any]
    vector: WorkVectorV1
    comparison: ComparisonVectorV1 | None
    raw: bytes


def _expected_route_binding(
    window_role: str,
) -> tuple[RouteKindEnum, ActualWorkScope]:
    if window_role == "SEGMENT_EPISODE_PLANNING_AND_TARGET_EXECUTION":
        return (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
        )
    if window_role in {
        "MODEL_ACQUISITION_AND_SELECTION",
        "MODEL_PROOF_AND_FREEZE",
        "SEGMENT_PROCESS_SUPERVISION",
        "CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
    }:
        return RouteKindEnum.ABSTRACT_FAILED_PREFIX, ActualWorkScope.COMMON_PREFIX
    _fail("unknown operational accounting window role")


def _verify_summary(
    summary: Mapping[str, Any], *, root: Path
) -> _VerifiedBundleV34:
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
        id_key="expression_full_accounting_counter_bundle_id",
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
        raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
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
        or document.get("expression_full_accounting_preregistration_id")
        != pre.PREREGISTRATION_ID
        or document.get("official_execution_allowed") is not False
        or type(document.get("fixed_point_iteration")) is not int
        or not 0 <= document["fixed_point_iteration"] < 16
    ):
        _fail("counter bundle identity or native completeness changed")
    role = document["window_role"]
    charged = document["output_bytes_fixed_point"]
    external = 0
    if role == "SEGMENT_EPISODE_PLANNING_AND_TARGET_EXECUTION":
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
            != "acfqp.standard_2048_expression_operational_counter_bundle.v34"
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
            raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
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
            raise ConstructionK7Standard2048ExpressionFullAccountedIndependentVerifierV34Error(
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
        return _VerifiedBundleV34(summary, document, vector, comparison, raw)
    if lane == "EVALUATION":
        if set(document) != _EVALUATION_BUNDLE_FIELDS:
            _fail("evaluation counter bundle exact field set changed")
        if (
            document["schema"]
            != "acfqp.standard_2048_expression_evaluation_counter_bundle.v34"
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
        return _VerifiedBundleV34(summary, document, vector, None, raw)
    _fail("counter bundle lane changed")


def _verify_campaign_structure(
    campaign: Mapping[str, Any],
) -> tuple[int, int, int, int]:
    if type(campaign) is not dict or set(campaign) != _CAMPAIGN_FIELDS:
        _fail("campaign exact field set changed")
    if (
        campaign["schema"]
        != "acfqp.standard_2048_expression_full_accounted_campaign.v34"
        or campaign["schema_version"] != SCHEMA_VERSION
        or campaign["profile_key"] != pre.PROFILE_KEY
        or type(campaign["segments"]) is not list
        or type(campaign["model_operational_bundles"]) is not list
        or len(campaign["model_operational_bundles"]) != 2
        or any(
            type(row) is not dict
            for row in campaign["model_operational_bundles"]
        )
        or type(campaign["model_evaluation_bundle"]) is not dict
        or type(campaign["campaign_bundle"]) is not dict
        or campaign["segment_count"] != 9
        or len(campaign["segments"]) != 9
    ):
        _fail("campaign schema or segment cardinality changed")
    expected_profiles = (
        "V24_INITIAL_32",
        "V26",
        "V27",
        "V28",
        "V29",
        "V30",
        "V31",
        "V32",
        "V33",
    )
    expected_decisions = (128, 128, 128, 128, 256, 512, 938, 765, 204)
    expected_active = (4, 4, 4, 4, 4, 4, 4, 3, 2)
    expected_terminal = (0, 0, 0, 0, 0, 0, 0, 1, 2)
    decision_total = 0
    cold_total = 0
    won = 0
    lost = 0
    for ordinal, segment in enumerate(campaign["segments"]):
        if type(segment) is not dict or set(segment) != _SEGMENT_FIELDS:
            _fail("segment exact field set changed")
        episodes = segment["episodes"]
        terminals = segment["terminal_carry_forward"]
        if (
            segment["segment_ordinal"] != ordinal
            or segment["profile"] != expected_profiles[ordinal]
            or segment["active_worker_count"] != expected_active[ordinal]
            or segment["terminal_carry_forward_count"]
            != expected_terminal[ordinal]
            or segment["decision_count"] != expected_decisions[ordinal]
            or type(episodes) is not list
            or len(episodes) != expected_active[ordinal]
            or type(terminals) is not list
            or len(terminals) != expected_terminal[ordinal]
        ):
            _fail("registered segment inventory changed")
        indexes = []
        episode_decisions = 0
        for episode in episodes:
            if type(episode) is not dict or set(episode) != _EPISODE_FIELDS:
                _fail("segment episode exact field set changed")
            if type(episode["operational_bundle"]) is not dict or (
                episode["evaluation_bundle"] is not None
                and type(episode["evaluation_bundle"]) is not dict
            ):
                _fail("segment episode bundle summary changed")
            index = episode["episode_index"]
            if type(index) is not int or not 0 <= index < 4:
                _fail("segment episode index changed")
            indexes.append(index)
            if (
                type(episode["decision_count"]) is not int
                or episode["decision_count"] <= 0
                or episode["episode_id"] != _OUTPUT_EPISODE_IDS[ordinal][index]
                or episode["operational_bundle"].get("window_role")
                != "SEGMENT_EPISODE_PLANNING_AND_TARGET_EXECUTION"
            ):
                _fail("segment episode accounting binding changed")
            episode_decisions += episode["decision_count"]
            if episode["evaluation_bundle"] is not None:
                if (
                    episode["evaluation_bundle"].get("window_role")
                    != "SEGMENT_COLD_CHECKPOINT_STANDALONE_REPLAY"
                ):
                    _fail("segment evaluation role changed")
            if ordinal == 8:
                final_state = episode.get("final_state")
                if type(final_state) is not dict:
                    _fail("final occurrence state changed")
                status = final_state.get("status")
                if status == "WON":
                    won += 1
                elif status == "LOST":
                    lost += 1
                else:
                    _fail("final active occurrence is not terminal")
        if indexes != sorted(indexes) or len(set(indexes)) != len(indexes):
            _fail("segment episode ordering changed")
        if episode_decisions != segment["decision_count"]:
            _fail("segment decision sum changed")
        if (
            type(segment["cold_evaluation_checkpoint_count"]) is not int
            or segment["cold_evaluation_checkpoint_count"] < 0
        ):
            _fail("segment cold-checkpoint count changed")
        if (
            type(segment["process_bundle"]) is not dict
            or segment["process_bundle"].get("window_role")
            != "SEGMENT_PROCESS_SUPERVISION"
        ):
            _fail("segment process-supervision bundle changed")
        for terminal in terminals:
            if type(terminal) is not dict or set(terminal) != _TERMINAL_FIELDS:
                _fail("terminal carry-forward exact field set changed")
            terminal_index = terminal["episode_index"]
            if (
                type(terminal_index) is not int
                or not 0 <= terminal_index < 4
                or terminal["decision_count"] != 0
                or terminal["source_episode_id"]
                != _SOURCE_EPISODE_IDS[ordinal][terminal_index]
                or terminal["output_episode_id"]
                != _OUTPUT_EPISODE_IDS[ordinal][terminal_index]
                or terminal["route_work_vector_id"] is not None
                or terminal["zero_decision_work"] is not True
                or terminal["retained_in_campaign_denominator"] is not True
                or terminal["source_status"] not in {"WON", "LOST"}
            ):
                _fail("terminal occurrence emitted route work or left denominator")
            if ordinal == 8:
                if terminal["source_status"] == "WON":
                    won += 1
                else:
                    lost += 1
        decision_total += segment["decision_count"]
        cold_total += segment["cold_evaluation_checkpoint_count"]
    return decision_total, cold_total, won, lost


def _campaign_summaries(document: Mapping[str, Any]) -> tuple[
    tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]
]:
    operational = list(document["model_operational_bundles"])
    evaluation = [document["model_evaluation_bundle"]]
    for segment in document["segments"]:
        for episode in segment["episodes"]:
            operational.append(episode["operational_bundle"])
            if episode["evaluation_bundle"] is not None:
                evaluation.append(episode["evaluation_bundle"])
        if segment["process_bundle"] is not None:
            operational.append(segment["process_bundle"])
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


def _subject_id(role: str, evidence: Mapping[str, Any]) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["measurement"],
        {
            "schema": "acfqp.standard_2048_expression_full_accounting_subject.v34",
            "schema_version": SCHEMA_VERSION,
            "expression_full_accounting_preregistration_id": pre.PREREGISTRATION_ID,
            "role": role,
            "evidence": dict(evidence),
        },
    )


def _verify_native_segment_evidence(
    campaign: Mapping[str, Any],
    bundles: Mapping[str, _VerifiedBundleV34],
) -> int:
    registry = registry_v9.official_counter_registry_v9()
    total_cold = 0
    for segment in campaign["segments"]:
        segment_cold = 0
        for episode in segment["episodes"]:
            operational = bundles[episode["operational_bundle"]["counter_bundle_id"]]
            if operational.vector.subject_id != episode["episode_id"]:
                _fail("episode WorkVector subject differs from episode identity")
            evidence = operational.document.get("evidence")
            if type(evidence) is not dict or set(evidence) != {
                "task",
                "worker_reply",
                "worker_reply_sha256",
                "worker_reply_byte_count",
                "observed_worker_ru_maxrss_within_preregistered_cap",
            }:
                _fail("episode native worker evidence shape changed")
            task = evidence["task"]
            reply = evidence["worker_reply"]
            if type(task) is not dict or type(reply) is not dict:
                _fail("episode task or worker reply changed")
            task_id = _document_id(
                task,
                id_key="expression_full_accounting_measurement_id",
                domain=pre.FUTURE_DOMAINS["measurement"],
                label="segment worker task",
            )
            reply_id = _document_id(
                reply,
                id_key="expression_full_accounting_segment_id",
                domain=pre.FUTURE_DOMAINS["segment"],
                label="segment worker reply",
            )
            task_raw = canonical_json_bytes(task)
            reply_raw = canonical_json_bytes(reply)
            if (
                task.get("schema")
                != "acfqp.standard_2048_expression_full_accounting_task.v34"
                or task.get("schema_version") != SCHEMA_VERSION
                or task.get("expression_full_accounting_preregistration_id")
                != pre.PREREGISTRATION_ID
                or task.get("native_counter_window") is not True
                or task.get("profile") != segment["profile"]
                or task.get("episode_index") != episode["episode_index"]
                or task.get("source_episode_id")
                != _SOURCE_EPISODE_IDS[segment["segment_ordinal"]][
                    episode["episode_index"]
                ]
                or reply.get("schema")
                != "acfqp.standard_2048_expression_full_accounting_worker_reply.v34"
                or reply.get("schema_version") != SCHEMA_VERSION
                or reply.get("expression_full_accounting_preregistration_id")
                != pre.PREREGISTRATION_ID
                or reply.get("task_id") != task_id
                or reply.get("profile") != segment["profile"]
                or reply.get("episode_index") != episode["episode_index"]
                or type(reply.get("episode")) is not dict
                or reply["episode"].get("expression_accounted_episode_id")
                not in {None, episode["episode_id"]}
                or reply["episode"].get("expression_checkpoint_episode_id")
                not in {None, episode["episode_id"]}
                or reply.get("summary_to_counter_translation_used") is not False
                or evidence["worker_reply_byte_count"] != len(reply_raw)
                or evidence["worker_reply_sha256"]
                != hashlib.sha256(reply_raw).hexdigest()
                or evidence["observed_worker_ru_maxrss_within_preregistered_cap"]
                is not True
            ):
                _fail("episode worker evidence identity or semantics changed")
            reply_episode_id = reply["episode"].get(
                "expression_accounted_episode_id"
            ) or reply["episode"].get("expression_checkpoint_episode_id")
            if (
                reply_id != content_id(
                    pre.FUTURE_DOMAINS["segment"],
                    {
                        key: value
                        for key, value in reply.items()
                        if key != "expression_full_accounting_segment_id"
                    },
                )
                or reply_episode_id != episode["episode_id"]
                or reply["episode"].get("closure_reason")
                != episode["closure_reason"]
                or reply["episode"].get("final_state") != episode["final_state"]
                or reply["episode"].get("tile_2048_reached")
                != episode["tile_2048_reached"]
                or len(reply["episode"].get("decisions", ()))
                != episode["decision_count"]
            ):
                _fail("episode worker reply differs from campaign summary")
            values = reply.get("operational_counter_values")
            if type(values) is not dict or set(values) != set(registry.by_path):
                _fail("worker operational native counter inventory changed")
            expected = dict(values)
            expected["common.hash_invocations"] += 2
            expected["common.integrity_checks"] += 2
            expected["common.protocol_checks"] += 2
            expected["io.staged_bytes"] += len(task_raw)
            expected["io.read_bytes"] += len(task_raw) + len(reply_raw)
            expected["io.output_bytes"] = operational.document[
                "output_bytes_fixed_point"
            ]
            expected["memory.working_bytes_peak"] = max(
                expected["memory.working_bytes_peak"],
                pre.WORKER_WORKING_BYTES_PEAK_UPPER,
            )
            if any(
                operational.vector.value(path) != value
                for path, value in expected.items()
            ):
                _fail("episode WorkVector differs from native worker counters")
            cold = reply.get("cold_evaluation_checkpoint_count")
            if type(cold) is not int or cold < 0:
                _fail("worker cold-checkpoint count changed")
            segment_cold += cold
            evaluation_summary = episode["evaluation_bundle"]
            if (evaluation_summary is None) != (cold == 0):
                _fail("cold evaluation bundle presence changed")
            if evaluation_summary is not None:
                evaluation = bundles[evaluation_summary["counter_bundle_id"]]
                eval_values = reply.get("evaluation_counter_values")
                if type(eval_values) is not dict or set(eval_values) != set(
                    registry.by_path
                ):
                    _fail("worker evaluation native counter inventory changed")
                expected_eval = dict(eval_values)
                expected_eval["evaluation.io_output_bytes"] = evaluation.document[
                    "output_bytes_fixed_point"
                ]
                if (
                    evaluation.vector.subject_id != episode["episode_id"]
                    or any(
                        evaluation.vector.value(path) != value
                        for path, value in expected_eval.items()
                    )
                ):
                    _fail("evaluation WorkVector differs from native worker counters")
        if segment_cold != segment["cold_evaluation_checkpoint_count"]:
            _fail("segment cold-checkpoint total differs from worker evidence")
        total_cold += segment_cold
        process = bundles[segment["process_bundle"]["counter_bundle_id"]]
        process_evidence = process.document.get("evidence")
        expected_processes = segment["active_worker_count"]
        maximum_concurrent_processes = min(
            pre.MAXIMUM_WORKER_PROCESSES, expected_processes
        )
        if (
            process_evidence
            != {
                "profile": segment["profile"],
                "task_count": segment["active_worker_count"],
                "worker_process_count": expected_processes,
                "maximum_concurrent_worker_process_count": (
                    maximum_concurrent_processes
                ),
                "maximum_tasks_per_worker_process": (
                    pre.MAXIMUM_TASKS_PER_WORKER_PROCESS
                ),
                "all_worker_replies_received": True,
            }
            or process.vector.subject_id
            != _subject_id("SEGMENT_PROCESS_SUPERVISION", process_evidence)
            or process.vector.value("process.launches") != expected_processes
            or process.vector.value("process.exit_successes") != expected_processes
            or process.vector.value("process.exit_failures") != 0
        ):
            _fail("process supervision evidence differs from native counters")
    return total_cold


def _verify_campaign_level_bundles(
    campaign: Mapping[str, Any],
    bundles: Mapping[str, _VerifiedBundleV34],
) -> None:
    model_roles = (
        "MODEL_ACQUISITION_AND_SELECTION",
        "MODEL_PROOF_AND_FREEZE",
    )
    if [row.get("window_role") for row in campaign["model_operational_bundles"]] != list(
        model_roles
    ):
        _fail("model operational bundle roles changed")
    for summary, role in zip(
        campaign["model_operational_bundles"], model_roles, strict=True
    ):
        bundle = bundles[summary["counter_bundle_id"]]
        evidence = bundle.document.get("evidence")
        if type(evidence) is not dict or bundle.vector.subject_id != _subject_id(
            role, evidence
        ):
            _fail("model accounting subject binding changed")
    model_eval = bundles[campaign["model_evaluation_bundle"]["counter_bundle_id"]]
    if (
        campaign["model_evaluation_bundle"].get("window_role")
        != "MODEL_SYNTHESIS_STANDALONE_REPLAY"
        or model_eval.document.get("measurement", {}).get("lane") != "EVALUATION"
    ):
        _fail("model evaluation bundle role changed")
    campaign_bundle = bundles[campaign["campaign_bundle"]["counter_bundle_id"]]
    campaign_evidence = campaign_bundle.document.get("evidence")
    terminal_carries = sum(
        segment["terminal_carry_forward_count"] for segment in campaign["segments"]
    )
    expected_evidence = {
        "segment_profiles": [row["profile"] for row in campaign["segments"]],
        "segment_decision_counts": [
            row["decision_count"] for row in campaign["segments"]
        ],
        "complete_decision_count": campaign["complete_decision_count"],
        "final_episode_ids": list(_FINAL_EPISODE_IDS),
        "won_occurrence_count": campaign["won_occurrence_count"],
        "lost_occurrence_count": campaign["lost_occurrence_count"],
    }
    mounted_before_campaign = sum(
        len(bundle.raw)
        for bundle in bundles.values()
        if bundle is not campaign_bundle
    )
    if (
        campaign_evidence != expected_evidence
        or campaign_bundle.vector.subject_id
        != _subject_id(
            "CAMPAIGN_AGGREGATION_AND_TERMINALIZATION", campaign_evidence
        )
        or campaign_bundle.vector.value("common.hash_invocations")
        != 3 + terminal_carries
        or campaign_bundle.vector.value("common.integrity_checks")
        != 4 + terminal_carries
        or campaign_bundle.vector.value("common.protocol_checks")
        != 4 + terminal_carries
        or campaign_bundle.vector.value("io.mounted_bytes_peak")
        != mounted_before_campaign
        or campaign_bundle.vector.value("memory.working_bytes_peak")
        != pre.PARENT_WORKING_BYTES_PEAK_UPPER
    ):
        _fail("campaign aggregation bundle differs from retained file tree")


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionFullAccountedIndependentVerificationV34:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent verification is not issuer-created")
        document = _object(self.canonical_bytes, "independent verification")
        if (
            document.get("expression_full_accounted_campaign_id")
            != self.campaign_id
            or document.get("expression_full_accounting_verification_id")
            != self.verification_id
        ):
            _fail("independent verification identity changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_full_accounting_verification_id"
        }
        if content_id(pre.FUTURE_DOMAINS["verification"], payload) != self.verification_id:
            _fail("independent verification content identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounting verification is not an object")
        return document


_ISSUER = object()


def verify_standard_2048_expression_full_accounting_bytes_independently_v34(
    campaign_bytes: bytes,
    output_root: Path,
) -> Standard2048ExpressionFullAccountedIndependentVerificationV34:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("accounting output root is absent")
    campaign = _object(campaign_bytes, "accounted campaign")
    campaign_id = _document_id(
        campaign,
        id_key="expression_full_accounted_campaign_id",
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
        or campaign.get("expression_full_accounting_preregistration")
        != pre.freeze_standard_2048_expression_full_accounting_preregistration_v34().to_document()
    ):
        _fail("frozen full accounted campaign bytes changed")
    decision_count, cold_count, won_count, lost_count = _verify_campaign_structure(
        campaign
    )
    operational_summaries, evaluation_summaries = _campaign_summaries(campaign)
    if (
        len(operational_summaries) != 45
        or len(evaluation_summaries) != 34
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
    verified_bundles = {
        bundle.summary["counter_bundle_id"]: bundle
        for bundle in (*operational, *evaluation)
    }
    if len(verified_bundles) != len(operational) + len(evaluation):
        _fail("counter bundle identity was reused")
    if _verify_native_segment_evidence(campaign, verified_bundles) != cold_count:
        _fail("cold evaluation total changed")
    _verify_campaign_level_bundles(campaign, verified_bundles)
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
    label_queries = sum(
        bundle.vector.value("model.target_probability_labels_acquired")
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
        or campaign.get("operational_target_probability_label_query_count")
        != label_queries
        or campaign.get("unique_operational_target_probability_label_count")
        != 4
        or campaign.get("additional_operational_target_probability_label_count")
        != 0
        or campaign.get("strict_no_prior_target_probability_label_count") != 8
        or campaign.get("target_probability_label_fraction_of_no_prior")
        != Fraction(1, 2)
        or campaign.get("certified_decisions_per_acquired_target_label")
        != Fraction(3187, 4)
        or campaign.get("logical_occurrence_count") != 4
        or campaign.get("complete_decision_count") != decision_count
        or campaign.get("model_certificate_count") != decision_count
        or campaign.get("won_occurrence_count") != won_count
        or campaign.get("lost_occurrence_count") != lost_count
        or campaign.get("terminal_occurrence_count") != won_count + lost_count
        or decision_count != 3187
        or won_count != 2
        or lost_count != 2
        or label_queries != 4
        or target_steps != 3187
    ):
        _fail("campaign aggregate differs from independently replayed vectors")
    if any(
        campaign.get(key) is not expected
        for key, expected in {
            "all_3187_decisions_rerun_under_native_counter_windows": True,
            "all_required_counter_leaves_have_explicit_native_records": True,
            "all_nine_shared_resource_paths_have_measurement_receipts": True,
            "evaluation_replay_excluded_from_operational_comparison": True,
            "terminal_occurrences_retained_in_denominator": True,
            "summary_to_counter_translation_used": False,
            "registered_profile_counter_completeness_candidate": True,
            "full_standard_2048_campaign_terminalized": True,
            "tile_2048_reached": True,
            "sample_tax_reduced_on_registered_label_axis": True,
            "broad_iid_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
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
        "schema": "acfqp.standard_2048_expression_full_accounted_independent_verification.v34",
        "schema_version": SCHEMA_VERSION,
        "expression_full_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_full_accounted_campaign_id": campaign_id,
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
        "complete_decision_count": decision_count,
        "cold_evaluation_checkpoint_count": cold_count,
        "won_occurrence_count": won_count,
        "lost_occurrence_count": lost_count,
        "four_actual_probability_queries_replayed": label_queries == 4,
        "three_thousand_one_hundred_eighty_seven_target_execution_steps_replayed": target_steps == 3187,
        "registered_label_axis_sample_tax_reduction_replayed": True,
        "broad_iid_sample_efficiency_claimed": False,
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
            "expression_full_accounting_verification_id": verification_id,
        }
    )
    if (
        EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT
        and (
            len(raw) != EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest()
            != EXPECTED_VERIFICATION_CANONICAL_SHA256
        )
    ):
        _fail("frozen accounting verification bytes changed")
    return Standard2048ExpressionFullAccountedIndependentVerificationV34(
        _ISSUER, raw, campaign_id, verification_id
    )


__all__ = (
    "EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_VERIFICATION_CANONICAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExpressionFullAccountedIndependentVerificationV34",
    "verify_standard_2048_expression_full_accounting_bytes_independently_v34",
)
