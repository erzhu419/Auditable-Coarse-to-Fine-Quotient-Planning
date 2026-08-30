"""Evidence-bound paired statistics for the hybrid successor campaign."""

from __future__ import annotations

import math
from statistics import fmean
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v1 import (
    HYBRID_CONFIRMATORY_ARMS_V1,
    HYBRID_CONFIRMATORY_CHECKPOINTS_V1,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1,
    HYBRID_INPUT_DIMENSION_V1,
    HYBRID_PARAMETER_COUNT_V1,
    RAW_STANDARD_ARM_V1,
    RAW_STANDARD_INPUT_DIMENSION_V1,
    RAW_STANDARD_PARAMETER_COUNT_V1,
    RESOURCE_CANDIDATE_ARM_V1,
    ROTATED_CONTROL_ARM_V1,
    LatentResourceHybridConfirmatoryProtocolV1Error,
    registered_hybrid_confirmatory_device_v1,
    validate_hybrid_confirmatory_protocol_identity_v1,
    validate_ratified_hybrid_confirmatory_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v1 import (
    HYBRID_CONFIRMATORY_RESULT_SCHEMA_V1,
)
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
    SampleLedgerV1Error,
)
from acfqp.science.statistics_gate_v1 import mean_sem_v1


class HybridConfirmatoryGateV1Error(ValueError):
    """The protocol, matrix evidence, or registered paired test is invalid."""


def _fail(message: str) -> NoReturn:
    raise HybridConfirmatoryGateV1Error(message)


def _not_run_v1(
    *, protocol_id: str, artifact_count: int, reasons: Sequence[str]
) -> dict[str, Any]:
    return {
        "schema": "acfqp.science.latent_resource_hybrid_confirmatory_joint_gate.v1",
        "protocol_id": protocol_id,
        "artifact_count": artifact_count,
        "evidence_complete": False,
        "not_run_reasons": sorted(set(reasons)),
        "JOINT_SCIENTIFIC_SUCCESS_GATE": "NOT_RUN",
        "scientific_success_claimed": False,
    }


def _registered_protocol_v1(protocol: Mapping[str, Any]) -> dict[str, Any]:
    try:
        replayed = validate_hybrid_confirmatory_protocol_identity_v1(protocol)
    except LatentResourceHybridConfirmatoryProtocolV1Error as error:
        raise HybridConfirmatoryGateV1Error(str(error)) from error
    training = replayed.get("training")
    arms = replayed.get("arms")
    seeds = replayed.get("training_seeds")
    if (
        arms != list(HYBRID_CONFIRMATORY_ARMS_V1)
        or seeds != list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1)
        or type(training) is not dict
        or training.get("environment_steps_per_seed_arm") != 100_000
        or training.get("evaluation_checkpoints")
        != list(HYBRID_CONFIRMATORY_CHECKPOINTS_V1)
        or training.get("evaluation_episodes_per_checkpoint") != 64
        or training.get("epsilon_schedule", {}).get("decay_steps") != 100_000
    ):
        _fail("registered hybrid confirmatory matrix or schedule changed")
    execution_authorized = (
        replayed.get("campaign_kind") == "HYBRID_CONFIRMATORY_RATIFIED"
        and replayed.get("authorization") == "RATIFIED_FOR_EXECUTION"
        and replayed.get("confirmatory_protocol_ratified") is True
        and replayed.get("confirmatory_execution_authorized") is True
    )
    if execution_authorized:
        try:
            replayed = validate_ratified_hybrid_confirmatory_protocol_v1(replayed)
        except LatentResourceHybridConfirmatoryProtocolV1Error as error:
            raise HybridConfirmatoryGateV1Error(
                "ratified hybrid protocol is not the frozen template"
            ) from error
    return {
        "protocol": replayed,
        "protocol_id": replayed["protocol_id"],
        "source_commit": replayed.get("source_commit"),
        "training": training,
        "execution_authorized": execution_authorized,
    }


def _registered_update_count_v1(training: Mapping[str, Any]) -> int:
    final = training["environment_steps_per_seed_arm"]
    warmup = training["replay_warmup_environment_steps"]
    every = training["train_every_environment_steps"]
    updates_per_event = training["gradient_updates_per_train_event"]
    if any(type(value) is not int or value <= 0 for value in (
        final,
        warmup,
        every,
        updates_per_event,
    )):
        _fail("registered optimizer update schedule changed")
    first = ((warmup + every - 1) // every) * every
    return 0 if first > final else ((final - first) // every + 1) * updates_per_event


def _parameter_count_v1(arm: str) -> int:
    return (
        RAW_STANDARD_PARAMETER_COUNT_V1
        if arm == RAW_STANDARD_ARM_V1
        else HYBRID_PARAMETER_COUNT_V1
    )


def _input_dimension_v1(arm: str) -> int:
    return (
        RAW_STANDARD_INPUT_DIMENSION_V1
        if arm == RAW_STANDARD_ARM_V1
        else HYBRID_INPUT_DIMENSION_V1
    )


def _positive_integer_v1(value: Any, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be a positive integer")
    return value


def _validate_telemetry_v1(
    artifact: Mapping[str, Any], *, arm: str, expected_updates: int
) -> None:
    latency = artifact["decision_latency_telemetry"]
    compute = artifact["compute_telemetry"]
    representation = artifact["representation_telemetry"]
    if type(latency) is not dict or not {
        "decision_count",
        "total_decision_latency_ns",
    } <= set(latency):
        _fail("decision latency telemetry is incomplete")
    if type(compute) is not dict or not {
        "wall_time_ns",
        "gradient_updates",
        "replay_buffer_draws",
        "peak_device_memory_bytes",
    } <= set(compute):
        _fail("compute telemetry is incomplete")
    required_representation = {
        "executed_arm",
        "input_dimension",
        "raw_observation_bytes",
        "arm_observation_bytes",
        "lossless_raw_board_retained",
        "second_block_kind",
        "second_block_calls_transition_or_successor_kernel",
        "control_second_block_is_bijective_redundancy",
        "candidate_second_block_is_human_inductive_bias",
        "parameter_count_equal_to_rotated_control",
        "parameter_count_equal_to_raw_standard",
        "compression_claimed",
    }
    if type(representation) is not dict or not required_representation <= set(
        representation
    ):
        _fail("representation telemetry is incomplete")
    _positive_integer_v1(latency["decision_count"], label="decision count")
    _positive_integer_v1(
        latency["total_decision_latency_ns"], label="decision latency"
    )
    _positive_integer_v1(compute["wall_time_ns"], label="wall time")
    if (
        compute["gradient_updates"] != expected_updates
        or compute["replay_buffer_draws"] != expected_updates * 256
        or type(compute["peak_device_memory_bytes"]) is not int
        or compute["peak_device_memory_bytes"] < 0
    ):
        _fail("compute telemetry counters changed")
    expected_dimension = _input_dimension_v1(arm)
    expected_second_block = {
        RAW_STANDARD_ARM_V1: "NONE_RAW_STANDARD",
        ROTATED_CONTROL_ARM_V1: "FIXED_180_DEGREE_RAW_REDUNDANCY",
        RESOURCE_CANDIDATE_ARM_V1: "STATE_ONLY_LATENT_RESOURCE",
    }[arm]
    if (
        representation["executed_arm"] != arm
        or representation["input_dimension"] != expected_dimension
        or representation["raw_observation_bytes"] != 64
        or representation["arm_observation_bytes"] != expected_dimension * 4
        or representation["lossless_raw_board_retained"] is not True
        or representation["second_block_kind"] != expected_second_block
        or representation["second_block_calls_transition_or_successor_kernel"]
        is not False
        or representation["control_second_block_is_bijective_redundancy"]
        is not (arm == ROTATED_CONTROL_ARM_V1)
        or representation["candidate_second_block_is_human_inductive_bias"]
        is not (arm == RESOURCE_CANDIDATE_ARM_V1)
        or representation["parameter_count_equal_to_rotated_control"]
        is not (arm in (ROTATED_CONTROL_ARM_V1, RESOURCE_CANDIDATE_ARM_V1))
        or representation["parameter_count_equal_to_raw_standard"]
        is not (arm == RAW_STANDARD_ARM_V1)
        or representation["compression_claimed"] is not False
    ):
        _fail("representation telemetry changed")


def _validate_execution_context_v1(
    artifact: Mapping[str, Any], *, expected_source_commit: str
) -> tuple[str, tuple[Any, ...]]:
    context = artifact["execution_context"]
    required = {
        "execution_id",
        "source_commit",
        "hostname",
        "python_version",
        "numpy_version",
        "torch_version",
        "torch_cuda_runtime_version",
        "torch_cudnn_version",
        "cuda_device_name",
    }
    if type(context) is not dict or not required <= set(context):
        _fail("execution context is incomplete")
    if (
        type(context["execution_id"]) is not str
        or not context["execution_id"]
        or context["source_commit"] != expected_source_commit
        or any(
            type(context[name]) is not str or not context[name]
            for name in (
                "hostname",
                "python_version",
                "numpy_version",
                "torch_version",
                "torch_cuda_runtime_version",
                "cuda_device_name",
            )
        )
        or type(context["torch_cudnn_version"]) is not int
        or context["torch_cudnn_version"] <= 0
    ):
        _fail("execution context changed")
    environment = (
        context["hostname"],
        context["python_version"],
        context["numpy_version"],
        context["torch_version"],
        context["torch_cuda_runtime_version"],
        context["torch_cudnn_version"],
        context["cuda_device_name"],
    )
    return context["execution_id"], environment


def _artifact_scores_v1(
    artifact: Mapping[str, Any],
) -> tuple[dict[int, float], int]:
    evaluations = artifact["evaluations"]
    if type(evaluations) is not list:
        _fail("checkpoint evidence is not a list")
    rows: dict[int, float] = {}
    total_decisions = 0
    for evaluation in evaluations:
        if type(evaluation) is not dict or not {
            "checkpoint_environment_interactions",
            "episode_count",
            "mean_total_merge_score",
            "episodes",
        } <= set(evaluation):
            _fail("checkpoint evidence is incomplete")
        checkpoint = evaluation["checkpoint_environment_interactions"]
        episodes = evaluation["episodes"]
        score = evaluation["mean_total_merge_score"]
        if (
            type(checkpoint) is not int
            or checkpoint in rows
            or evaluation["episode_count"] != 64
            or type(episodes) is not list
            or len(episodes) != 64
            or type(score) not in (int, float)
            or not math.isfinite(float(score))
            or float(score) < 0
        ):
            _fail("checkpoint evidence changed")
        episode_scores: list[int] = []
        episode_indices: set[int] = set()
        for episode in episodes:
            if (
                type(episode) is not dict
                or type(episode.get("episode_index")) is not int
                or episode["episode_index"] in episode_indices
                or type(episode.get("total_merge_score")) is not int
                or episode["total_merge_score"] < 0
                or type(episode.get("decision_count")) is not int
                or episode["decision_count"] <= 0
            ):
                _fail("episode outcome evidence changed")
            episode_indices.add(episode["episode_index"])
            episode_scores.append(episode["total_merge_score"])
            total_decisions += episode["decision_count"]
        if episode_indices != set(range(64)):
            _fail("registered evaluation episodes are incomplete")
        if not math.isclose(
            float(score), fmean(episode_scores), rel_tol=0.0, abs_tol=0.0
        ):
            _fail("checkpoint mean does not replay from episode outcomes")
        rows[checkpoint] = float(score)
    if tuple(sorted(rows)) != HYBRID_CONFIRMATORY_CHECKPOINTS_V1:
        _fail("all three registered checkpoints are required")
    return rows, total_decisions


def _paired_test_v1(
    differences: Sequence[float], *, alternative: str
) -> dict[str, Any]:
    values = tuple(float(value) for value in differences)
    summary = mean_sem_v1(values)
    standard_error = float(summary["sem"])
    if standard_error <= 0:
        _fail("paired effect has zero uncertainty")
    try:
        from scipy import stats
    except ImportError as error:  # pragma: no cover - experiment dependency
        raise HybridConfirmatoryGateV1Error(
            "SciPy is required for the registered paired tests"
        ) from error
    mean = float(summary["mean"])
    degrees = len(values) - 1
    statistic = mean / standard_error
    if alternative == "greater":
        p_value = float(stats.t.sf(statistic, degrees))
        lower = mean - float(stats.t.ppf(0.95, degrees)) * standard_error
        return {
            "alternative": "GREATER_THAN_ZERO",
            "difference_summary": summary,
            "t_statistic": statistic,
            "degrees_of_freedom": degrees,
            "one_sided_p_value": p_value,
            "difference_ci95_one_sided_lower": lower,
            "passes_registered_test": (
                mean > 0 and p_value < 0.05 and lower > 0
            ),
        }
    if alternative != "two-sided":
        _fail("paired test alternative changed")
    critical = float(stats.t.ppf(0.975, degrees))
    half_width = critical * standard_error
    p_value = float(2.0 * stats.t.sf(abs(statistic), degrees))
    return {
        "alternative": "TWO_SIDED",
        "difference_summary": summary,
        "t_statistic": statistic,
        "degrees_of_freedom": degrees,
        "two_sided_p_value": p_value,
        "difference_ci95_lower": mean - half_width,
        "difference_ci95_upper": mean + half_width,
        "passes_registered_test": (
            mean > 0 and p_value < 0.05 and mean - half_width > 0
        ),
    }


def _welch_sensitivity_v1(
    candidate: Sequence[float], baseline: Sequence[float]
) -> dict[str, Any]:
    candidate_values = tuple(float(value) for value in candidate)
    baseline_values = tuple(float(value) for value in baseline)
    candidate_summary = mean_sem_v1(candidate_values)
    baseline_summary = mean_sem_v1(baseline_values)
    try:
        from scipy import stats
    except ImportError as error:  # pragma: no cover - experiment dependency
        raise HybridConfirmatoryGateV1Error(
            "SciPy is required for the registered sensitivity report"
        ) from error
    result = stats.ttest_ind(candidate_values, baseline_values, equal_var=False)
    variance_candidate = float(candidate_summary["sample_standard_deviation"]) ** 2
    variance_baseline = float(baseline_summary["sample_standard_deviation"]) ** 2
    se_squared = variance_candidate / len(candidate_values) + variance_baseline / len(
        baseline_values
    )
    if se_squared <= 0:
        return {
            "status": "NOT_COMPUTABLE_ZERO_UNCERTAINTY",
            "changes_primary_gate": False,
        }
    degrees = se_squared**2 / (
        (variance_candidate / len(candidate_values)) ** 2
        / (len(candidate_values) - 1)
        + (variance_baseline / len(baseline_values)) ** 2
        / (len(baseline_values) - 1)
    )
    difference = float(candidate_summary["mean"]) - float(
        baseline_summary["mean"]
    )
    half_width = float(stats.t.ppf(0.975, degrees)) * math.sqrt(se_squared)
    return {
        "status": "REPORTED_SENSITIVITY_ONLY",
        "candidate_minus_baseline_mean": difference,
        "t_statistic": float(result.statistic),
        "two_sided_p_value": float(result.pvalue),
        "degrees_of_freedom": degrees,
        "difference_ci95_lower": difference - half_width,
        "difference_ci95_upper": difference + half_width,
        "changes_primary_gate": False,
    }


def evaluate_hybrid_confirmatory_joint_gate_v1(
    *,
    protocol: Mapping[str, Any],
    seed_arm_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate the exact 30-artifact matrix under the frozen paired gate."""

    registered = _registered_protocol_v1(protocol)
    if type(seed_arm_artifacts) not in (list, tuple):
        _fail("seed-arm artifacts must be a list or tuple")
    protocol_id = registered["protocol_id"]
    expected_identities = {
        (arm, seed)
        for arm in HYBRID_CONFIRMATORY_ARMS_V1
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1
    }
    if registered["execution_authorized"] is not True:
        return _not_run_v1(
            protocol_id=protocol_id,
            artifact_count=len(seed_arm_artifacts),
            reasons=["hybrid confirmatory protocol is not ratified for execution"],
        )
    if len(seed_arm_artifacts) < len(expected_identities):
        present_arms = {
            artifact.get("arm")
            for artifact in seed_arm_artifacts
            if type(artifact) is dict
        }
        missing_arms = sorted(set(HYBRID_CONFIRMATORY_ARMS_V1) - present_arms)
        reasons = ["requires the complete 30 registered seed-arm artifacts"]
        if missing_arms:
            reasons.append("missing arms: " + ",".join(missing_arms))
        return _not_run_v1(
            protocol_id=protocol_id,
            artifact_count=len(seed_arm_artifacts),
            reasons=reasons,
        )
    if len(seed_arm_artifacts) > len(expected_identities):
        _fail("foreign or duplicate seed-arm artifacts supplied")

    training = registered["training"]
    expected_updates = _registered_update_count_v1(training)
    expected_steps = training["environment_steps_per_seed_arm"]
    scores: dict[str, dict[int, dict[int, float]]] = {
        arm: {checkpoint: {} for checkpoint in HYBRID_CONFIRMATORY_CHECKPOINTS_V1}
        for arm in HYBRID_CONFIRMATORY_ARMS_V1
    }
    identities: set[tuple[str, int]] = set()
    execution_ids: set[str] = set()
    execution_environments: set[tuple[Any, ...]] = set()
    required_fields = {
        "schema",
        "protocol_id",
        "device",
        "arm",
        "seed",
        "network_parameter_count",
        "training_environment_interactions",
        "evaluations",
        "sample_ledger",
        "decision_latency_telemetry",
        "compute_telemetry",
        "representation_telemetry",
        "execution_context",
        "tape_binding",
        "hybrid_confirmatory_joint_gate",
        "scientific_success_claimed",
    }
    for artifact in seed_arm_artifacts:
        if type(artifact) is not dict:
            _fail("seed-arm artifact must be a plain object")
        missing = sorted(required_fields - set(artifact))
        if missing:
            return _not_run_v1(
                protocol_id=protocol_id,
                artifact_count=len(seed_arm_artifacts),
                reasons=["artifact fields missing: " + ",".join(missing)],
            )
        arm = artifact["arm"]
        seed = artifact["seed"]
        identity = (arm, seed)
        if (
            artifact["schema"] != HYBRID_CONFIRMATORY_RESULT_SCHEMA_V1
            or artifact["protocol_id"] != protocol_id
            or artifact["device"] != registered_hybrid_confirmatory_device_v1(seed)
            or identity not in expected_identities
        ):
            _fail("foreign hybrid seed-arm artifact supplied")
        if identity in identities:
            _fail("duplicate hybrid seed-arm artifact supplied")
        identities.add(identity)
        if artifact["network_parameter_count"] != _parameter_count_v1(arm):
            _fail("registered arm network parameter count changed")
        if artifact["training_environment_interactions"] != expected_steps:
            _fail("training interaction budget changed")
        if (
            artifact["hybrid_confirmatory_joint_gate"]
            != "NOT_RUN_REQUIRES_COMPLETE_30_ARTIFACT_MATRIX"
            or artifact["scientific_success_claimed"] is not False
        ):
            _fail("single-job artifact gate state changed")
        tape = artifact["tape_binding"]
        expected_training_tape = (
            f"{registered['protocol']['training_tape_prefix']}:{seed}"
        )
        if (
            type(tape) is not dict
            or tape.get("training_tape_root") != expected_training_tape
            or tape.get("evaluation_tape_root")
            != registered["protocol"]["evaluation_tape_prefix"]
            or tape.get("same_seed_training_tape_across_arms") is not True
            or tape.get("same_evaluation_tapes_across_all_seed_arms") is not True
        ):
            _fail("registered seed-paired tape binding changed")
        try:
            ledger = SampleLedgerV1.from_document(artifact["sample_ledger"])
        except SampleLedgerV1Error as error:
            raise HybridConfirmatoryGateV1Error("sample ledger is invalid") from error
        if ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        ) != expected_steps:
            _fail("training ENVIRONMENT_INTERACTION ledger count changed")
        if ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        ) != 2 * expected_steps:
            _fail("training action-mask query ledger count changed")
        ledger_document = ledger.to_document()
        if (
            ledger_document["diagnostic_counters"]["gradient_updates"]
            != expected_updates
        ):
            _fail("gradient update count changed")
        if (
            ledger_document["diagnostic_counters"]["replay_buffer_draws"]
            != expected_updates * 256
        ):
            _fail("replay buffer draw count changed")
        artifact_scores, evaluation_decisions = _artifact_scores_v1(artifact)
        if ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION,
            EvidenceLane.STANDALONE_EVALUATION,
        ) != evaluation_decisions:
            _fail("standalone evaluation interaction ledger count changed")
        if ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY,
            EvidenceLane.STANDALONE_EVALUATION,
        ) != evaluation_decisions:
            _fail("standalone evaluation action-mask ledger count changed")
        if any(
            ledger.evidence_count(evidence_class, lane) != 0
            for evidence_class in EvidenceClass
            for lane in EvidenceLane
            if (evidence_class, lane)
            not in {
                (
                    EvidenceClass.ENVIRONMENT_INTERACTION,
                    EvidenceLane.ONLINE_TARGET,
                ),
                (
                    EvidenceClass.ENVIRONMENT_INTERACTION,
                    EvidenceLane.STANDALONE_EVALUATION,
                ),
                (EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET),
                (
                    EvidenceClass.EXACT_KERNEL_QUERY,
                    EvidenceLane.STANDALONE_EVALUATION,
                ),
            }
        ):
            _fail("unregistered evidence authority was used")
        _validate_telemetry_v1(
            artifact, arm=arm, expected_updates=expected_updates
        )
        if (
            artifact["decision_latency_telemetry"]["decision_count"]
            != evaluation_decisions
        ):
            _fail("decision latency count does not replay from episode outcomes")
        execution_id, environment = _validate_execution_context_v1(
            artifact, expected_source_commit=registered["source_commit"]
        )
        if execution_id in execution_ids:
            _fail("duplicate execution identity supplied")
        execution_ids.add(execution_id)
        execution_environments.add(environment)
        for checkpoint, score in artifact_scores.items():
            scores[arm][checkpoint][seed] = score

    if identities != expected_identities:
        return _not_run_v1(
            protocol_id=protocol_id,
            artifact_count=len(seed_arm_artifacts),
            reasons=["registered seed-arm identities are incomplete"],
        )
    if len(execution_environments) != 1:
        _fail("hybrid confirmatory execution environments changed")

    ordered_scores = {
        arm: {
            checkpoint: tuple(
                scores[arm][checkpoint][seed]
                for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1
            )
            for checkpoint in HYBRID_CONFIRMATORY_CHECKPOINTS_V1
        }
        for arm in HYBRID_CONFIRMATORY_ARMS_V1
    }
    raw_final = ordered_scores[RAW_STANDARD_ARM_V1][100_000]
    raw_early_25 = ordered_scores[RAW_STANDARD_ARM_V1][25_000]
    raw_early_50 = ordered_scores[RAW_STANDARD_ARM_V1][50_000]
    candidate_mid = ordered_scores[RESOURCE_CANDIDATE_ARM_V1][50_000]
    candidate_final = ordered_scores[RESOURCE_CANDIDATE_ARM_V1][100_000]
    rotated_final = ordered_scores[ROTATED_CONTROL_ARM_V1][100_000]
    sample_tax_differences = tuple(
        candidate - 0.99 * raw
        for candidate, raw in zip(candidate_mid, raw_final, strict=True)
    )
    raw_early_nonattainment_differences = tuple(
        0.99 * raw_final_score - max(raw_25_score, raw_50_score)
        for raw_final_score, raw_25_score, raw_50_score in zip(
            raw_final, raw_early_25, raw_early_50, strict=True
        )
    )
    candidate_raw_final_differences = tuple(
        candidate - raw
        for candidate, raw in zip(candidate_final, raw_final, strict=True)
    )
    candidate_rotated_final_differences = tuple(
        candidate - rotated
        for candidate, rotated in zip(candidate_final, rotated_final, strict=True)
    )
    sample_tax_test = _paired_test_v1(
        sample_tax_differences, alternative="greater"
    )
    raw_early_nonattainment_test = _paired_test_v1(
        raw_early_nonattainment_differences, alternative="greater"
    )
    candidate_raw_test = _paired_test_v1(
        candidate_raw_final_differences, alternative="two-sided"
    )
    candidate_rotated_test = _paired_test_v1(
        candidate_rotated_final_differences, alternative="two-sided"
    )
    component_passes = (
        sample_tax_test["passes_registered_test"],
        raw_early_nonattainment_test["passes_registered_test"],
        candidate_raw_test["passes_registered_test"],
        candidate_rotated_test["passes_registered_test"],
    )
    passed = all(component_passes)
    sample_tax_strictly_lower = (
        sample_tax_test["passes_registered_test"]
        and raw_early_nonattainment_test["passes_registered_test"]
    )
    checkpoint_summaries = {
        arm: {
            str(checkpoint): mean_sem_v1(ordered_scores[arm][checkpoint])
            for checkpoint in HYBRID_CONFIRMATORY_CHECKPOINTS_V1
        }
        for arm in HYBRID_CONFIRMATORY_ARMS_V1
    }
    return {
        "schema": "acfqp.science.latent_resource_hybrid_confirmatory_joint_gate.v1",
        "protocol_id": protocol_id,
        "source_commit": registered["source_commit"],
        "artifact_count": len(seed_arm_artifacts),
        "evidence_complete": True,
        "seed_count_per_arm": len(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1),
        "registered_unique_seeds": list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1),
        "arms_executed": list(HYBRID_CONFIRMATORY_ARMS_V1),
        "checkpoints": list(HYBRID_CONFIRMATORY_CHECKPOINTS_V1),
        "training_environment_interactions_per_seed_arm": expected_steps,
        "seed_is_statistical_unit": True,
        "evaluation_episode_is_statistical_unit": False,
        "uncertainty_is_across_ten_training_seeds": True,
        "fixed_evaluation_tapes_establish_iid_environment_generalization": False,
        "same_seed_training_tapes_validated": True,
        "same_evaluation_tapes_validated": True,
        "sample_ledgers_validated": True,
        "execution_identity_count": len(execution_ids),
        "execution_environment_count": len(execution_environments),
        "network_parameter_counts_by_arm": {
            arm: _parameter_count_v1(arm) for arm in HYBRID_CONFIRMATORY_ARMS_V1
        },
        "candidate_and_rotated_control_parameter_count_equal": True,
        "candidate_and_raw_standard_parameter_count_equal": False,
        "raw_standard_is_general_rl_benchmark_not_pure_representation_control": True,
        "maximum_positive_claim_scope": registered["protocol"]["claim_boundary"][
            "maximum_positive_claim_scope"
        ],
        "economics_scalar_break_even_and_official_execution_gates": {
            name: registered["protocol"]["claim_boundary"][name]
            for name in (
                "WORKLOAD_ECONOMICS_GATE",
                "SCALAR_CALIBRATION_GATE",
                "BREAK_EVEN_GATE",
                "OFFICIAL_EXECUTION_GATE",
            )
        },
        "checkpoint_score_mean_sem_by_arm": checkpoint_summaries,
        "primary_seed_paired_gate": {
            "global_null": "AT_LEAST_ONE_COMPONENT_CLAIM_IS_FALSE",
            "global_alternative": "ALL_FOUR_COMPONENT_CLAIMS_ARE_TRUE",
            "multiple_testing_rule": "INTERSECTION_UNION_NO_ALPHA_SPLIT",
            "component_results_confirmatory_only_if_strict_conjunction_passes": True,
            "candidate_50000_threshold_attainment": (
                sample_tax_test
            ),
            "raw_early_threshold_nonattainment": raw_early_nonattainment_test,
            "raw_early_nonattainment_uses_maximum_of_25000_and_50000": True,
            "sample_tax_strictly_lower": sample_tax_strictly_lower,
            "candidate_100000_minus_raw_100000": candidate_raw_test,
            "candidate_100000_minus_rotated_100000": candidate_rotated_test,
            "strict_conjunction_passed": passed,
            "component_results_descriptive_only_due_to_joint_failure": not passed,
        },
        "welch_sensitivity_not_gate": {
            "candidate_100000_vs_raw_100000": _welch_sensitivity_v1(
                candidate_final, raw_final
            ),
            "candidate_100000_vs_rotated_100000": _welch_sensitivity_v1(
                candidate_final, rotated_final
            ),
            "can_change_joint_gate": False,
        },
        "gradient_updates_per_seed_arm": expected_updates,
        "JOINT_SCIENTIFIC_SUCCESS_GATE": "PASS" if passed else "FAIL",
        "scientific_success_claimed": passed,
    }


__all__ = (
    "HYBRID_CONFIRMATORY_RESULT_SCHEMA_V1",
    "HybridConfirmatoryGateV1Error",
    "evaluate_hybrid_confirmatory_joint_gate_v1",
)
