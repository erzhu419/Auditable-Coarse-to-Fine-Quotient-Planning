"""Producer-free replay of V36 native vectors, receipts, and V35 semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as pre
from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as semantic_v35
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35_pre
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    LaneEnum,
    NativeZeroAttestationV1,
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
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
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
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64
V35_CAMPAIGN_ID = "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
V35_VERIFICATION_ID = "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"


class ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
    RuntimeError
):
    """The V35 replay, bundle DAG, native records, or projection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _document_id(
    document: Mapping[str, Any], *, id_key: str, domain: str, label: str
) -> str:
    if type(document) is not dict or id_key not in document:
        _fail(f"{label} shape changed")
    try:
        identity = parse_content_id(document[id_key])
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
            f"{label} identity changed"
        ) from error
    payload = {key: value for key, value in document.items() if key != id_key}
    if content_id(domain, payload) != identity:
        _fail(f"{label} content identity changed")
    return identity


_OPERATIONAL_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "adaptive_accounting_preregistration_id",
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
    "adaptive_accounting_counter_bundle_id",
}
_EVALUATION_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "adaptive_accounting_preregistration_id",
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
    "adaptive_accounting_counter_bundle_id",
}
_MEASUREMENT_FIELDS = {
    "schema",
    "schema_version",
    "adaptive_accounting_preregistration_id",
    "subject_id",
    "window_role",
    "lane",
    "measured_values",
    "native_measurement_not_legacy_summary_translation",
    "adaptive_accounting_measurement_id",
}
_SUMMARY_FIELDS = {
    "counter_bundle_id",
    "output_key",
    "canonical_byte_count",
    "canonical_sha256",
    "subject_id",
    "work_vector_id",
    "comparison_vector_id",
    "lane",
}
_EPISODE_ROW_FIELDS = {
    "episode_index",
    "v35_episode_id",
    "decision_count",
    "closure_reason",
    "final_state",
    "planning_operational_bundle",
    "execution_operational_bundle",
    "evaluation_bundle",
}
_CAMPAIGN_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "adaptive_accounting_preregistration",
    "v35_adaptive_expression_campaign_id",
    "v35_adaptive_expression_verification_id",
    "v35_native_replay_campaign_id",
    "counter_registry_id",
    "stage_profile_id",
    "comparison_profile_id",
    "actual_projection_profile_id",
    "model_stage_bundles",
    "matched_no_prior_control_bundle",
    "episode_rows",
    "process_supervision_bundle",
    "campaign_aggregation_bundle",
    "operational_work_vector_count",
    "evaluation_work_vector_count",
    "vector_prefix_totals",
    "final_operational_comparison_totals",
    "logical_occurrence_count",
    "complete_decision_count",
    "model_certificate_count",
    "certificate_failure_count",
    "operational_target_probability_label_query_count",
    "evaluation_no_prior_probability_label_count",
    "adaptive_label_fraction_of_no_prior",
    "cold_evaluation_checkpoint_count",
    "all_checkpoint_root_values_and_actions_exactly_equal",
    "all_required_counter_leaves_have_explicit_native_records",
    "all_nine_shared_resource_paths_have_measurement_receipts",
    "evaluation_replay_excluded_from_operational_comparison",
    "summary_to_counter_translation_used",
    "every_worker_process_executes_exactly_one_occurrence",
    "sample_tax_reduced_on_registered_first_failure_label_axis",
    "formal_counter_completeness_candidate",
    "automatic_reusable_world_model_goal_completed",
    "broad_iid_or_cross_domain_sample_efficiency_claimed",
    "total_operational_work_saving_claimed",
    "official_execution_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "adaptive_accounted_campaign_id",
}
_EVALUATION_SHARED_PATHS = (
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


@dataclass(frozen=True, slots=True)
class _VerifiedBundleV36:
    summary: Mapping[str, Any]
    document: Mapping[str, Any]
    vector: WorkVectorV1
    comparison: ComparisonVectorV1 | None
    raw: bytes


def _measurement(
    document: Mapping[str, Any],
    *,
    subject_id: str,
    window_role: str,
    lane: str,
    vector: WorkVectorV1,
) -> None:
    if type(document) is not dict or set(document) != _MEASUREMENT_FIELDS:
        _fail("measurement exact field set changed")
    identity = _document_id(
        document,
        id_key="adaptive_accounting_measurement_id",
        domain=pre.FUTURE_DOMAINS["measurement"],
        label="V36 measurement",
    )
    if (
        document["schema"]
        != "acfqp.standard_2048_adaptive_accounting_measurement.v36"
        or document["schema_version"] != SCHEMA_VERSION
        or document["adaptive_accounting_preregistration_id"]
        != pre.PREREGISTRATION_ID
        or document["subject_id"] != subject_id
        or document["window_role"] != window_role
        or document["lane"] != lane
        or document["native_measurement_not_legacy_summary_translation"]
        is not True
    ):
        _fail("measurement semantic binding changed")
    paths = pre.SHARED_RESOURCE_PATHS if lane == "OPERATIONAL" else _EVALUATION_SHARED_PATHS
    if document["measured_values"] != [
        {"path": path, "value": vector.value(path)} for path in paths
    ]:
        _fail("measurement values differ from CounterRecords")
    if any(record.recorder_id != identity for record in vector.records):
        _fail("CounterRecord recorder differs from measurement")


def _expected_route_binding(
    role: str,
) -> tuple[RouteKindEnum, ActualWorkScope]:
    if role in {
        "EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION",
        "EPISODE_SELECTED_TARGET_EXECUTION",
    }:
        return (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            ActualWorkScope.ABSTRACT_SELECTED_ROUTE_EXECUTION,
        )
    if role in {
        "CERTIFICATE_FAILURE_FRONTIER_FREEZE",
        "ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
        "EXPRESSION_PROPOSAL_FREEZE",
        "EXACT_PROGRAM_PROOF",
        "PROVED_OVERLAY_FREEZE",
        "PROCESS_AND_IO_SUPERVISION",
        "CAMPAIGN_AGGREGATION_AND_TERMINALIZATION",
    }:
        return RouteKindEnum.ABSTRACT_FAILED_PREFIX, ActualWorkScope.COMMON_PREFIX
    _fail("unknown V36 operational window role")


def _verify_summary(
    summary: Mapping[str, Any], *, root: Path
) -> _VerifiedBundleV36:
    if type(summary) is not dict or set(summary) != _SUMMARY_FIELDS:
        _fail("bundle summary exact field set changed")
    key = summary["output_key"]
    if (
        type(key) is not str
        or not key
        or Path(key).is_absolute()
        or ".." in Path(key).parts
    ):
        _fail("bundle output key changed")
    path = root / key
    if not path.is_file() or path.is_symlink():
        _fail("bundle output file is absent or indirect")
    raw = path.read_bytes()
    document = _object(raw, key)
    identity = _document_id(
        document,
        id_key="adaptive_accounting_counter_bundle_id",
        domain=pre.FUTURE_DOMAINS["counter_bundle"],
        label="V36 counter bundle",
    )
    if (
        summary["counter_bundle_id"] != identity
        or summary["canonical_byte_count"] != len(raw)
        or summary["canonical_sha256"] != hashlib.sha256(raw).hexdigest()
        or summary["subject_id"] != document.get("subject_id")
        or summary["lane"] != document.get("measurement", {}).get("lane")
    ):
        _fail("bundle summary differs from retained bytes")
    registry = registry_v9.official_counter_registry_v9()
    try:
        vector = WorkVectorV1.from_dict(document["work_vector"], registry)
        zero = NativeZeroAttestationV1.from_dict(
            document["native_zero_attestation"]
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
            "retained WorkVector or native-zero attestation is invalid"
        ) from error
    if (
        zero != NativeZeroAttestationV1.derive(vector, registry)
        or vector.subject_id != document.get("subject_id")
        or summary["work_vector_id"] != vector.work_vector_id
        or len(vector.records) != len(registry.leaves)
        or document.get("adaptive_accounting_preregistration_id")
        != pre.PREREGISTRATION_ID
        or document.get("official_execution_allowed") is not False
        or type(document.get("fixed_point_iteration")) is not int
        or not 0 <= document["fixed_point_iteration"] < 16
    ):
        _fail("bundle native completeness or identity changed")
    role = document["window_role"]
    charged = document["output_bytes_fixed_point"]
    external = 0
    if role == "EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION":
        evidence = document.get("evidence")
        if (
            type(evidence) is not dict
            or type(evidence.get("worker_reply_byte_count")) is not int
            or evidence["worker_reply_byte_count"] <= 0
        ):
            _fail("worker transport byte evidence changed")
        worker_raw = canonical_json_bytes(evidence.get("worker_reply"))
        if (
            len(worker_raw) != evidence["worker_reply_byte_count"]
            or hashlib.sha256(worker_raw).hexdigest()
            != evidence.get("worker_reply_sha256")
        ):
            _fail("embedded worker reply bytes changed")
        external = len(worker_raw)
    if charged != len(raw) + external:
        _fail("bundle output-byte fixed point changed")
    lane = document["measurement"]["lane"]
    _measurement(
        document["measurement"],
        subject_id=vector.subject_id,
        window_role=role,
        lane=lane,
        vector=vector,
    )
    if lane == "OPERATIONAL":
        if set(document) != _OPERATIONAL_BUNDLE_FIELDS:
            _fail("operational bundle exact field set changed")
        if (
            document["schema"]
            != "acfqp.standard_2048_adaptive_operational_counter_bundle.v36"
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
            raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
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
            raise ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error(
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
        ):
            _fail("operational route, scope, or projection changed")
        return _VerifiedBundleV36(summary, document, vector, comparison, raw)
    if lane == "EVALUATION":
        if set(document) != _EVALUATION_BUNDLE_FIELDS:
            _fail("evaluation bundle exact field set changed")
        if (
            document["schema"]
            != "acfqp.standard_2048_adaptive_evaluation_counter_bundle.v36"
            or document["comparison_vector"] is not None
            or document["actual_projection_proof"] is not None
            or document[
                "evaluation_lane_excluded_from_operational_comparison"
            ]
            is not True
            or summary["comparison_vector_id"] is not None
            or any(vector.value(leaf.path) for leaf in registry.operational_leaves)
        ):
            _fail("evaluation work entered operational comparison")
        return _VerifiedBundleV36(summary, document, vector, None, raw)
    _fail("bundle lane changed")


def _campaign_summaries(
    campaign: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]]:
    model = campaign.get("model_stage_bundles")
    episodes = campaign.get("episode_rows")
    if (
        type(model) is not list
        or len(model) != 5
        or type(episodes) is not list
        or len(episodes) != 4
        or any(type(row) is not dict or set(row) != _EPISODE_ROW_FIELDS for row in episodes)
    ):
        _fail("campaign bundle inventory changed")
    operational = list(model)
    evaluation = [campaign.get("matched_no_prior_control_bundle")]
    for index, row in enumerate(episodes):
        if row["episode_index"] != index:
            _fail("episode row order changed")
        operational.extend(
            (
                row["planning_operational_bundle"],
                row["execution_operational_bundle"],
            )
        )
        if row["evaluation_bundle"] is not None:
            evaluation.append(row["evaluation_bundle"])
    operational.extend(
        (
            campaign.get("process_supervision_bundle"),
            campaign.get("campaign_aggregation_bundle"),
        )
    )
    return tuple(operational), tuple(evaluation)


def _zero_values() -> dict[str, int]:
    return {
        path: 0 for path in registry_v9.official_counter_registry_v9().by_path
    }


def _expect_vector(
    bundle: _VerifiedBundleV36,
    expected: Mapping[str, int],
    *,
    label: str,
) -> None:
    if bundle.vector.values != dict(expected):
        changed = sorted(
            path
            for path, value in bundle.vector.values.items()
            if value != expected.get(path)
        )
        _fail(f"{label} CounterRecords changed: {changed!r}")


def _base_bundle_values(bundle: _VerifiedBundleV36) -> dict[str, int]:
    values = _zero_values()
    if bundle.document["measurement"]["lane"] == "OPERATIONAL":
        values["io.output_bytes"] = bundle.document["output_bytes_fixed_point"]
    else:
        values["evaluation.io_output_bytes"] = bundle.document[
            "output_bytes_fixed_point"
        ]
    return values


def _verify_model_bundles(
    bundles: tuple[_VerifiedBundleV36, ...], v35_campaign: Mapping[str, Any]
) -> None:
    if len(bundles) != 5:
        _fail("model-stage bundle count changed")
    roles = (
        "CERTIFICATE_FAILURE_FRONTIER_FREEZE",
        "ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
        "EXPRESSION_PROPOSAL_FREEZE",
        "EXACT_PROGRAM_PROOF",
        "PROVED_OVERLAY_FREEZE",
    )
    if tuple(row.document["window_role"] for row in bundles) != roles:
        _fail("model-stage bundle order changed")
    counts = v35_campaign.get("model_operational_counter_values")
    if type(counts) is not dict or set(counts) != {
        "model.structural_context_rows_frozen",
        "model.structural_expression_value_evaluations",
        "model.expression_candidates_materialized",
        "model.candidate_label_consistency_checks",
        "model.active_query_partition_evaluations",
        "model.target_probability_labels_acquired",
        "model.exact_program_proof_rows_evaluated",
        "model.world_model_freezes",
    }:
        _fail("V35 model counter inventory changed")
    stage_paths = (
        {"model.structural_context_rows_frozen"},
        set(counts)
        - {
            "model.structural_context_rows_frozen",
            "model.exact_program_proof_rows_evaluated",
            "model.world_model_freezes",
        },
        set(),
        {"model.exact_program_proof_rows_evaluated"},
        {"model.world_model_freezes"},
    )
    evidence_ids = (
        v35_campaign["certificate_failure"]["adaptive_expression_failure_id"],
        tuple(
            row["adaptive_expression_acquisition_id"]
            for row in v35_campaign["expression_acquisitions"]
        ),
        v35_campaign["expression_proposal"]["adaptive_expression_proposal_id"],
        v35_campaign["expression_proof"]["adaptive_expression_proof_id"],
        v35_campaign["expression_overlay"]["adaptive_expression_overlay_id"],
    )
    for index, (bundle, paths) in enumerate(zip(bundles, stage_paths, strict=True)):
        expected = _base_bundle_values(bundle)
        for path in paths:
            expected[path] = counts[path]
        expected["common.protocol_checks"] = 2
        expected["common.integrity_checks"] = 2
        expected["common.hash_invocations"] = 2
        expected["route.attempts"] = 1
        expected["route.successes"] = 1
        expected["memory.working_bytes_peak"] = pre.PARENT_WORKING_BYTES_PEAK_UPPER
        _expect_vector(bundle, expected, label=roles[index])
        evidence = bundle.document["evidence"]
        if index == 0 and evidence.get("adaptive_expression_failure_id") != evidence_ids[0]:
            _fail("failure-frontier evidence changed")
        if index == 1 and tuple(
            row.get("adaptive_expression_acquisition_id")
            for row in evidence.get("expression_acquisitions", ())
        ) != evidence_ids[1]:
            _fail("acquisition evidence changed")
        if index >= 2:
            id_key = (
                "adaptive_expression_proposal_id",
                "adaptive_expression_proof_id",
                "adaptive_expression_overlay_id",
            )[index - 2]
            if evidence.get(id_key) != evidence_ids[index]:
                _fail("proposal/proof/overlay evidence changed")


def _planning_expected(
    bundle: _VerifiedBundleV36,
    episode: Mapping[str, Any],
    *,
    overlay: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, Any]]:
    decisions = episode["decisions"]
    expected = _base_bundle_values(bundle)
    expected["common.abstract_bellman_backups"] = sum(
        row["certificate"]["factored_action_row_evaluation_count"]
        for row in decisions
    )
    expected["common.abstract_support_outcome_evaluations"] = sum(
        row["certificate"]["factored_support_outcome_evaluation_count"]
        for row in decisions
    )
    hits = sum(
        row["certificate"]["subproof_cache_hit_count"] for row in decisions
    )
    misses = sum(
        row["certificate"]["subproof_cache_miss_count"] for row in decisions
    )
    expected["common.abstract_subproof_cache_hits"] = hits
    expected["common.abstract_subproof_cache_misses"] = misses
    expected["common.abstract_subproof_cache_lookups"] = hits + misses
    expected["common.protocol_checks"] = 2 * len(decisions) + 2
    expected["common.integrity_checks"] = 2 * len(decisions) + 2
    expected["common.hash_invocations"] = 2 * len(decisions) + 2
    expected["route.attempts"] = len(decisions)
    expected["route.successes"] = len(decisions)
    evidence = bundle.document["evidence"]
    worker_reply = evidence["worker_reply"]
    candidate = overlay["selected_candidate"]
    task = {
        "schema": "acfqp.standard_2048_adaptive_accounting_worker_task.v36",
        "schema_version": SCHEMA_VERSION,
        "adaptive_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode["episode_index"],
        "initial_board_ranks": list(episode["initial_state"]["board_ranks"]),
        "execution_seed": episode["execution_seed"],
        "overlay": overlay,
        "candidate": candidate,
    }
    task_bytes = canonical_json_bytes(task)
    if (
        len(task_bytes) != evidence.get("task_byte_count")
        or hashlib.sha256(task_bytes).hexdigest() != evidence.get("task_sha256")
    ):
        _fail("worker task bytes changed")
    expected["io.staged_bytes"] = len(task_bytes)
    expected["io.read_bytes"] = len(task_bytes) + evidence["worker_reply_byte_count"]
    expected["memory.working_bytes_peak"] = pre.WORKER_WORKING_BYTES_PEAK_UPPER
    raw_counter_values = dict(expected)
    raw_counter_values["common.protocol_checks"] -= 2
    raw_counter_values["common.integrity_checks"] -= 2
    raw_counter_values["common.hash_invocations"] -= 2
    raw_counter_values["io.staged_bytes"] = 0
    raw_counter_values["io.read_bytes"] = 0
    raw_counter_values["memory.working_bytes_peak"] = 0
    raw_counter_values["io.output_bytes"] = 0
    if worker_reply.get("planning_operational_counter_values") != raw_counter_values:
        _fail("worker planning counters differ from V35 certificates")
    return expected, worker_reply


def _execution_expected(
    bundle: _VerifiedBundleV36,
    episode: Mapping[str, Any],
    worker_reply: Mapping[str, Any],
) -> dict[str, int]:
    decisions = episode["decisions"]
    outcome_count = 0
    for decision in decisions:
        board = tuple(decision["predecision_state"]["board_ranks"])
        post, _ = semantic_v35._swipe(board, decision["executed_action"])  # noqa: SLF001
        outcome_count += 2 * post.count(0)
    expected = _base_bundle_values(bundle)
    expected["common.protocol_checks"] = len(decisions)
    expected["common.integrity_checks"] = len(decisions)
    expected["common.hash_invocations"] = len(decisions)
    expected["target.execution_ground_steps"] = len(decisions)
    expected["target.execution_outcome_rows"] = outcome_count
    expected["target.transition_observations"] = len(decisions)
    expected["memory.working_bytes_peak"] = pre.WORKER_WORKING_BYTES_PEAK_UPPER
    raw_counter_values = dict(expected)
    raw_counter_values["memory.working_bytes_peak"] = 0
    raw_counter_values["io.output_bytes"] = 0
    if worker_reply.get("execution_operational_counter_values") != raw_counter_values:
        _fail("worker execution counters differ from target transitions")
    return expected


def _cold_evaluation_expected(
    bundle: _VerifiedBundleV36,
    episode: Mapping[str, Any],
) -> dict[str, int]:
    expected = _base_bundle_values(bundle)
    checkpoints = [
        row for row in episode["decisions"] if row["cold_target_checkpoint"] is not None
    ]
    states = actions = outcomes = hits = misses = 0
    for decision in checkpoints:
        planner = semantic_v35._GroundPlanner()  # noqa: SLF001
        state = semantic_v35._state(decision["predecision_state"])  # noqa: SLF001
        replay = planner.root(state)
        if replay != decision["cold_target_checkpoint"]:
            _fail("cold checkpoint differs from producer-free exact replay")
        actions += planner.rows
        outcomes += planner.outcomes
        hits += planner.hits
        misses += planner.misses
        states += 1 + sum(
            1
            for _, status, remaining in planner.cache
            if status == "ACTIVE" and remaining > 0
        )
    expected["evaluation.exact_states_expanded"] = states
    expected["evaluation.exact_actions_evaluated"] = actions
    expected["evaluation.exact_ground_steps"] = actions
    expected["evaluation.exact_outcome_rows"] = outcomes
    expected["evaluation.exact_bellman_backups"] = actions
    expected["evaluation.exact_subproof_cache_lookups"] = hits + misses
    expected["evaluation.exact_subproof_cache_hits"] = hits
    expected["evaluation.exact_subproof_cache_misses"] = misses
    expected["evaluation.semantic_integrity_checks"] = len(checkpoints)
    expected["evaluation.semantic_protocol_checks"] = len(checkpoints)
    return expected


def _verify_episode_bundles(
    campaign: Mapping[str, Any],
    v35_campaign: Mapping[str, Any],
    by_id: Mapping[str, _VerifiedBundleV36],
) -> tuple[int, int]:
    rows = campaign["episode_rows"]
    v35_episodes = v35_campaign["episodes"]
    total_decisions = total_cold = 0
    overlay = v35_campaign["expression_overlay"]
    for index, (row, episode) in enumerate(zip(rows, v35_episodes, strict=True)):
        if (
            row["episode_index"] != index
            or episode["episode_index"] != index
            or row["v35_episode_id"] != episode["adaptive_expression_episode_id"]
            or row["decision_count"] != episode["decision_count"]
            or row["closure_reason"] != episode["closure_reason"]
            or row["final_state"] != episode["final_state"]
        ):
            _fail("V36 episode summary differs from V35 semantics")
        planning = by_id[row["planning_operational_bundle"]["counter_bundle_id"]]
        execution = by_id[row["execution_operational_bundle"]["counter_bundle_id"]]
        expected_planning, worker_reply = _planning_expected(
            planning, episode, overlay=overlay
        )
        _expect_vector(planning, expected_planning, label="episode planning")
        _expect_vector(
            execution,
            _execution_expected(execution, episode, worker_reply),
            label="episode target execution",
        )
        if worker_reply.get("episode") != episode:
            _fail("worker reply episode differs from V35 campaign")
        evaluation_summary = row["evaluation_bundle"]
        checkpoints = episode["cold_evaluation_checkpoint_count"]
        if checkpoints:
            if evaluation_summary is None:
                _fail("cold checkpoint lost evaluation bundle")
            evaluation = by_id[evaluation_summary["counter_bundle_id"]]
            _expect_vector(
                evaluation,
                _cold_evaluation_expected(evaluation, episode),
                label="cold evaluation",
            )
        elif evaluation_summary is not None:
            _fail("zero-checkpoint episode gained evaluation bundle")
        total_decisions += episode["decision_count"]
        total_cold += checkpoints
    return total_decisions, total_cold


def _verify_control_bundle(
    bundle: _VerifiedBundleV36, v35_campaign: Mapping[str, Any]
) -> int:
    control = v35_campaign["matched_no_prior_first_frontier_control"]
    count = control["distinct_context_probability_label_count"]
    if bundle.document["evidence"] != control:
        _fail("matched no-prior control evidence changed")
    expected = _base_bundle_values(bundle)
    expected["evaluation.target_probability_labels_acquired"] = count
    expected["evaluation.semantic_protocol_checks"] = 2
    expected["evaluation.semantic_integrity_checks"] = 2
    expected["evaluation.hash_invocations"] = 2
    _expect_vector(bundle, expected, label="matched no-prior control")
    return count


def _verify_process_bundle(
    bundle: _VerifiedBundleV36, occurrence_count: int
) -> None:
    evidence = bundle.document["evidence"]
    if evidence != {
        "worker_process_count": occurrence_count,
        "maximum_concurrent_worker_process_count": min(
            pre.MAXIMUM_WORKER_PROCESSES, occurrence_count
        ),
        "maximum_tasks_per_worker_process": pre.MAXIMUM_TASKS_PER_WORKER_PROCESS,
        "all_worker_pids_distinct": True,
    }:
        _fail("process supervision evidence changed")
    expected = _base_bundle_values(bundle)
    expected["process.launches"] = occurrence_count
    expected["process.exit_successes"] = occurrence_count
    expected["common.protocol_checks"] = occurrence_count
    expected["common.integrity_checks"] = occurrence_count
    expected["common.hash_invocations"] = 1
    _expect_vector(bundle, expected, label="process supervision")


def _verify_campaign_bundle(
    bundle: _VerifiedBundleV36,
    *,
    root: Path,
    campaign: Mapping[str, Any],
    v35_campaign: Mapping[str, Any],
) -> None:
    evidence = bundle.document["evidence"]
    if evidence != {
        "v35_campaign_id": V35_CAMPAIGN_ID,
        "v35_verification_id": V35_VERIFICATION_ID,
        "v35_episode_ids": [
            row["adaptive_expression_episode_id"]
            for row in v35_campaign["episodes"]
        ],
        "decision_count": v35_campaign["decision_count"],
        "ground_distinction_query_count": v35_campaign[
            "ground_distinction_query_count"
        ],
    }:
        _fail("campaign aggregation evidence changed")
    expected = _base_bundle_values(bundle)
    expected["common.hash_invocations"] = 3
    expected["common.integrity_checks"] = 4
    expected["common.protocol_checks"] = 4
    expected["memory.working_bytes_peak"] = pre.PARENT_WORKING_BYTES_PEAK_UPPER
    expected["io.mounted_bytes_peak"] = sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and path != root / bundle.summary["output_key"]
    )
    _expect_vector(bundle, expected, label="campaign aggregation")


def _accumulate(
    total: dict[str, int], values: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    result = dict(total)
    for axis, value in values:
        if axis in {"peak_mounted_bytes", "peak_working_bytes"}:
            result[axis] = max(result[axis], value)
        else:
            result[axis] += value
    return result


def _verify_v35_semantics(
    *,
    campaign_bytes: bytes,
    verification_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if V35_CAMPAIGN_ID == "0" * 64 or V35_VERIFICATION_ID == "0" * 64:
        _fail("V35 semantic predecessor has not been frozen")
    preregistration = (
        v35_pre.freeze_standard_2048_adaptive_expression_preregistration_v35()
    )
    replay = semantic_v35.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
        campaign_bytes, preregistration.canonical_bytes
    )
    observed_verification = _object(verification_bytes, "V35 verification")
    verification_id = _document_id(
        observed_verification,
        id_key="adaptive_expression_verification_id",
        domain=CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
        label="V35 verification",
    )
    if (
        replay.canonical_bytes != verification_bytes
        or replay.campaign_id != V35_CAMPAIGN_ID
        or replay.verification_id != V35_VERIFICATION_ID
        or verification_id != V35_VERIFICATION_ID
    ):
        _fail("V35 independent verification bytes changed")
    return _object(campaign_bytes, "V35 campaign"), observed_verification


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveAccountedIndependentVerificationV36:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V36 independent verification is not issuer-created")
        document = _object(self.canonical_bytes, "V36 independent verification")
        if (
            document.get("adaptive_accounted_campaign_id") != self.campaign_id
            or document.get("adaptive_accounting_verification_id")
            != self.verification_id
        ):
            _fail("V36 independent verification identity changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_accounting_verification_id"
        }
        if content_id(
            pre.FUTURE_DOMAINS["verification"], payload
        ) != self.verification_id:
            _fail("V36 independent verification content ID changed")

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V36 independent verification")


def verify_standard_2048_adaptive_accounting_bytes_independently_v36(
    *,
    campaign_bytes: bytes,
    output_root: Path,
    v35_campaign_bytes: bytes,
    v35_verification_bytes: bytes,
) -> Standard2048AdaptiveAccountedIndependentVerificationV36:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("V36 accounting output root is absent")
    campaign = _object(campaign_bytes, "V36 accounted campaign")
    if set(campaign) != _CAMPAIGN_FIELDS:
        _fail("V36 campaign exact field set changed")
    campaign_id = _document_id(
        campaign,
        id_key="adaptive_accounted_campaign_id",
        domain=pre.FUTURE_DOMAINS["campaign"],
        label="V36 accounted campaign",
    )
    if (
        (EXPECTED_CAMPAIGN_ID != "0" * 64 and campaign_id != EXPECTED_CAMPAIGN_ID)
        or (
            EXPECTED_CANONICAL_BYTE_COUNT
            and len(campaign_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        )
        or (
            EXPECTED_CANONICAL_SHA256 != "0" * 64
            and hashlib.sha256(campaign_bytes).hexdigest()
            != EXPECTED_CANONICAL_SHA256
        )
        or campaign["schema"]
        != "acfqp.standard_2048_adaptive_accounted_campaign.v36"
        or campaign["schema_version"] != SCHEMA_VERSION
        or campaign["proposed_contract_version"] != pre.PROPOSED_CONTRACT_VERSION
        or campaign["adaptive_accounting_preregistration"]
        != pre.freeze_standard_2048_adaptive_accounting_preregistration_v36().to_document()
    ):
        _fail("frozen V36 campaign identity or predecessor changed")
    v35_campaign, v35_verification = _verify_v35_semantics(
        campaign_bytes=v35_campaign_bytes,
        verification_bytes=v35_verification_bytes,
    )
    if (
        campaign["v35_adaptive_expression_campaign_id"] != V35_CAMPAIGN_ID
        or campaign["v35_native_replay_campaign_id"] != V35_CAMPAIGN_ID
        or campaign["v35_adaptive_expression_verification_id"]
        != V35_VERIFICATION_ID
        or v35_campaign["adaptive_expression_campaign_id"] != V35_CAMPAIGN_ID
        or v35_verification["adaptive_expression_verification_id"]
        != V35_VERIFICATION_ID
    ):
        _fail("V35 to V36 semantic binding changed")
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    if (
        campaign["counter_registry_id"]
        != profiles["counter_registry"]["counter_registry_id"]
        or campaign["stage_profile_id"]
        != profiles["stage_profile"]["stage_profile_id"]
        or campaign["comparison_profile_id"]
        != profiles["comparison_profile"]["comparison_profile_id"]
        or campaign["actual_projection_profile_id"]
        != profiles["actual_projection_profile"]["actual_projection_profile_id"]
    ):
        _fail("V36 registry profile binding changed")
    operational_summaries, evaluation_summaries = _campaign_summaries(campaign)
    if (
        len(operational_summaries) != 15
        or len(evaluation_summaries) != 5
        or campaign["operational_work_vector_count"]
        != len(operational_summaries)
        or campaign["evaluation_work_vector_count"]
        != len(evaluation_summaries)
    ):
        _fail("V36 WorkVector cardinality changed")
    all_summaries = (*operational_summaries, *evaluation_summaries)
    output_keys = [row.get("output_key") for row in all_summaries]
    retained = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
    }
    if len(set(output_keys)) != len(output_keys) or retained != set(output_keys):
        _fail("V36 retained bundle file inventory changed")
    operational = tuple(
        _verify_summary(summary, root=output_root)
        for summary in operational_summaries
    )
    evaluation = tuple(
        _verify_summary(summary, root=output_root)
        for summary in evaluation_summaries
    )
    by_id = {
        bundle.summary["counter_bundle_id"]: bundle
        for bundle in (*operational, *evaluation)
    }
    if len(by_id) != len(operational) + len(evaluation):
        _fail("V36 counter bundle identity was reused")
    _verify_model_bundles(operational[:5], v35_campaign)
    control_count = _verify_control_bundle(evaluation[0], v35_campaign)
    decision_count, cold_count = _verify_episode_bundles(
        campaign, v35_campaign, by_id
    )
    _verify_process_bundle(operational[-2], len(v35_campaign["episodes"]))
    _verify_campaign_bundle(
        operational[-1],
        root=output_root,
        campaign=campaign,
        v35_campaign=v35_campaign,
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
    label_count = sum(
        bundle.vector.value("model.target_probability_labels_acquired")
        for bundle in operational
    )
    execution_steps = sum(
        bundle.vector.value("target.execution_ground_steps")
        for bundle in operational
    )
    registry = registry_v9.official_counter_registry_v9()
    counter_record_count = sum(
        len(bundle.vector.records) for bundle in (*operational, *evaluation)
    )
    if (
        campaign["vector_prefix_totals"] != prefix
        or campaign["final_operational_comparison_totals"] != final_totals
        or campaign["logical_occurrence_count"] != 4
        or campaign["complete_decision_count"] != decision_count
        or campaign["model_certificate_count"] != decision_count
        or campaign["certificate_failure_count"] != 1
        or campaign["operational_target_probability_label_query_count"]
        != label_count
        or campaign["evaluation_no_prior_probability_label_count"]
        != control_count
        or campaign["adaptive_label_fraction_of_no_prior"]
        != Fraction(label_count, control_count)
        or campaign["cold_evaluation_checkpoint_count"] != cold_count
        or decision_count != v35_campaign["decision_count"]
        or execution_steps != decision_count
        or label_count != v35_campaign["ground_distinction_query_count"]
        or control_count != v35_campaign["first_frontier_no_prior_label_count"]
        or counter_record_count
        != (len(operational) + len(evaluation)) * len(registry.leaves)
    ):
        _fail("V36 campaign aggregate differs from exact native replay")
    if any(
        campaign[key] is not expected
        for key, expected in {
            "all_checkpoint_root_values_and_actions_exactly_equal": True,
            "all_required_counter_leaves_have_explicit_native_records": True,
            "all_nine_shared_resource_paths_have_measurement_receipts": True,
            "evaluation_replay_excluded_from_operational_comparison": True,
            "summary_to_counter_translation_used": False,
            "every_worker_process_executes_exactly_one_occurrence": True,
            "sample_tax_reduced_on_registered_first_failure_label_axis": True,
            "formal_counter_completeness_candidate": True,
            "automatic_reusable_world_model_goal_completed": False,
            "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
            "official_execution_allowed": False,
        }.items()
    ) or (
        campaign["official_scalar_cost"] is not None
        or campaign["official_N_break_even"] is not None
        or campaign["counter_completeness_gate_status"] != "NOT_RUN"
        or campaign["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("V36 claim locks changed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounted_independent_verification.v36",
        "schema_version": SCHEMA_VERSION,
        "adaptive_accounting_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_accounted_campaign_id": campaign_id,
        "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
        "counter_registry_id": campaign["counter_registry_id"],
        "stage_profile_id": campaign["stage_profile_id"],
        "comparison_profile_id": campaign["comparison_profile_id"],
        "actual_projection_profile_id": campaign["actual_projection_profile_id"],
        "operational_work_vector_count": len(operational),
        "evaluation_work_vector_count": len(evaluation),
        "counter_record_count": counter_record_count,
        "complete_decision_count": decision_count,
        "cold_evaluation_checkpoint_count": cold_count,
        "operational_target_probability_label_query_count": label_count,
        "evaluation_no_prior_probability_label_count": control_count,
        "every_counter_record_and_native_zero_replayed": True,
        "every_operational_comparison_recomputed": True,
        "every_output_byte_fixed_point_replayed": True,
        "all_nine_shared_resource_receipts_replayed": True,
        "V35_semantic_campaign_replayed_before_accounting": True,
        "failure_acquisition_proposal_proof_overlay_planning_and_execution_separate": True,
        "evaluation_excluded_from_operational_comparison": True,
        "final_operational_comparison_totals": final_totals,
        "registered_first_failure_label_axis_sample_tax_reduction_replayed": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(pre.FUTURE_DOMAINS["verification"], payload)
    raw = canonical_json_bytes(
        {**payload, "adaptive_accounting_verification_id": verification_id}
    )
    if (
        (EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID)
        or (
            EXPECTED_VERIFICATION_BYTE_COUNT
            and len(raw) != EXPECTED_VERIFICATION_BYTE_COUNT
        )
        or (
            EXPECTED_VERIFICATION_SHA256 != "0" * 64
            and hashlib.sha256(raw).hexdigest() != EXPECTED_VERIFICATION_SHA256
        )
    ):
        _fail("frozen V36 verification changed")
    return Standard2048AdaptiveAccountedIndependentVerificationV36(
        _ISSUER, raw, campaign_id, verification_id
    )


__all__ = (
    "ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048AdaptiveAccountedIndependentVerificationV36",
    "verify_standard_2048_adaptive_accounting_bytes_independently_v36",
)
