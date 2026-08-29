from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.latent_resource_protocol_v1 import (
    PROTOCOL_DOMAIN,
    build_confirmatory_template_v1,
)
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
)
from acfqp.science.statistics_gate_v1 import (
    CONFIRMATORY_RESULT_SCHEMA_V1,
    NETWORK_PARAMETER_COUNT_V1,
    StatisticsGateV1Error,
    earliest_threshold_v1,
    evaluate_confirmatory_joint_gate_v1,
    mean_sem_v1,
)


def _ratified_protocol() -> dict:
    protocol = build_confirmatory_template_v1()
    protocol["campaign_kind"] = "CONFIRMATORY_RATIFIED"
    protocol["authorization"] = "RATIFIED_FOR_EXECUTION"
    protocol["confirmatory_protocol_ratified"] = True
    protocol["claim_boundary"]["official_execution_allowed"] = True
    protocol["source_commit"] = "1" * 40
    payload = dict(protocol)
    del payload["protocol_id"]
    protocol["protocol_id"] = hashlib.sha256(
        PROTOCOL_DOMAIN.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    return protocol


def _expected_updates(protocol: dict) -> int:
    training = protocol["training"]
    warmup = training["replay_warmup_environment_steps"]
    every = training["train_every_environment_steps"]
    final = training["environment_steps_per_seed_arm"]
    first = ((warmup + every - 1) // every) * every
    return ((final - first) // every) + 1


def _ledger(protocol: dict) -> dict:
    ledger = SampleLedgerV1()
    training_steps = protocol["training"]["environment_steps_per_seed_arm"]
    ledger.charge(
        EvidenceClass.ENVIRONMENT_INTERACTION,
        EvidenceLane.ONLINE_TARGET,
        training_steps,
    )
    ledger.charge(
        EvidenceClass.ENVIRONMENT_INTERACTION,
        EvidenceLane.STANDALONE_EVALUATION,
        1_000,
    )
    ledger.charge(
        EvidenceClass.EXACT_KERNEL_QUERY,
        EvidenceLane.ONLINE_TARGET,
        2 * training_steps,
    )
    ledger.charge(
        EvidenceClass.EXACT_KERNEL_QUERY,
        EvidenceLane.STANDALONE_EVALUATION,
        1_000,
    )
    ledger.increment_diagnostic("gradient_updates", _expected_updates(protocol))
    return ledger.to_document()


def _score(
    *, protocol: dict, arm: str, seed_index: int, checkpoint_index: int
) -> int:
    gate = protocol["joint_success_gate"]
    if arm == gate["reference_arm"]:
        bases = (100, 200, 300, 400, 500, 1_000)
    elif arm == gate["candidate_arm"]:
        bases = (200, 300, 400, 1_100, 1_200, 1_300)
    else:
        bases = (100, 200, 300, 400, 500, 600)
    return bases[checkpoint_index] + seed_index


def _artifact(protocol: dict, arm: str, seed: int) -> dict:
    seed_index = protocol["training_seeds"].index(seed)
    checkpoints = protocol["training"]["evaluation_checkpoints"]
    updates = _expected_updates(protocol)
    return {
        "schema": CONFIRMATORY_RESULT_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "arm": arm,
        "seed": seed,
        "network_parameter_count": NETWORK_PARAMETER_COUNT_V1,
        "training_environment_interactions": 500_000,
        "evaluations": [
            {
                "checkpoint_environment_interactions": checkpoint,
                "episode_count": 64,
                "mean_total_merge_score": _score(
                    protocol=protocol,
                    arm=arm,
                    seed_index=seed_index,
                    checkpoint_index=checkpoint_index,
                ),
                "episodes": [
                    {
                        "episode_index": episode_index,
                        "total_merge_score": _score(
                            protocol=protocol,
                            arm=arm,
                            seed_index=seed_index,
                            checkpoint_index=checkpoint_index,
                        ),
                        "decision_count": (
                            3
                            if checkpoint_index * 64 + episode_index < 232
                            else 2
                        ),
                    }
                    for episode_index in range(64)
                ],
            }
            for checkpoint_index, checkpoint in enumerate(checkpoints)
        ],
        "sample_ledger": _ledger(protocol),
        "decision_latency_telemetry": {
            "decision_count": 1_000,
            "total_decision_latency_ns": 10_000_000,
        },
        "compute_telemetry": {
            "wall_time_ns": 20_000_000,
            "gradient_updates": updates,
            "replay_buffer_draws": updates * 256,
            "peak_device_memory_bytes": 1_000_000,
        },
        "representation_telemetry": {
            "executed_arm": arm,
            "input_dimension": 16,
            "raw_observation_bytes": 64,
            "arm_observation_bytes": 64,
        },
        "execution_context": {
            "execution_id": f"confirmatory:{arm}:{seed}",
            "source_commit": protocol.get("source_commit", "0" * 40),
            "hostname": "jtl110gpu2",
            "python_version": "3.12.3",
            "numpy_version": "2.2.6",
            "torch_version": "2.7.0+cu118",
            "torch_cuda_runtime_version": "11.8",
            "torch_cudnn_version": 90100,
            "cuda_device_name": "NVIDIA GPU",
        },
    }


def _complete_matrix(protocol: dict) -> list[dict]:
    return [
        _artifact(protocol, arm, seed)
        for arm in protocol["arms"]
        for seed in protocol["training_seeds"]
    ]


def test_mean_sem_and_earliest_threshold() -> None:
    summary = mean_sem_v1([1.0, 2.0, 3.0, 4.0])
    assert summary["mean"] == 2.5
    assert summary["sem"] == pytest.approx(0.6454972244)
    assert earliest_threshold_v1({100: 1.0, 200: 2.5, 300: 3.0}, 2.0) == 200
    assert earliest_threshold_v1({100: 1.0}, 2.0) is None


def test_mean_sem_rejects_single_seed() -> None:
    with pytest.raises(StatisticsGateV1Error):
        mean_sem_v1([1.0])


def test_incomplete_seed_arm_matrix_is_not_run() -> None:
    protocol = _ratified_protocol()
    artifacts = _complete_matrix(protocol)[:-1]
    result = evaluate_confirmatory_joint_gate_v1(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    assert result["evidence_complete"] is False
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"
    assert result["scientific_success_claimed"] is False


def test_missing_ablation_arm_is_not_run() -> None:
    protocol = _ratified_protocol()
    reference = protocol["joint_success_gate"]["reference_arm"]
    candidate = protocol["joint_success_gate"]["candidate_arm"]
    artifacts = [
        artifact
        for artifact in _complete_matrix(protocol)
        if artifact["arm"] in (reference, candidate)
    ]
    result = evaluate_confirmatory_joint_gate_v1(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"
    assert "missing arms" in " ".join(result["not_run_reasons"])


def test_unratified_template_cannot_pass_with_fabricated_complete_artifacts() -> None:
    protocol = build_confirmatory_template_v1()
    result = evaluate_confirmatory_joint_gate_v1(
        protocol=protocol,
        seed_arm_artifacts=_complete_matrix(protocol),
    )
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"
    assert result["scientific_success_claimed"] is False
    assert "not ratified" in " ".join(result["not_run_reasons"])


def test_complete_identity_bound_matrix_can_pass() -> None:
    pytest.importorskip("scipy")
    protocol = _ratified_protocol()
    result = evaluate_confirmatory_joint_gate_v1(
        protocol=protocol,
        seed_arm_artifacts=_complete_matrix(protocol),
    )
    assert result["protocol_id"] == protocol["protocol_id"]
    assert result["artifact_count"] == 40
    assert result["seed_count_per_arm"] == 10
    assert result["checkpoints"] == [
        25_000,
        50_000,
        100_000,
        200_000,
        350_000,
        500_000,
    ]
    assert result["sample_tax_strictly_lower"] is True
    assert result["candidate_final_outcome_significantly_better"] is True
    assert result["ablation_arms_executed"] is True
    assert result["training_environment_interaction_ledgers_validated"] is True
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "PASS"


def test_protocol_identity_must_be_replayable() -> None:
    protocol = _ratified_protocol()
    protocol["training_seeds"][0] += 1
    with pytest.raises(StatisticsGateV1Error, match="identity is not replayable"):
        evaluate_confirmatory_joint_gate_v1(
            protocol=protocol, seed_arm_artifacts=[]
        )


def test_artifact_protocol_id_mismatch_is_rejected() -> None:
    protocol = _ratified_protocol()
    artifacts = _complete_matrix(protocol)
    artifacts[0]["protocol_id"] = "0" * 64
    with pytest.raises(StatisticsGateV1Error, match="foreign seed-arm"):
        evaluate_confirmatory_joint_gate_v1(
            protocol=protocol, seed_arm_artifacts=artifacts
        )


def test_duplicate_identity_is_rejected() -> None:
    protocol = _ratified_protocol()
    artifacts = _complete_matrix(protocol)
    artifacts[-1] = deepcopy(artifacts[0])
    with pytest.raises(StatisticsGateV1Error, match="duplicate seed-arm"):
        evaluate_confirmatory_joint_gate_v1(
            protocol=protocol, seed_arm_artifacts=artifacts
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda artifact: artifact.__setitem__("network_parameter_count", 1),
            "parameter count",
        ),
        (
            lambda artifact: artifact["sample_ledger"]["evidence_rows"][5].__setitem__(
                "count", 499_999
            ),
            "ENVIRONMENT_INTERACTION ledger count",
        ),
        (
            lambda artifact: artifact["sample_ledger"]["diagnostic_counters"].__setitem__(
                "gradient_updates", 1
            ),
            "gradient update count",
        ),
        (
            lambda artifact: artifact["evaluations"].pop(),
            "six registered checkpoints",
        ),
        (
            lambda artifact: artifact["representation_telemetry"].__setitem__(
                "executed_arm", "NOT_THE_ARTIFACT_ARM"
            ),
            "compression telemetry changed",
        ),
        (
            lambda artifact: artifact["evaluations"][0].__setitem__(
                "mean_total_merge_score",
                artifact["evaluations"][0]["mean_total_merge_score"] + 1,
            ),
            "does not replay from episode outcomes",
        ),
        (
            lambda artifact: artifact["execution_context"].__setitem__(
                "source_commit", "2" * 40
            ),
            "execution context changed",
        ),
        (
            lambda artifact: artifact["evaluations"][0]["episodes"][0].__setitem__(
                "decision_count", 1
            ),
            "decision latency count does not replay",
        ),
    ],
)
def test_contradictory_evidence_is_rejected(mutation, message: str) -> None:
    protocol = _ratified_protocol()
    artifacts = _complete_matrix(protocol)
    mutation(artifacts[0])
    with pytest.raises(StatisticsGateV1Error, match=message):
        evaluate_confirmatory_joint_gate_v1(
            protocol=protocol, seed_arm_artifacts=artifacts
        )


def test_missing_telemetry_is_not_run_not_pass() -> None:
    protocol = _ratified_protocol()
    artifacts = _complete_matrix(protocol)
    del artifacts[0]["decision_latency_telemetry"]
    result = evaluate_confirmatory_joint_gate_v1(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"
    assert result["scientific_success_claimed"] is False
