#!/usr/bin/env python3
"""Validate and summarize the complete nonconfirmatory 2048 pilot."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
from statistics import fmean
import sys

from acfqp.science.latent_resource_protocol_v1 import build_pilot_protocol_v1
from acfqp.science.matched_double_dqn_2048_v1 import NETWORK_PARAMETER_COUNT_V1
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_result(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if type(document) is not dict:
        raise ValueError(f"pilot result is not an object: {path}")
    return document


def summarize_pilot_v1(results: list[dict]) -> dict:
    protocol = build_pilot_protocol_v1()
    expected = {
        (arm, seed)
        for arm in protocol["arms"]
        for seed in protocol["training_seeds"]
    }
    if len(results) != len(expected):
        raise ValueError(f"pilot requires exactly {len(expected)} result artifacts")
    checkpoints = tuple(protocol["training"]["evaluation_checkpoints"])
    expected_steps = protocol["training"]["environment_steps_per_seed_arm"]
    expected_episodes = protocol["training"]["evaluation_episodes_per_checkpoint"]
    training = protocol["training"]
    first_update = (
        (
            training["replay_warmup_environment_steps"]
            + training["train_every_environment_steps"]
            - 1
        )
        // training["train_every_environment_steps"]
    ) * training["train_every_environment_steps"]
    expected_updates = (
        (expected_steps - first_update)
        // training["train_every_environment_steps"]
        + 1
    )
    seen: set[tuple[str, int]] = set()
    scores: dict[str, dict[int, list[float]]] = {
        arm: {checkpoint: [] for checkpoint in checkpoints}
        for arm in protocol["arms"]
    }
    compute_rows: dict[str, list[dict]] = {arm: [] for arm in protocol["arms"]}
    execution_rows: list[dict] = []
    for result in results:
        identity = (result.get("arm"), result.get("seed"))
        if identity not in expected or identity in seen:
            raise ValueError("pilot contains a foreign or duplicate seed-arm identity")
        seen.add(identity)
        arm, seed = identity
        if (
            result.get("schema")
            != "acfqp.science.matched_double_dqn_2048_pilot_result.v1"
            or result.get("protocol_id") != protocol["protocol_id"]
            or result.get("campaign_kind") != "PILOT_NONCONFIRMATORY"
            or result.get("network_parameter_count") != NETWORK_PARAMETER_COUNT_V1
            or result.get("training_environment_interactions") != expected_steps
            or result.get("pilot_scientific_gate") != "NOT_RUN"
            or result.get("scientific_success_claimed") is not False
        ):
            raise ValueError("pilot result contract changed")
        ledger = SampleLedgerV1.from_document(result["sample_ledger"])
        if ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        ) != expected_steps:
            raise ValueError("pilot training interaction ledger changed")
        if ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        ) != 2 * expected_steps:
            raise ValueError("pilot shared action-mask query ledger changed")
        if any(
            ledger.evidence_count(EvidenceClass.EXACT_KERNEL_QUERY, lane) != 0
            for lane in (EvidenceLane.OFFLINE_SOURCE, EvidenceLane.OPERATIONAL_QUERY)
        ):
            raise ValueError("pilot used an unregistered exact-query lane")
        evaluations = result.get("evaluations")
        if type(evaluations) is not list or len(evaluations) != len(checkpoints):
            raise ValueError("pilot checkpoint evidence is incomplete")
        by_checkpoint = {
            row.get("checkpoint_environment_interactions"): row
            for row in evaluations
            if type(row) is dict
        }
        if tuple(sorted(by_checkpoint)) != checkpoints:
            raise ValueError("pilot checkpoint identities changed")
        evaluation_decision_count = 0
        evaluation_decision_total_ns = 0
        for checkpoint in checkpoints:
            row = by_checkpoint[checkpoint]
            score = row.get("mean_total_merge_score")
            episodes = row.get("episodes")
            if row.get("episode_count") != expected_episodes or type(score) not in (
                int,
                float,
            ) or type(episodes) is not list or len(episodes) != expected_episodes:
                raise ValueError("pilot checkpoint outcome changed shape")
            episode_scores = []
            episode_indices: set[int] = set()
            checkpoint_decisions = 0
            for episode in episodes:
                if (
                    type(episode) is not dict
                    or type(episode.get("episode_index")) is not int
                    or episode["episode_index"] in episode_indices
                    or type(episode.get("total_merge_score")) is not int
                    or episode["total_merge_score"] < 0
                    or type(episode.get("decision_count")) is not int
                    or episode["decision_count"] <= 0
                    or type(episode.get("maximum_tile_rank")) is not int
                    or episode["maximum_tile_rank"] <= 0
                    or type(episode.get("won")) is not bool
                ):
                    raise ValueError("pilot episode outcome changed shape")
                episode_indices.add(episode["episode_index"])
                episode_scores.append(episode["total_merge_score"])
                checkpoint_decisions += episode["decision_count"]
            if episode_indices != set(range(expected_episodes)):
                raise ValueError("pilot evaluation episode identities changed")
            if not math.isclose(
                float(score), fmean(episode_scores), rel_tol=0.0, abs_tol=0.0
            ):
                raise ValueError("pilot checkpoint mean does not replay from episodes")
            checkpoint_compute = row.get("compute_telemetry")
            if (
                type(checkpoint_compute) is not dict
                or checkpoint_compute.get("decision_encoding_calls")
                != checkpoint_decisions
                or checkpoint_compute.get("policy_forward_calls")
                != checkpoint_decisions
                or type(checkpoint_compute.get("wall_time_ns")) is not int
                or checkpoint_compute["wall_time_ns"] <= 0
                or type(checkpoint_compute.get("decision_total_ns")) is not int
                or checkpoint_compute["decision_total_ns"] <= 0
                or type(checkpoint_compute.get("decision_encoding_total_ns"))
                is not int
                or checkpoint_compute["decision_encoding_total_ns"] <= 0
                or type(checkpoint_compute.get("policy_forward_total_ns")) is not int
                or checkpoint_compute["policy_forward_total_ns"] <= 0
            ):
                raise ValueError("pilot checkpoint compute telemetry changed")
            evaluation_decision_count += checkpoint_decisions
            evaluation_decision_total_ns += checkpoint_compute["decision_total_ns"]
            scores[arm][checkpoint].append(float(score))
        compute = result.get("compute_telemetry")
        context = result.get("execution_context")
        if type(compute) is not dict or type(context) is not dict:
            raise ValueError("pilot compute or execution context is absent")
        latency = result.get("decision_latency_telemetry")
        representation = result.get("representation_telemetry")
        if (
            type(latency) is not dict
            or latency.get("lane") != EvidenceLane.STANDALONE_EVALUATION.value
            or latency.get("decision_count") != evaluation_decision_count
            or latency.get("total_decision_latency_ns")
            != evaluation_decision_total_ns
            or latency.get(
                "includes_state_only_encoding_action_mask_and_policy_forward"
            )
            is not True
            or not math.isclose(
                latency.get("mean_decision_latency_ns", -1),
                evaluation_decision_total_ns / evaluation_decision_count,
                rel_tol=0.0,
                abs_tol=0.0,
            )
        ):
            raise ValueError("pilot decision latency telemetry changed")
        required_compute = {
            "wall_time_ns",
            "total_wall_time_ns",
            "training_wall_time_excluding_standalone_evaluation_ns",
            "standalone_evaluation_wall_time_ns",
            "training_decision_encoding_calls",
            "training_decision_encoding_total_ns",
            "training_decision_encoding_mean_ns",
            "replay_next_encoding_calls",
            "replay_next_encoding_total_ns",
            "replay_next_encoding_mean_ns",
            "training_policy_forward_calls",
            "optimizer_update_calls",
            "gradient_updates",
            "replay_buffer_draws",
            "optimizer_network_forward_passes",
            "optimizer_update_total_ns",
            "optimizer_update_mean_ns",
            "peak_device_memory_bytes",
            "device_latency_measured_with_synchronization",
        }
        if not required_compute <= set(compute):
            raise ValueError("pilot compute telemetry is incomplete")
        if (
            type(compute["total_wall_time_ns"]) is not int
            or compute["total_wall_time_ns"] <= 0
            or compute["wall_time_ns"] != compute["total_wall_time_ns"]
            or type(
                compute["training_wall_time_excluding_standalone_evaluation_ns"]
            )
            is not int
            or compute["training_wall_time_excluding_standalone_evaluation_ns"]
            <= 0
            or compute["standalone_evaluation_wall_time_ns"]
            != sum(
                row["compute_telemetry"]["wall_time_ns"] for row in evaluations
            )
            or compute["total_wall_time_ns"]
            != compute["training_wall_time_excluding_standalone_evaluation_ns"]
            + compute["standalone_evaluation_wall_time_ns"]
            or compute["training_decision_encoding_calls"] != expected_steps
            or compute["replay_next_encoding_calls"] != expected_steps
            or compute["optimizer_update_calls"] != expected_updates
            or compute["gradient_updates"] != expected_updates
            or compute["replay_buffer_draws"]
            != expected_updates * training["batch_size"]
            or compute["optimizer_network_forward_passes"] != expected_updates * 3
            or type(compute["training_policy_forward_calls"]) is not int
            or not 0 <= compute["training_policy_forward_calls"] <= expected_steps
            or type(compute["peak_device_memory_bytes"]) is not int
            or compute["peak_device_memory_bytes"] <= 0
            or compute["device_latency_measured_with_synchronization"] is not True
        ):
            raise ValueError("pilot compute telemetry changed")
        for calls_name, total_name, mean_name in (
            (
                "training_decision_encoding_calls",
                "training_decision_encoding_total_ns",
                "training_decision_encoding_mean_ns",
            ),
            (
                "replay_next_encoding_calls",
                "replay_next_encoding_total_ns",
                "replay_next_encoding_mean_ns",
            ),
            (
                "optimizer_update_calls",
                "optimizer_update_total_ns",
                "optimizer_update_mean_ns",
            ),
        ):
            if (
                type(compute[total_name]) is not int
                or compute[total_name] <= 0
                or not math.isclose(
                    compute[mean_name],
                    compute[total_name] / compute[calls_name],
                    rel_tol=0.0,
                    abs_tol=0.0,
                )
            ):
                raise ValueError("pilot compute mean does not replay from totals")
        if (
            type(representation) is not dict
            or representation.get("active_representation") != arm
            or representation.get("executed_arm") != arm
            or representation.get("input_dimension") != 16
            or representation.get("raw_observation_bytes") != 64
            or representation.get("arm_observation_bytes") != 64
            or representation.get("resource_quantization_bins_per_coordinate") != 256
            or representation.get("equal_dimension_is_not_counted_as_compression")
            is not True
            or representation.get("compression_claimed") is not False
        ):
            raise ValueError("pilot representation telemetry changed")
        raw_signatures = representation.get("lossless_raw_board_signature_count")
        resource_signatures = representation.get(
            "quantized_state_only_resource_signature_count"
        )
        if (
            type(raw_signatures) is not int
            or type(resource_signatures) is not int
            or (
                arm == "RAW_BOARD"
                and not (raw_signatures > 0 and resource_signatures == 0)
            )
            or (
                arm == "RESOURCE_STATE_ONLY"
                and not (resource_signatures > 0 and raw_signatures == 0)
            )
        ):
            raise ValueError("pilot representation signatures changed")
        allowed_evidence = {
            (
                EvidenceClass.ENVIRONMENT_INTERACTION,
                EvidenceLane.ONLINE_TARGET,
            ): expected_steps,
            (
                EvidenceClass.ENVIRONMENT_INTERACTION,
                EvidenceLane.STANDALONE_EVALUATION,
            ): evaluation_decision_count,
            (
                EvidenceClass.EXACT_KERNEL_QUERY,
                EvidenceLane.ONLINE_TARGET,
            ): 2 * expected_steps,
            (
                EvidenceClass.EXACT_KERNEL_QUERY,
                EvidenceLane.STANDALONE_EVALUATION,
            ): evaluation_decision_count,
        }
        if any(
            ledger.evidence_count(evidence_class, lane)
            != allowed_evidence.get((evidence_class, lane), 0)
            for evidence_class in EvidenceClass
            for lane in EvidenceLane
        ):
            raise ValueError("pilot sample authority ledger changed")
        diagnostics = ledger.to_document()["diagnostic_counters"]
        if (
            diagnostics["gradient_updates"] != expected_updates
            or diagnostics["replay_buffer_draws"]
            != expected_updates * training["batch_size"]
            or diagnostics["target_network_syncs"]
            != expected_steps // training["target_network_sync_environment_steps"]
            or diagnostics["evaluation_episodes"]
            != len(checkpoints) * expected_episodes
            or diagnostics["simulator_transition_calls"]
            != expected_steps + evaluation_decision_count
            or diagnostics["policy_forward_passes"]
            != compute["training_policy_forward_calls"] + evaluation_decision_count
            or diagnostics["training_episodes"] <= 0
        ):
            raise ValueError("pilot diagnostic compute ledger changed")
        required_context = {
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
        if (
            not required_context <= set(context)
            or type(context["execution_id"]) is not str
            or not context["execution_id"]
            or type(context["source_commit"]) is not str
            or re.fullmatch(r"[0-9a-f]{40}", context["source_commit"]) is None
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
            raise ValueError("pilot execution context changed shape")
        compute_rows[arm].append(compute)
        execution_rows.append(
            {
                "arm": arm,
                "seed": seed,
                "execution_id": context.get("execution_id"),
                "source_commit": context.get("source_commit"),
                "hostname": context.get("hostname"),
                "python_version": context.get("python_version"),
                "numpy_version": context.get("numpy_version"),
                "torch_version": context.get("torch_version"),
                "torch_cuda_runtime_version": context.get(
                    "torch_cuda_runtime_version"
                ),
                "torch_cudnn_version": context.get("torch_cudnn_version"),
                "cuda_device_name": context.get("cuda_device_name"),
            }
        )
    if seen != expected:
        raise ValueError("pilot seed-arm matrix is incomplete")
    source_commits = {row["source_commit"] for row in execution_rows}
    execution_ids = {row["execution_id"] for row in execution_rows}
    environments = {
        (
            row["hostname"],
            row["python_version"],
            row["numpy_version"],
            row["torch_version"],
            row["torch_cuda_runtime_version"],
            row["torch_cudnn_version"],
            row["cuda_device_name"],
        )
        for row in execution_rows
    }
    if len(source_commits) != 1 or len(execution_ids) != len(expected):
        raise ValueError("pilot source commit or execution identities are not matched")
    if len(environments) != 1:
        raise ValueError("pilot seed arms used different execution environments")
    checkpoint_means = {
        arm: {
            checkpoint: fmean(scores[arm][checkpoint]) for checkpoint in checkpoints
        }
        for arm in protocol["arms"]
    }
    reference = "RAW_BOARD"
    candidate = "RESOURCE_STATE_ONLY"
    threshold = 0.99 * checkpoint_means[reference][checkpoints[-1]]

    def earliest(arm: str) -> int | None:
        return next(
            (
                checkpoint
                for checkpoint in checkpoints
                if checkpoint_means[arm][checkpoint] >= threshold
            ),
            None,
        )

    compute_summary = {
        arm: {
            "mean_training_wall_time_excluding_evaluation_ns": fmean(
                row["training_wall_time_excluding_standalone_evaluation_ns"]
                for row in compute_rows[arm]
            ),
            "mean_training_decision_encoding_ns": fmean(
                row["training_decision_encoding_mean_ns"]
                for row in compute_rows[arm]
            ),
            "mean_peak_device_memory_bytes": fmean(
                row["peak_device_memory_bytes"] for row in compute_rows[arm]
            ),
        }
        for arm in protocol["arms"]
    }
    return {
        "schema": "acfqp.science.matched_double_dqn_2048_pilot_summary.v1",
        "protocol_id": protocol["protocol_id"],
        "campaign_kind": "PILOT_NONCONFIRMATORY",
        "artifact_count": len(results),
        "seed_arm_matrix_complete": True,
        "source_commit": next(iter(source_commits)),
        "execution_ids": sorted(execution_ids),
        "checkpoint_means": checkpoint_means,
        "raw_final_99_percent_threshold": threshold,
        "descriptive_reference_earliest_threshold_interactions": earliest(reference),
        "descriptive_candidate_earliest_threshold_interactions": earliest(candidate),
        "descriptive_candidate_minus_reference_final_mean": (
            checkpoint_means[candidate][checkpoints[-1]]
            - checkpoint_means[reference][checkpoints[-1]]
        ),
        "compute_summary": compute_summary,
        "execution_rows": sorted(execution_rows, key=lambda row: (row["arm"], row["seed"])),
        "shared_training_action_mask_exact_query_count_per_seed_arm": 2
        * expected_steps,
        "state_only_representation_extra_exact_model_query_count": 0,
        "pilot_scientific_gate": "NOT_RUN",
        "statistics_gate": "NOT_RUN_PILOT_TWO_SEEDS",
        "scientific_success_claimed": False,
    }


def main() -> int:
    args = _arguments()
    summary = summarize_pilot_v1([_load_result(path) for path in args.result])
    _write_exclusive(
        args.output,
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "success": True,
                "output": str(args.output),
                "pilot_scientific_gate": "NOT_RUN",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
