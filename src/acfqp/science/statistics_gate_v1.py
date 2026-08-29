"""Cross-seed statistics and evidence-bound confirmatory success gate."""

from __future__ import annotations

import hashlib
import math
import re
from statistics import fmean
from typing import Any, Mapping, Sequence

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.latent_resource_2048_v1 import (
    STATE_ONLY_RESOURCE_FEATURE_NAMES_V1,
)
from acfqp.science.latent_resource_protocol_v1 import (
    PILOT_ARMS,
    PROTOCOL_DOMAIN,
    LatentResourceProtocolV1Error,
    validate_ratified_confirmatory_protocol_v1,
    zero_mask_coordinate_indices_v1,
)
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
    SampleLedgerV1Error,
)


CONFIRMATORY_RESULT_SCHEMA_V1 = (
    "acfqp.science.matched_double_dqn_2048_confirmatory_seed_arm_result.v1"
)
NETWORK_PARAMETER_COUNT_V1 = 71_172


class StatisticsGateV1Error(ValueError):
    """A protocol, seed result, checkpoint series, or dependency is invalid."""


def mean_sem_v1(values: Sequence[float]) -> dict[str, float | int]:
    """Summarize a numeric sample; this low-level helper may consume arrays."""

    materialized = tuple(float(value) for value in values)
    if len(materialized) < 2 or any(not math.isfinite(value) for value in materialized):
        raise StatisticsGateV1Error("mean/SEM needs at least two finite values")
    mean = fmean(materialized)
    variance = sum((value - mean) ** 2 for value in materialized) / (
        len(materialized) - 1
    )
    return {
        "count": len(materialized),
        "mean": mean,
        "sample_standard_deviation": math.sqrt(variance),
        "sem": math.sqrt(variance / len(materialized)),
    }


def earliest_threshold_v1(
    checkpoint_means: Mapping[int, float], threshold: float
) -> int | None:
    if (
        type(checkpoint_means) is not dict
        or not checkpoint_means
        or not math.isfinite(float(threshold))
        or any(
            type(step) is not int
            or step <= 0
            or not math.isfinite(float(value))
            for step, value in checkpoint_means.items()
        )
    ):
        raise StatisticsGateV1Error("checkpoint threshold input changed")
    for step in sorted(checkpoint_means):
        if float(checkpoint_means[step]) >= float(threshold):
            return step
    return None


def _welch_v1(candidate: Sequence[float], baseline: Sequence[float]) -> dict[str, float]:
    """Run the preregistered Welch test on evidence-validated arrays."""

    candidate_values = tuple(float(value) for value in candidate)
    baseline_values = tuple(float(value) for value in baseline)
    candidate_summary = mean_sem_v1(candidate_values)
    baseline_summary = mean_sem_v1(baseline_values)
    try:
        from scipy import stats
    except ImportError as error:  # pragma: no cover - GPU environment dependency
        raise StatisticsGateV1Error(
            "SciPy is required for the preregistered Welch test"
        ) from error
    result = stats.ttest_ind(candidate_values, baseline_values, equal_var=False)
    n_c = len(candidate_values)
    n_b = len(baseline_values)
    var_c = float(candidate_summary["sample_standard_deviation"]) ** 2
    var_b = float(baseline_summary["sample_standard_deviation"]) ** 2
    se_squared = var_c / n_c + var_b / n_b
    if se_squared <= 0:
        raise StatisticsGateV1Error("Welch effect has zero uncertainty")
    degrees = se_squared**2 / (
        (var_c / n_c) ** 2 / (n_c - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    )
    critical = float(stats.t.ppf(0.975, degrees))
    difference = float(candidate_summary["mean"]) - float(baseline_summary["mean"])
    standard_error = math.sqrt(se_squared)
    return {
        "candidate_minus_baseline_mean": difference,
        "t_statistic": float(result.statistic),
        "two_sided_p_value": float(result.pvalue),
        "degrees_of_freedom": degrees,
        "difference_standard_error": standard_error,
        "difference_ci95_lower": difference - critical * standard_error,
        "difference_ci95_upper": difference + critical * standard_error,
    }


def _not_run_v1(
    *, protocol_id: str, reasons: Sequence[str], artifact_count: int
) -> dict[str, Any]:
    return {
        "schema": "acfqp.science.latent_resource_confirmatory_joint_gate.v1",
        "protocol_id": protocol_id,
        "artifact_count": artifact_count,
        "evidence_complete": False,
        "not_run_reasons": sorted(set(reasons)),
        "JOINT_SCIENTIFIC_SUCCESS_GATE": "NOT_RUN",
        "scientific_success_claimed": False,
    }


def _registered_protocol_v1(protocol: Mapping[str, Any]) -> dict[str, Any]:
    if type(protocol) is not dict:
        raise StatisticsGateV1Error("confirmatory protocol must be a plain object")
    required = {
        "protocol_id",
        "campaign_kind",
        "arms",
        "training_seeds",
        "training",
        "joint_success_gate",
        "authorization",
        "claim_boundary",
    }
    if not required <= set(protocol):
        raise StatisticsGateV1Error("confirmatory protocol is incomplete")
    protocol_id = protocol["protocol_id"]
    if type(protocol_id) is not str or len(protocol_id) != 64:
        raise StatisticsGateV1Error("confirmatory protocol identity changed")
    payload = dict(protocol)
    del payload["protocol_id"]
    reconstructed_id = hashlib.sha256(
        PROTOCOL_DOMAIN.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    if reconstructed_id != protocol_id:
        raise StatisticsGateV1Error("confirmatory protocol identity is not replayable")
    arms = protocol["arms"]
    seeds = protocol["training_seeds"]
    training = protocol["training"]
    gate = protocol["joint_success_gate"]
    if (
        type(arms) is not list
        or len(arms) != 4
        or any(type(arm) is not str or not arm for arm in arms)
        or len(set(arms)) != 4
        or type(seeds) is not list
        or len(seeds) != 10
        or any(type(seed) is not int for seed in seeds)
        or len(set(seeds)) != 10
        or type(training) is not dict
        or type(gate) is not dict
    ):
        raise StatisticsGateV1Error("registered arm or seed matrix changed")
    checkpoints = training.get("evaluation_checkpoints")
    if (
        training.get("environment_steps_per_seed_arm") != 500_000
        or type(checkpoints) is not list
        or len(checkpoints) != 6
        or tuple(checkpoints) != tuple(sorted(set(checkpoints)))
        or checkpoints[-1] != 500_000
        or training.get("evaluation_episodes_per_checkpoint") != 64
    ):
        raise StatisticsGateV1Error("registered confirmatory schedule changed")
    reference_arm = gate.get("reference_arm")
    candidate_arm = gate.get("candidate_arm")
    if (
        type(reference_arm) is not str
        or type(candidate_arm) is not str
        or reference_arm == candidate_arm
        or reference_arm not in arms
        or candidate_arm not in arms
    ):
        raise StatisticsGateV1Error("joint gate arm authorities changed")
    claim_boundary = protocol["claim_boundary"]
    if type(claim_boundary) is not dict:
        raise StatisticsGateV1Error("confirmatory claim boundary changed")
    execution_authorized = (
        protocol["campaign_kind"] == "CONFIRMATORY_RATIFIED"
        and protocol["authorization"] == "RATIFIED_FOR_EXECUTION"
        and protocol.get("confirmatory_protocol_ratified") is True
        and protocol.get("confirmatory_execution_authorized") is True
        and claim_boundary.get("official_execution_allowed") is False
        and claim_boundary.get("OFFICIAL_EXECUTION_GATE") == "NOT_RUN"
        and type(protocol.get("source_commit")) is str
        and re.fullmatch(r"[0-9a-f]{40}", protocol["source_commit"]) is not None
    )
    if execution_authorized:
        try:
            validate_ratified_confirmatory_protocol_v1(protocol)
        except LatentResourceProtocolV1Error as error:
            raise StatisticsGateV1Error(
                "ratified protocol is not the frozen confirmatory template"
            ) from error
    return {
        "protocol_id": protocol_id,
        "arms": tuple(arms),
        "seeds": tuple(seeds),
        "training": training,
        "checkpoints": tuple(checkpoints),
        "reference_arm": reference_arm,
        "candidate_arm": candidate_arm,
        "ablation_arms": tuple(
            arm for arm in arms if arm not in (reference_arm, candidate_arm)
        ),
        "execution_authorized": execution_authorized,
        "source_commit": protocol.get("source_commit"),
    }


def _registered_update_count_v1(training: Mapping[str, Any]) -> int:
    environment_steps = training.get("environment_steps_per_seed_arm")
    warmup = training.get("replay_warmup_environment_steps")
    train_every = training.get("train_every_environment_steps")
    updates_per_event = training.get("gradient_updates_per_train_event")
    if (
        type(environment_steps) is not int
        or type(warmup) is not int
        or type(train_every) is not int
        or type(updates_per_event) is not int
        or environment_steps <= 0
        or warmup <= 0
        or train_every <= 0
        or updates_per_event <= 0
    ):
        raise StatisticsGateV1Error("registered update schedule changed")
    first_train_interaction = (
        (warmup + train_every - 1) // train_every
    ) * train_every
    if first_train_interaction > environment_steps:
        return 0
    train_events = (
        (environment_steps - first_train_interaction) // train_every
    ) + 1
    return train_events * updates_per_event


def _plain_nonempty_telemetry_v1(value: Any, *, name: str) -> Mapping[str, Any]:
    if type(value) is not dict or not value:
        raise StatisticsGateV1Error(f"{name} telemetry is incomplete")
    if any(type(key) is not str or not key for key in value):
        raise StatisticsGateV1Error(f"{name} telemetry fields changed")
    return value


def _positive_integer_v1(value: Any, *, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise StatisticsGateV1Error(f"{name} must be a positive integer")
    return value


def _validate_telemetry_v1(
    artifact: Mapping[str, Any], *, arm: str, expected_updates: int
) -> None:
    latency = _plain_nonempty_telemetry_v1(
        artifact["decision_latency_telemetry"], name="decision latency"
    )
    compute = _plain_nonempty_telemetry_v1(
        artifact["compute_telemetry"], name="compute"
    )
    compression = _plain_nonempty_telemetry_v1(
        artifact["representation_telemetry"], name="compression"
    )
    if not {"decision_count", "total_decision_latency_ns"} <= set(latency):
        raise StatisticsGateV1Error("decision latency telemetry is incomplete")
    if not {
        "wall_time_ns",
        "gradient_updates",
        "replay_buffer_draws",
        "peak_device_memory_bytes",
    } <= set(compute):
        raise StatisticsGateV1Error("compute telemetry is incomplete")
    if not {
        "executed_arm",
        "input_dimension",
        "raw_observation_bytes",
        "arm_observation_bytes",
        "zero_mask_coordinate_indices",
        "zero_mask_coordinate_names",
        "zero_mask_applied_after_full_state_only_encoding",
        "equal_dimension_is_not_counted_as_compression",
        "compression_claimed",
    } <= set(compression):
        raise StatisticsGateV1Error("compression telemetry is incomplete")
    _positive_integer_v1(latency["decision_count"], name="decision count")
    _positive_integer_v1(
        latency["total_decision_latency_ns"], name="total decision latency"
    )
    _positive_integer_v1(compute["wall_time_ns"], name="wall time")
    if (
        type(compute["gradient_updates"]) is not int
        or compute["gradient_updates"] != expected_updates
        or type(compute["replay_buffer_draws"]) is not int
        or compute["replay_buffer_draws"] < 0
        or type(compute["peak_device_memory_bytes"]) is not int
        or compute["peak_device_memory_bytes"] < 0
    ):
        raise StatisticsGateV1Error("compute telemetry counters changed")
    expected_zero_mask = zero_mask_coordinate_indices_v1(arm)
    if (
        compression["executed_arm"] != arm
        or compression["input_dimension"] != 16
        or compression["raw_observation_bytes"] != 64
        or compression["arm_observation_bytes"] != 64
        or compression["zero_mask_coordinate_indices"] != list(expected_zero_mask)
        or compression["zero_mask_coordinate_names"]
        != [STATE_ONLY_RESOURCE_FEATURE_NAMES_V1[index] for index in expected_zero_mask]
        or compression["zero_mask_applied_after_full_state_only_encoding"]
        is not (arm not in PILOT_ARMS)
        or compression["equal_dimension_is_not_counted_as_compression"] is not True
        or compression["compression_claimed"] is not False
    ):
        raise StatisticsGateV1Error("compression telemetry changed")


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
        raise StatisticsGateV1Error("execution context is incomplete")
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
        raise StatisticsGateV1Error("execution context changed")
    return context["execution_id"], (
        context["hostname"],
        context["python_version"],
        context["numpy_version"],
        context["torch_version"],
        context["torch_cuda_runtime_version"],
        context["torch_cudnn_version"],
        context["cuda_device_name"],
    )


def _artifact_scores_v1(
    artifact: Mapping[str, Any],
    *,
    expected_checkpoints: tuple[int, ...],
    expected_evaluation_episodes: int,
) -> tuple[dict[int, float], int]:
    evaluations = artifact["evaluations"]
    if type(evaluations) is not list:
        raise StatisticsGateV1Error("checkpoint evidence is not a list")
    rows: dict[int, float] = {}
    total_decisions = 0
    for row in evaluations:
        if type(row) is not dict:
            raise StatisticsGateV1Error("checkpoint evidence row changed")
        required = {
            "checkpoint_environment_interactions",
            "episode_count",
            "mean_total_merge_score",
            "episodes",
        }
        if not required <= set(row):
            raise StatisticsGateV1Error("checkpoint evidence is incomplete")
        checkpoint = row["checkpoint_environment_interactions"]
        score = row["mean_total_merge_score"]
        episodes = row["episodes"]
        if (
            type(checkpoint) is not int
            or checkpoint in rows
            or row["episode_count"] != expected_evaluation_episodes
            or type(score) not in (int, float)
            or not math.isfinite(float(score))
            or float(score) < 0
            or type(episodes) is not list
            or len(episodes) != expected_evaluation_episodes
        ):
            raise StatisticsGateV1Error("checkpoint evidence changed")
        episode_scores: list[int] = []
        seen_episode_indices: set[int] = set()
        for episode in episodes:
            if (
                type(episode) is not dict
                or type(episode.get("episode_index")) is not int
                or episode["episode_index"] in seen_episode_indices
                or type(episode.get("total_merge_score")) is not int
                or episode["total_merge_score"] < 0
                or type(episode.get("decision_count")) is not int
                or episode["decision_count"] <= 0
            ):
                raise StatisticsGateV1Error("episode outcome evidence changed")
            seen_episode_indices.add(episode["episode_index"])
            episode_scores.append(episode["total_merge_score"])
            total_decisions += episode["decision_count"]
        if seen_episode_indices != set(range(expected_evaluation_episodes)):
            raise StatisticsGateV1Error("registered evaluation episodes are incomplete")
        if not math.isclose(
            float(score), fmean(episode_scores), rel_tol=0.0, abs_tol=0.0
        ):
            raise StatisticsGateV1Error(
                "checkpoint mean does not replay from episode outcomes"
            )
        rows[checkpoint] = float(score)
    if tuple(sorted(rows)) != expected_checkpoints:
        raise StatisticsGateV1Error("all six registered checkpoints are required")
    return rows, total_decisions


def evaluate_confirmatory_joint_gate_v1(
    *,
    protocol: Mapping[str, Any],
    seed_arm_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate only from the complete registered seed-arm artifact matrix.

    A partial campaign returns ``NOT_RUN``.  Contradictory, foreign, duplicate,
    or internally invalid evidence is rejected instead of being converted into
    favorable anonymous score arrays.
    """

    registered = _registered_protocol_v1(protocol)
    if type(seed_arm_artifacts) not in (list, tuple):
        raise StatisticsGateV1Error("seed-arm artifacts must be a list or tuple")
    expected_arms = registered["arms"]
    expected_seeds = registered["seeds"]
    expected_checkpoints = registered["checkpoints"]
    training = registered["training"]
    protocol_id = registered["protocol_id"]
    expected_environment_steps = training["environment_steps_per_seed_arm"]
    expected_evaluation_episodes = training["evaluation_episodes_per_checkpoint"]
    expected_updates = _registered_update_count_v1(training)
    expected_identities = {
        (arm, seed) for arm in expected_arms for seed in expected_seeds
    }
    if registered["execution_authorized"] is not True:
        return _not_run_v1(
            protocol_id=protocol_id,
            reasons=["confirmatory protocol is not ratified for science execution"],
            artifact_count=len(seed_arm_artifacts),
        )
    if len(seed_arm_artifacts) < len(expected_identities):
        present_arms = {
            artifact.get("arm")
            for artifact in seed_arm_artifacts
            if type(artifact) is dict
        }
        missing_arms = sorted(set(expected_arms) - present_arms)
        reasons = [
            f"requires {len(expected_identities)} registered seed-arm artifacts"
        ]
        if missing_arms:
            reasons.append("missing arms: " + ",".join(missing_arms))
        return _not_run_v1(
            protocol_id=protocol_id,
            reasons=reasons,
            artifact_count=len(seed_arm_artifacts),
        )
    if len(seed_arm_artifacts) > len(expected_identities):
        raise StatisticsGateV1Error("foreign or duplicate seed-arm artifacts supplied")

    scores: dict[str, dict[int, dict[int, float]]] = {
        arm: {checkpoint: {} for checkpoint in expected_checkpoints}
        for arm in expected_arms
    }
    identities: set[tuple[str, int]] = set()
    gradient_updates_by_arm: dict[str, list[int]] = {
        arm: [] for arm in expected_arms
    }
    execution_ids: set[str] = set()
    execution_environments: set[tuple[Any, ...]] = set()
    for artifact in seed_arm_artifacts:
        if type(artifact) is not dict:
            raise StatisticsGateV1Error("seed-arm artifact must be a plain object")
        required = {
            "schema",
            "protocol_id",
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
        }
        missing = sorted(required - set(artifact))
        if missing:
            return _not_run_v1(
                protocol_id=protocol_id,
                reasons=["artifact fields missing: " + ",".join(missing)],
                artifact_count=len(seed_arm_artifacts),
            )
        arm = artifact["arm"]
        seed = artifact["seed"]
        identity = (arm, seed)
        if (
            artifact["schema"] != CONFIRMATORY_RESULT_SCHEMA_V1
            or artifact["protocol_id"] != protocol_id
            or type(arm) is not str
            or type(seed) is not int
            or identity not in expected_identities
        ):
            raise StatisticsGateV1Error("foreign seed-arm artifact supplied")
        if identity in identities:
            raise StatisticsGateV1Error("duplicate seed-arm artifact supplied")
        identities.add(identity)
        if artifact["network_parameter_count"] != NETWORK_PARAMETER_COUNT_V1:
            raise StatisticsGateV1Error("network parameter count changed")
        if artifact["training_environment_interactions"] != expected_environment_steps:
            raise StatisticsGateV1Error("training interaction budget changed")
        try:
            ledger = SampleLedgerV1.from_document(artifact["sample_ledger"])
        except SampleLedgerV1Error as error:
            raise StatisticsGateV1Error("sample ledger is invalid") from error
        training_interactions = ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        )
        if training_interactions != expected_environment_steps:
            raise StatisticsGateV1Error(
                "training ENVIRONMENT_INTERACTION ledger count changed"
            )
        gradient_updates = ledger.to_document()["diagnostic_counters"][
            "gradient_updates"
        ]
        if gradient_updates != expected_updates:
            raise StatisticsGateV1Error("gradient update count changed")
        artifact_scores, episode_decision_count = _artifact_scores_v1(
            artifact,
            expected_checkpoints=expected_checkpoints,
            expected_evaluation_episodes=expected_evaluation_episodes,
        )
        _validate_telemetry_v1(
            artifact, arm=arm, expected_updates=expected_updates
        )
        execution_id, execution_environment = _validate_execution_context_v1(
            artifact, expected_source_commit=registered["source_commit"]
        )
        if execution_id in execution_ids:
            raise StatisticsGateV1Error("duplicate execution identity supplied")
        execution_ids.add(execution_id)
        execution_environments.add(execution_environment)
        evaluation_decisions = artifact["decision_latency_telemetry"][
            "decision_count"
        ]
        if evaluation_decisions != episode_decision_count:
            raise StatisticsGateV1Error(
                "decision latency count does not replay from episode outcomes"
            )
        if ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION,
            EvidenceLane.STANDALONE_EVALUATION,
        ) != evaluation_decisions:
            raise StatisticsGateV1Error(
                "standalone evaluation interaction ledger count changed"
            )
        if ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        ) != 2 * expected_environment_steps:
            raise StatisticsGateV1Error(
                "shared training action-mask query ledger count changed"
            )
        if ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY,
            EvidenceLane.STANDALONE_EVALUATION,
        ) != evaluation_decisions:
            raise StatisticsGateV1Error(
                "standalone evaluation action-mask query ledger count changed"
            )
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
            raise StatisticsGateV1Error("unregistered evidence authority was used")
        gradient_updates_by_arm[arm].append(gradient_updates)
        for checkpoint, score in artifact_scores.items():
            scores[arm][checkpoint][seed] = score

    missing_identities = expected_identities - identities
    if missing_identities:
        return _not_run_v1(
            protocol_id=protocol_id,
            reasons=["registered seed-arm identities are incomplete"],
            artifact_count=len(seed_arm_artifacts),
        )
    if any(
        tuple(counts) != (expected_updates,) * len(expected_seeds)
        for counts in gradient_updates_by_arm.values()
    ):
        raise StatisticsGateV1Error("gradient update counts are not matched")
    if len(execution_ids) != len(expected_identities):
        raise StatisticsGateV1Error("execution identities are incomplete")
    if len(execution_environments) != 1:
        raise StatisticsGateV1Error("confirmatory execution environments changed")

    ordered_scores = {
        arm: {
            checkpoint: tuple(
                scores[arm][checkpoint][seed] for seed in expected_seeds
            )
            for checkpoint in expected_checkpoints
        }
        for arm in expected_arms
    }
    reference_arm = registered["reference_arm"]
    candidate_arm = registered["candidate_arm"]
    reference_means = {
        checkpoint: float(mean_sem_v1(ordered_scores[reference_arm][checkpoint])["mean"])
        for checkpoint in expected_checkpoints
    }
    candidate_means = {
        checkpoint: float(mean_sem_v1(ordered_scores[candidate_arm][checkpoint])["mean"])
        for checkpoint in expected_checkpoints
    }
    final_step = expected_checkpoints[-1]
    reference_final = ordered_scores[reference_arm][final_step]
    candidate_final = ordered_scores[candidate_arm][final_step]
    threshold = reference_means[final_step] * 0.99
    reference_earliest = earliest_threshold_v1(reference_means, threshold)
    candidate_earliest = earliest_threshold_v1(candidate_means, threshold)
    welch = _welch_v1(candidate_final, reference_final)
    sample_tax_lower = (
        reference_earliest is not None
        and candidate_earliest is not None
        and candidate_earliest < reference_earliest
    )
    outcome_better = (
        welch["candidate_minus_baseline_mean"] > 0
        and welch["two_sided_p_value"] < 0.05
        and welch["difference_ci95_lower"] > 0
    )
    passed = sample_tax_lower and outcome_better
    ablation_arms = registered["ablation_arms"]
    return {
        "schema": "acfqp.science.latent_resource_confirmatory_joint_gate.v1",
        "protocol_id": protocol_id,
        "artifact_count": len(seed_arm_artifacts),
        "evidence_complete": True,
        "seed_count_per_arm": len(expected_seeds),
        "registered_unique_seeds": list(expected_seeds),
        "arms_executed": list(expected_arms),
        "reference_arm": reference_arm,
        "candidate_arm": candidate_arm,
        "ablation_arms": list(ablation_arms),
        "ablation_arms_executed": all(
            all((arm, seed) in identities for seed in expected_seeds)
            for arm in ablation_arms
        ),
        "checkpoints": list(expected_checkpoints),
        "training_environment_interactions_per_seed_arm": expected_environment_steps,
        "source_commit": registered["source_commit"],
        "execution_identity_count": len(execution_ids),
        "matched_execution_environment": True,
        "reference_checkpoint_means": reference_means,
        "candidate_checkpoint_means": candidate_means,
        "reference_final_summary": mean_sem_v1(reference_final),
        "candidate_final_summary": mean_sem_v1(candidate_final),
        "reference_final_99_percent_threshold": threshold,
        "reference_earliest_threshold_interactions": reference_earliest,
        "candidate_earliest_threshold_interactions": candidate_earliest,
        "sample_tax_strictly_lower": sample_tax_lower,
        "welch_two_sided": welch,
        "candidate_final_outcome_significantly_better": outcome_better,
        "network_parameter_count": NETWORK_PARAMETER_COUNT_V1,
        "gradient_updates_per_seed_arm": expected_updates,
        "network_parameter_count_equal": True,
        "gradient_update_schedule_equal": True,
        "training_environment_interaction_ledgers_validated": True,
        "latency_compute_and_compression_telemetry_present_for_every_artifact": True,
        "JOINT_SCIENTIFIC_SUCCESS_GATE": "PASS" if passed else "FAIL",
        "scientific_success_claimed": passed,
    }


__all__ = (
    "CONFIRMATORY_RESULT_SCHEMA_V1",
    "NETWORK_PARAMETER_COUNT_V1",
    "StatisticsGateV1Error",
    "earliest_threshold_v1",
    "evaluate_confirmatory_joint_gate_v1",
    "mean_sem_v1",
)
