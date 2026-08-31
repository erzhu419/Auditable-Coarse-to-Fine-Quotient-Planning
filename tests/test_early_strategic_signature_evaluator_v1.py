from __future__ import annotations

from copy import deepcopy
import json

import numpy as np
import pytest

from acfqp.science import early_strategic_signature_evaluator_v1 as evaluator
from acfqp.science import early_strategic_signature_protocol_v1 as protocol_subject
from acfqp.science.early_strategic_signature_2048_pilot_v1 import (
    AUGMENTED_PREFIX_DIMENSION_V1,
    RAW_PREFIX_ARM_V1,
    RAW_PREFIX_DIMENSION_V1,
    ROTATED_PREFIX_ARM_V1,
    STRATEGIC_PREFIX_ARM_V1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
)


PILOT_SOURCE_COMMIT = "1" * 40


def _parent_protocol_and_manifest():
    parent = build_ratified_hybrid_confirmatory_protocol_v2(
        protocol_subject.PARENT_U005_SOURCE_COMMIT_V1
    )
    jobs = []
    for arm in HYBRID_CONFIRMATORY_ARMS_V2:
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2:
            jobs.append(
                {
                    "job_ordinal": len(jobs),
                    "arm": arm,
                    "seed": seed,
                    "execution_id": f"u005-{arm.lower()}-{seed}",
                    "worker": (seed - HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2[0]) % 2,
                    "device": registered_hybrid_confirmatory_device_v2(seed),
                }
            )
    manifest = {
        "schema": protocol_subject.PARENT_MANIFEST_SCHEMA_V1,
        "protocol_id": parent["protocol_id"],
        "source_commit": parent["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }
    return parent, manifest


def _pilot_protocol():
    parent, manifest = _parent_protocol_and_manifest()
    return protocol_subject.build_pilot_protocol_v1(
        parent, manifest, PILOT_SOURCE_COMMIT
    )


def _collector(protocol, policy_index: int):
    raw_matrix = [[0.0] * RAW_PREFIX_DIMENSION_V1 for _ in range(64)]
    rotated_matrix = [
        [0.0] * AUGMENTED_PREFIX_DIMENSION_V1 for _ in range(64)
    ]
    strategic_matrix = [
        [0.0] * RAW_PREFIX_DIMENSION_V1
        + [float(policy_index)]
        + [0.0] * (AUGMENTED_PREFIX_DIMENSION_V1 - RAW_PREFIX_DIMENSION_V1 - 1)
        for _ in range(64)
    ]
    return {
        "schema": evaluator.COLLECTOR_EVIDENCE_SCHEMA_V1,
        "label_tape_root": protocol["label_tape_root"],
        "prefix_tape_root": protocol["prefix_tape_root"],
        "independent_tape_roots": True,
        "episode_indices": list(range(64)),
        "prefix_accepted_legal_action_count": 8,
        "state_canonicalization_applied": False,
        "label_rows": [
            {
                "episode_index": episode,
                "total_merge_score": policy_index,
                "maximum_tile_rank": 10,
                "decision_count": 100,
                "terminal_status": "LOST",
                "won": False,
            }
            for episode in range(64)
        ],
        "prefix_rows": [
            {
                "episode_index": episode,
                "action_indices": [0, 1, 2, 3, 0, 1, 2, 3],
                "merge_scores": [0] * 8,
                "tape_digests": ["a" * 64] * 8,
                "final_status": "ACTIVE",
            }
            for episode in range(64)
        ],
        "prefix_feature_dimensions": {
            RAW_PREFIX_ARM_V1: RAW_PREFIX_DIMENSION_V1,
            ROTATED_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
            STRATEGIC_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
        },
        "prefix_matrices": {
            RAW_PREFIX_ARM_V1: raw_matrix,
            ROTATED_PREFIX_ARM_V1: rotated_matrix,
            STRATEGIC_PREFIX_ARM_V1: strategic_matrix,
        },
        "strategic_features_use_only_prefix_observations_and_pre_spawn_swipes": True,
    }


def _worker_documents(protocol):
    documents = []
    roster = protocol["candidate_models"]
    for worker in (0, 1):
        rows = []
        for candidate in roster:
            if candidate["worker"] != worker:
                continue
            policy_index = HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2.index(
                candidate["seed"]
            )
            rows.append(
                {
                    "seed": candidate["seed"],
                    "model_filename": candidate["model_filename"],
                    "parent_execution_id": candidate["parent_execution_id"],
                    "collector": _collector(protocol, policy_index),
                }
            )
        documents.append(
            {
                "schema": evaluator.WORKER_EVIDENCE_SCHEMA_V1,
                "protocol_id": protocol["protocol_id"],
                "source_commit": protocol["source_commit"],
                "pilot_execution_identity": protocol["pilot_execution_identity"],
                "worker": worker,
                "device": f"cuda:{worker}",
                "execution_id": (
                    f"{protocol['pilot_execution_identity']}:worker:{worker}"
                ),
                "runtime_context": {
                    "hostname": "pilot-host",
                    "python_version": "3.10.12",
                    "numpy_version": "2.2.6",
                    "scipy_version": "1.15.3",
                    "torch_version": "2.7.1+cu118",
                    "torch_cuda_runtime_version": "11.8",
                    "torch_cudnn_version": 90100,
                    "device": f"cuda:{worker}",
                    "cuda_device_name": f"synthetic-gpu-{worker}",
                },
                "policy_count": len(rows),
                "policy_evidence": rows,
                "scientific_success_claimed": False,
            }
        )
    return documents


def test_protocol_freezes_parent_roster_and_separate_pilot_commit() -> None:
    protocol = _pilot_protocol()

    assert (
        protocol["parent_u005_protocol_id"]
        == protocol_subject.PARENT_U005_PROTOCOL_ID_V1
    )
    assert (
        protocol["parent_u005_source_commit"]
        == protocol_subject.PARENT_U005_SOURCE_COMMIT_V1
    )
    assert protocol["source_commit"] == PILOT_SOURCE_COMMIT
    assert protocol["pilot_execution_identity"] == (
        "acfqp-early-strategic-signature-2048-pilot-v1-ordinal1-attempt1"
    )
    assert len(protocol["candidate_models"]) == 24
    assert protocol["label_episode_indices"] == list(range(64))
    assert protocol["prefix_episode_indices"] == list(range(64))
    assert protocol["prefix_action_count"] == 8
    for index, candidate in enumerate(protocol["candidate_models"]):
        assert candidate["worker"] == index % 2
        assert candidate["device"] == f"cuda:{index % 2}"
        assert "/" not in candidate["model_filename"]
    assert protocol["claim_boundary"]["feasibility_pilot_execution_authorized"] is True
    assert protocol["claim_boundary"]["confirmatory_execution_authorized"] is False
    assert protocol_subject.validate_pilot_protocol_v1(protocol) == protocol

    tampered = deepcopy(protocol)
    tampered["prefix_action_count"] = 7
    with pytest.raises(
        protocol_subject.EarlyStrategicSignatureProtocolV1Error,
        match="identity",
    ):
        protocol_subject.validate_pilot_protocol_v1(tampered)


def test_seed_tie_break_and_tie_safe_metrics_are_exact() -> None:
    seeds = list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)
    labels = evaluator.assign_policy_labels_v1({seed: 1.0 for seed in seeds})
    assert [seed for seed in seeds if labels[seed] == "NOVICE"] == seeds[:8]
    assert [seed for seed in seeds if labels[seed] == "EXCLUDED_MIDDLE"] == seeds[8:16]
    assert [seed for seed in seeds if labels[seed] == "EXPERT"] == seeds[16:]
    assert evaluator.tie_safe_auroc_v1([0, 0, 1, 1], [0.5] * 4) == 0.5
    assert evaluator.tie_safe_auroc_v1([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert evaluator.brier_score_v1([0, 1], [0.0, 1.0]) == 0.0


def test_fold_label_weighting_removes_fixed_composition_leakage() -> None:
    features = np.zeros((15 * 64, 1), dtype=np.float64)
    labels = np.concatenate(
        (
            np.zeros(7 * 64, dtype=np.int64),
            np.ones(8 * 64, dtype=np.int64),
        )
    )
    probabilities = evaluator._fit_fold_probabilities(  # noqa: SLF001
        features,
        labels,
        np.zeros((64, 1), dtype=np.float64),
    )
    assert np.all(probabilities == 0.5)


def test_full_grouped_evaluation_passes_only_the_provisional_signal() -> None:
    protocol = _pilot_protocol()
    result = evaluator.evaluate_pilot_v1(protocol, _worker_documents(protocol))

    json.dumps(result, allow_nan=False, sort_keys=True)
    assert result["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "PASS"
    assert result["metrics"]["raw"]["auroc"] == 0.5
    assert result["metrics"]["raw_plus_rotated_redundancy"]["auroc"] == 0.5
    assert result["metrics"]["raw_plus_strategic"]["auroc"] == 1.0
    assert result["bootstrap"] == {
        "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
        "replicates": 2_000,
        "random_seed": protocol_subject.BOOTSTRAP_RANDOM_SEED_V1,
        "confidence_interval": "PERCENTILE_95",
    }
    assert len(result["leave_one_policy_out_predictions"]) == 16
    assert all(
        len(row["probabilities"][arm]) == 64
        for row in result["leave_one_policy_out_predictions"]
        for arm in protocol_subject.PILOT_ARMS_V1
    )
    assert result["scientific_success"] is False
    assert result["scientific_success_claimed"] is False
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert result["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert result["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert result["official_execution_allowed"] is False


def test_evaluator_rejects_incomplete_prefix_evidence_before_modeling() -> None:
    protocol = _pilot_protocol()
    workers = _worker_documents(protocol)

    inconsistent_runtime = deepcopy(workers)
    inconsistent_runtime[1]["runtime_context"]["hostname"] = "other-host"
    with pytest.raises(
        evaluator.EarlyStrategicSignatureEvaluatorV1Error,
        match="runtime contexts differ",
    ):
        evaluator.evaluate_pilot_v1(protocol, inconsistent_runtime)

    workers[0]["policy_evidence"][0]["collector"]["prefix_rows"].pop()

    with pytest.raises(
        evaluator.EarlyStrategicSignatureEvaluatorV1Error,
        match="exact 64 prefixes",
    ):
        evaluator.evaluate_pilot_v1(protocol, workers)
