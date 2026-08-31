from __future__ import annotations

from copy import deepcopy
import json

import numpy as np
import pytest

from acfqp.science import decision_point_signature_evaluator_v2 as evaluator
from acfqp.science import decision_point_signature_protocol_v2 as protocol_subject
from acfqp.science.decision_point_signature_2048_pilot_v2 import (
    AUGMENTED_PREFIX_DIMENSION_V2,
    DECISION_PREFIX_ACTION_COUNT_V2,
    DECISION_STATE_COUNT_V2,
    RAW_PREFIX_ARM_V2,
    RAW_PREFIX_DIMENSION_V2,
    ROTATED_PREFIX_ARM_V2,
    STRATEGIC_PREFIX_ARM_V2,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
)


SOURCE_COMMIT = "3" * 40


def _parent_documents() -> tuple[dict, dict]:
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
                    "execution_id": f"u005:{arm}:{seed}",
                    "worker": (
                        seed - HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2[0]
                    )
                    % 2,
                    "device": registered_hybrid_confirmatory_device_v2(seed),
                }
            )
    return parent, {
        "schema": (
            "acfqp.science.latent_resource_hybrid_confirmatory_launch_manifest.v2"
        ),
        "protocol_id": parent["protocol_id"],
        "source_commit": parent["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }


def _prior_result() -> dict:
    labels = []
    for index, seed in enumerate(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2):
        labels.append(
            {
                "seed": seed,
                "mean_label_score": float(1_000 + index),
                "label": (
                    "NOVICE"
                    if index < 8
                    else "EXPERT"
                    if index >= 16
                    else "EXCLUDED_MIDDLE"
                ),
            }
        )
    return {
        "schema": protocol_subject.PRIOR_RESULT_SCHEMA_V2,
        "protocol_id": protocol_subject.PRIOR_PROTOCOL_ID_V2,
        "source_commit": protocol_subject.PRIOR_SOURCE_COMMIT_V2,
        "pilot_execution_identity": protocol_subject.PRIOR_EXECUTION_IDENTITY_V2,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL",
        "provisional_design_signal": "FAIL",
        "scientific_success": False,
        "scientific_success_claimed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "policy_labels": labels,
    }


@pytest.fixture(scope="module")
def protocol() -> dict:
    parent, manifest = _parent_documents()
    return protocol_subject.build_decision_point_protocol_v2(
        parent, manifest, _prior_result(), SOURCE_COMMIT
    )


def _collector(protocol: dict, policy_index: int) -> dict:
    raw = [[0.0] * RAW_PREFIX_DIMENSION_V2 for _ in range(64)]
    rotated = [[0.0] * AUGMENTED_PREFIX_DIMENSION_V2 for _ in range(64)]
    strategic = [
        [0.0] * RAW_PREFIX_DIMENSION_V2
        + [float(policy_index)]
        + [0.0]
        * (AUGMENTED_PREFIX_DIMENSION_V2 - RAW_PREFIX_DIMENSION_V2 - 1)
        for _ in range(64)
    ]
    prefix_rows = []
    for state in protocol["decision_states"]:
        prefix_rows.append(
            {
                "state_index": state["state_index"],
                "generator_episode_index": state["generator_episode_index"],
                "generator_decision_index": state["generator_decision_index"],
                "action_indices": [0, 1, 2, 3, 0, 1, 2, 3],
                "merge_scores": [0] * DECISION_PREFIX_ACTION_COUNT_V2,
                "tape_digests": ["a" * 64] * DECISION_PREFIX_ACTION_COUNT_V2,
                "final_status": "ACTIVE",
            }
        )
    return {
        "schema": evaluator.COLLECTOR_EVIDENCE_SCHEMA_V2,
        "state_library_tape_root": protocol["decision_state_library_contract"][
            "tape_root"
        ],
        "prefix_tape_root": protocol["prefix_tape_root"],
        "state_count": DECISION_STATE_COUNT_V2,
        "state_indices": list(range(DECISION_STATE_COUNT_V2)),
        "prefix_accepted_legal_action_count": DECISION_PREFIX_ACTION_COUNT_V2,
        "state_canonicalization_applied": False,
        "label_lane_present": False,
        "decision_state_rows": deepcopy(protocol["decision_states"]),
        "prefix_rows": prefix_rows,
        "prefix_feature_dimensions": {
            RAW_PREFIX_ARM_V2: RAW_PREFIX_DIMENSION_V2,
            ROTATED_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
            STRATEGIC_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
        },
        "prefix_matrices": {
            RAW_PREFIX_ARM_V2: raw,
            ROTATED_PREFIX_ARM_V2: rotated,
            STRATEGIC_PREFIX_ARM_V2: strategic,
        },
        "strategic_features_use_only_observed_prefix_and_pre_spawn_swipes": True,
        "independent_state_generation_and_policy_execution": True,
    }


def _worker_documents(protocol: dict) -> list[dict]:
    documents = []
    for worker in (0, 1):
        rows = []
        for candidate in protocol["candidate_models"]:
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
                "schema": evaluator.WORKER_EVIDENCE_SCHEMA_V2,
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
                    "python_version": "3.12.3",
                    "numpy_version": "2.2.6",
                    "scipy_version": "1.15.3",
                    "torch_version": "2.7.0+cu118",
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


def test_tie_safe_metrics_and_fold_weighting_are_exact() -> None:
    assert evaluator.tie_safe_auroc_v2([0, 0, 1, 1], [0.5] * 4) == 0.5
    assert evaluator.tie_safe_auroc_v2([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert evaluator.brier_score_v2([0, 1], [0.0, 1.0]) == 0.0
    features = np.zeros((15 * 64, 1), dtype=np.float64)
    labels = np.concatenate(
        (np.zeros(7 * 64, dtype=np.int64), np.ones(8 * 64, dtype=np.int64))
    )
    probabilities = evaluator._fit_fold_probabilities(  # noqa: SLF001
        features, labels, np.zeros((64, 1), dtype=np.float64)
    )
    assert np.all(probabilities == 0.5)


def test_full_grouped_evaluation_closes_only_provisional_signal(
    protocol: dict,
) -> None:
    result = evaluator.evaluate_decision_point_pilot_v2(
        protocol, _worker_documents(protocol)
    )

    json.dumps(result, allow_nan=False, sort_keys=True)
    assert result["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "PASS"
    assert result["metrics"]["raw"]["auroc"] == 0.5
    assert result["metrics"]["raw_plus_rotated_redundancy"]["auroc"] == 0.5
    assert result["metrics"]["raw_plus_strategic"]["auroc"] == 1.0
    assert result["bootstrap"] == {
        "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
        "replicates": 2_000,
        "random_seed": protocol_subject.BOOTSTRAP_RANDOM_SEED_V2,
        "confidence_interval": "PERCENTILE_95",
    }
    assert len(result["leave_one_policy_out_predictions"]) == 16
    assert result["scientific_success"] is False
    assert result["scientific_success_claimed"] is False
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert result["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert result["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert result["official_execution_allowed"] is False


def test_evaluator_rejects_runtime_and_collector_schema_drift(
    protocol: dict,
) -> None:
    workers = _worker_documents(protocol)
    workers[1]["runtime_context"]["torch_version"] = np.str_("2.7.0+cu118")
    with pytest.raises(
        evaluator.DecisionPointSignatureEvaluatorV2Error,
        match="runtime",
    ):
        evaluator.evaluate_decision_point_pilot_v2(protocol, workers)

    workers = _worker_documents(protocol)
    del workers[0]["policy_evidence"][0]["collector"]["prefix_rows"][0][
        "generator_decision_index"
    ]
    with pytest.raises(
        evaluator.DecisionPointSignatureEvaluatorV2Error,
        match="prefix_rows",
    ):
        evaluator.evaluate_decision_point_pilot_v2(protocol, workers)
