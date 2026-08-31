from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science import matched_double_dqn_2048_hybrid_confirmatory_v2 as runtime
from acfqp.science.hybrid_confirmatory_gate_v2 import (
    HybridConfirmatoryGateV2Error,
    evaluate_hybrid_confirmatory_joint_gate_v2,
)
from acfqp.science.hybrid_confirmatory_evaluator_v2 import (
    HYBRID_CONFIRMATORY_MANIFEST_SCHEMA_V2,
    HybridConfirmatoryEvaluatorV2Error,
    load_evidence_bound_hybrid_confirmatory_matrix_v2,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    HYBRID_PARAMETER_COUNT_V2,
    HYBRID_PILOT_PROTOCOL_ID_V2,
    RAW_STANDARD_ARM_V2,
    RAW_STANDARD_PARAMETER_COUNT_V2,
    RESOURCE_CANDIDATE_ARM_V2,
    ROTATED_CONTROL_ARM_V2,
    U003_PROTOCOL_ID_V2,
    U004_PROTOCOL_ID_V2,
    LatentResourceHybridConfirmatoryProtocolV2Error,
    build_hybrid_confirmatory_template_v2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
    validate_ratified_hybrid_confirmatory_protocol_v2,
)
from acfqp.science.latent_resource_hybrid_protocol_v1 import (
    build_hybrid_pilot_protocol_v1,
)
from acfqp.science.matched_2048_env_v1 import initial_state_v1
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v2 import (
    HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2,
    observation_vector_hybrid_confirmatory_v2,
    run_hybrid_confirmatory_seed_arm_v2,
)
from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _load_script(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / relative_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _protocol() -> dict:
    return build_ratified_hybrid_confirmatory_protocol_v2("1" * 40)


def _expected_updates() -> int:
    return ((100_000 - 10_000) // 4) + 1


def _score(arm: str, seed_index: int, checkpoint: int) -> int:
    if arm == RAW_STANDARD_ARM_V2:
        return {
            25_000: 400 + 4 * seed_index,
            50_000: 700 + 5 * seed_index,
            100_000: 1_000 + 10 * seed_index,
        }[checkpoint]
    if arm == ROTATED_CONTROL_ARM_V2:
        return {
            25_000: 500 + 3 * seed_index,
            50_000: 850 + 5 * seed_index,
            100_000: 1_120 + 7 * seed_index,
        }[checkpoint]
    return {
        25_000: 1_400 + 12 * seed_index,
        50_000: 1_200 + 8 * seed_index,
        100_000: 1_500 + 12 * seed_index,
    }[checkpoint]


def _ledger(evaluation_decisions: int) -> dict:
    ledger = SampleLedgerV1()
    ledger.charge(
        EvidenceClass.ENVIRONMENT_INTERACTION,
        EvidenceLane.ONLINE_TARGET,
        100_000,
    )
    ledger.charge(
        EvidenceClass.EXACT_KERNEL_QUERY,
        EvidenceLane.ONLINE_TARGET,
        200_000,
    )
    ledger.charge(
        EvidenceClass.ENVIRONMENT_INTERACTION,
        EvidenceLane.STANDALONE_EVALUATION,
        evaluation_decisions,
    )
    ledger.charge(
        EvidenceClass.EXACT_KERNEL_QUERY,
        EvidenceLane.STANDALONE_EVALUATION,
        evaluation_decisions,
    )
    ledger.increment_diagnostic("gradient_updates", _expected_updates())
    ledger.increment_diagnostic(
        "replay_buffer_draws", _expected_updates() * 256
    )
    return ledger.to_document()


def _artifact(protocol: dict, arm: str, seed: int) -> dict:
    seed_index = protocol["training_seeds"].index(seed)
    input_dimension = 16 if arm == RAW_STANDARD_ARM_V2 else 32
    parameter_count = (
        RAW_STANDARD_PARAMETER_COUNT_V2
        if arm == RAW_STANDARD_ARM_V2
        else HYBRID_PARAMETER_COUNT_V2
    )
    second_block = {
        RAW_STANDARD_ARM_V2: "NONE_RAW_STANDARD",
        ROTATED_CONTROL_ARM_V2: "FIXED_180_DEGREE_RAW_REDUNDANCY",
        RESOURCE_CANDIDATE_ARM_V2: "STATE_ONLY_LATENT_RESOURCE",
    }[arm]
    evaluations = []
    for checkpoint in (25_000, 50_000, 100_000):
        score = _score(arm, seed_index, checkpoint)
        evaluations.append(
            {
                "checkpoint_environment_interactions": checkpoint,
                "episode_count": 64,
                "mean_total_merge_score": score,
                "episodes": [
                    {
                        "episode_index": episode_index,
                        "total_merge_score": score,
                        "decision_count": 2,
                    }
                    for episode_index in range(64)
                ],
            }
        )
    evaluation_decisions = 3 * 64 * 2
    return {
        "schema": HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2,
        "protocol_id": protocol["protocol_id"],
        "device": registered_hybrid_confirmatory_device_v2(seed),
        "arm": arm,
        "seed": seed,
        "network_parameter_count": parameter_count,
        "training_environment_interactions": 100_000,
        "evaluations": evaluations,
        "sample_ledger": _ledger(evaluation_decisions),
        "decision_latency_telemetry": {
            "decision_count": evaluation_decisions,
            "total_decision_latency_ns": evaluation_decisions * 1_000,
        },
        "compute_telemetry": {
            "wall_time_ns": 10_000_000,
            "gradient_updates": _expected_updates(),
            "replay_buffer_draws": _expected_updates() * 256,
            "peak_device_memory_bytes": 1_000_000,
        },
        "representation_telemetry": {
            "executed_arm": arm,
            "input_dimension": input_dimension,
            "raw_observation_bytes": 64,
            "arm_observation_bytes": input_dimension * 4,
            "lossless_raw_board_retained": True,
            "second_block_kind": second_block,
            "second_block_calls_transition_or_successor_kernel": False,
            "control_second_block_is_bijective_redundancy": (
                arm == ROTATED_CONTROL_ARM_V2
            ),
            "candidate_second_block_is_human_inductive_bias": (
                arm == RESOURCE_CANDIDATE_ARM_V2
            ),
            "parameter_count_equal_to_rotated_control": (
                arm in (ROTATED_CONTROL_ARM_V2, RESOURCE_CANDIDATE_ARM_V2)
            ),
            "parameter_count_equal_to_raw_standard": arm == RAW_STANDARD_ARM_V2,
            "compression_claimed": False,
        },
        "tape_binding": {
            "training_tape_root": f"{protocol['training_tape_prefix']}:{seed}",
            "evaluation_tape_root": protocol["evaluation_tape_prefix"],
            "same_seed_training_tape_across_arms": True,
            "same_evaluation_tapes_across_all_seed_arms": True,
        },
        "execution_context": {
            "execution_id": f"hybrid-confirmatory:{arm}:{seed}",
            "source_commit": protocol["source_commit"],
            "hostname": "jtl110gpu2",
            "python_version": "3.12.3",
            "numpy_version": "2.2.6",
            "torch_version": "2.7.0+cu118",
            "torch_cuda_runtime_version": "11.8",
            "torch_cudnn_version": 90100,
            "cuda_device_name": "NVIDIA GPU",
        },
        "hybrid_confirmatory_joint_gate": (
            "NOT_RUN_REQUIRES_COMPLETE_72_ARTIFACT_MATRIX"
        ),
        "scientific_success_claimed": False,
    }


def _matrix(protocol: dict) -> list[dict]:
    return [
        _artifact(protocol, arm, seed)
        for arm in HYBRID_CONFIRMATORY_ARMS_V2
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2
    ]


def test_protocol_freezes_fresh_matrix_paired_gate_and_claim_boundary() -> None:
    template = build_hybrid_confirmatory_template_v2()
    training = template["training"]
    predecessor = template["predecessor_evidence_contract"]
    sample_size = template["sample_size_design_contract"]
    claims = template["claim_boundary"]

    assert template["arms"] == list(HYBRID_CONFIRMATORY_ARMS_V2)
    assert template["training_seeds"] == list(range(760101, 760125))
    assert training["environment_steps_per_seed_arm"] == 100_000
    assert training["evaluation_checkpoints"] == [25_000, 50_000, 100_000]
    assert training["evaluation_episodes_per_checkpoint"] == 64
    assert training["primary_gate_checkpoints"] == [25_000, 100_000]
    assert training["diagnostic_only_checkpoints"] == [50_000]
    assert training["checkpoint_50000_cannot_change_joint_gate"] is True
    assert training["epsilon_schedule"]["decay_steps"] == 100_000
    assert predecessor["u003_protocol_id"] == U003_PROTOCOL_ID_V2
    assert predecessor["u003_joint_gate"].startswith("FAIL_RETAINED")
    assert predecessor["hybrid_pilot_protocol_id"] == HYBRID_PILOT_PROTOCOL_ID_V2
    assert build_hybrid_pilot_protocol_v1()["protocol_id"] == (
        HYBRID_PILOT_PROTOCOL_ID_V2
    )
    assert predecessor["u004_protocol_id"] == U004_PROTOCOL_ID_V2
    assert predecessor["u004_joint_gate"].startswith("FAIL_RETAINED")
    assert predecessor["u004_25000_checkpoint_role"].startswith("DESIGN_ONLY")
    assert predecessor["u004_results_used_to_choose_u005_hypothesis"] is True
    assert predecessor["predecessor_seeds_or_outcomes_pooled"] is False
    assert sample_size["u004_observed_standardized_paired_effect_dz"] == (
        "1.051273"
    )
    assert sample_size["planning_standardized_paired_effect_dz"] == "0.525636"
    assert sample_size["training_seed_count"] == 24
    assert sample_size["approximate_bottleneck_marginal_power"] == "0.803255"
    assert sample_size["joint_intersection_union_power_guaranteed"] is False
    assert sample_size["u004_observations_enter_u005_tests"] is False
    assert sample_size["post_launch_sample_size_expansion_allowed"] is False
    assert sample_size[
        "result_contingent_checkpoint_or_seed_successor_allowed"
    ] is False
    assert sample_size[
        "future_same_hypothesis_successor_requires_pre_outcome_cross_"
        "successor_error_control"
    ] is True
    assert sample_size[
        "cross_successor_error_control_registered_by_this_protocol"
    ] is False
    assert template["joint_success_gate"]["all_four_tests_must_pass"] is True
    assert template["joint_success_gate"]["global_null"].startswith(
        "AT_LEAST_ONE"
    )
    assert template["joint_success_gate"]["global_alternative"].startswith(
        "ALL_FOUR"
    )
    assert template["joint_success_gate"][
        "candidate_25000_threshold_attainment_test"
    ]["per_seed_difference"].startswith("candidate_mean_score_at_25000")
    assert template["joint_success_gate"][
        "raw_early_threshold_nonattainment_test"
    ]["per_seed_difference"].endswith("raw_standard_mean_score_at_25000")
    assert template["joint_success_gate"][
        "checkpoint_50000_excluded_from_all_four_gate_components"
    ] is True
    assert template["joint_success_gate"]["multiple_testing_rule"] == (
        "INTERSECTION_UNION_NO_ALPHA_SPLIT"
    )
    assert template["statistics_gate"][
        "uncertainty_is_across_twenty_four_training_seeds"
    ] is True
    assert template["statistics_gate"][
        "evaluation_episodes_are_fixed_tape_measurements_not_statistical_units"
    ] is True
    assert template["statistics_gate"][
        "fixed_evaluation_tapes_do_not_establish_iid_environment_generalization"
    ] is True
    ledger_contract = template["sample_ledger_contract"]
    assert ledger_contract[
        "same_training_lane_authorities_and_counts_required_for_all_arms"
    ] is True
    assert ledger_contract[
        "standalone_evaluation_counts_may_vary_with_policy_survival_length"
    ] is True
    assert ledger_contract[
        "standalone_evaluation_counts_replay_from_each_fixed_64_episode_tape"
    ] is True
    assert template["joint_success_gate"]["complete_72_of_72_matrix_required"] is True
    assert template["confirmatory_execution_contract"][
        "same_execution_environment_tuple_required_for_all_72_jobs"
    ] == [
        "hostname",
        "python_version",
        "numpy_version",
        "torch_version",
        "torch_cuda_runtime_version",
        "torch_cudnn_version",
        "cuda_device_name",
    ]
    assert template["confirmatory_execution_contract"]["jobs_per_worker"] == 36
    assert template["confirmatory_execution_contract"][
        "seeds_per_cuda_ordinal"
    ] == 12
    assert template["confirmatory_execution_contract"][
        "completed_job_artifact_triplet"
    ] == ["JSON_RESULT", "PT_MODEL", "LOG"]
    assert template["confirmatory_execution_contract"][
        "matching_job_completed_status_required_for_every_job"
    ] is True
    assert template["confirmatory_execution_contract"][
        "job_failed_status_forbids_evaluation"
    ] is True
    assert template["confirmatory_execution_contract"][
        "same_seed_all_three_arms_share_cuda_ordinal"
    ] is True
    assert list(
        template["confirmatory_execution_contract"]["device_by_seed"].values()
    ).count("cuda:0") == 12
    assert "AT_REGISTERED_PRIMARY_25000_AND_100000_CHECKPOINTS" in claims[
        "maximum_positive_claim_scope"
    ]
    assert "ON_REGISTERED_FIXED_EVALUATION_TAPES" in claims[
        "maximum_positive_claim_scope"
    ]
    assert claims["sample_tax_claim_only_at_registered_checkpoints"] is True
    assert claims["checkpoint_50000_is_diagnostic_only"] is True
    assert claims["checkpoint_50000_can_change_scientific_success"] is False
    assert claims[
        "unobserved_intermediate_threshold_crossing_order_claimed"
    ] is False
    for gate in (
        "WORKLOAD_ECONOMICS_GATE",
        "SCALAR_CALIBRATION_GATE",
        "BREAK_EVEN_GATE",
        "OFFICIAL_EXECUTION_GATE",
    ):
        assert claims[gate] == "NOT_RUN"
    assert claims["official_execution_allowed"] is False
    assert claims["total_operational_work_dominance_claimed"] is False
    assert claims["broad_iid_sample_efficiency_claimed"] is False
    assert claims["cross_domain_transfer_claimed"] is False
    assert claims["neural_representation_discovery_claimed"] is False


def test_ratified_protocol_identity_is_exact() -> None:
    protocol = _protocol()
    assert validate_ratified_hybrid_confirmatory_protocol_v2(protocol) == protocol
    changed = deepcopy(protocol)
    changed["training_seeds"][0] += 1
    with pytest.raises(
        LatentResourceHybridConfirmatoryProtocolV2Error, match="not replayable"
    ):
        validate_ratified_hybrid_confirmatory_protocol_v2(changed)


def test_three_observation_arms_retain_raw_and_match_only_hybrid_width() -> None:
    state = initial_state_v1(seed="hybrid-confirmatory-unit", episode_index=0)
    raw = observation_vector_hybrid_confirmatory_v2(state, RAW_STANDARD_ARM_V2)
    rotated = observation_vector_hybrid_confirmatory_v2(
        state, ROTATED_CONTROL_ARM_V2
    )
    candidate = observation_vector_hybrid_confirmatory_v2(
        state, RESOURCE_CANDIDATE_ARM_V2
    )
    assert len(raw) == 16
    assert len(rotated) == len(candidate) == 32
    assert rotated[:16] == candidate[:16] == raw
    assert rotated[16:] == tuple(reversed(raw))
    assert candidate[16:] != rotated[16:]
    with pytest.raises(
        runtime.MatchedDoubleDQN2048V1Error, match="not registered"
    ):
        observation_vector_hybrid_confirmatory_v2(state, "RAW_BOARD")


def test_tiny_cpu_runtime_preserves_per_arm_dimensions_ledgers_and_tapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("numpy")
    pytest.importorskip("torch")
    protocol = _protocol()
    training = protocol["training"]
    training.update(
        {
            "environment_steps_per_seed_arm": 20,
            "evaluation_checkpoints": [20],
            "evaluation_episodes_per_checkpoint": 1,
            "replay_capacity": 64,
            "replay_warmup_environment_steps": 4,
            "batch_size": 4,
            "train_every_environment_steps": 4,
            "target_network_sync_environment_steps": 8,
        }
    )
    training["epsilon_schedule"]["decay_steps"] = 20
    monkeypatch.setattr(
        runtime,
        "validate_ratified_hybrid_confirmatory_protocol_v2",
        lambda value: value,
    )

    results = []
    for arm in HYBRID_CONFIRMATORY_ARMS_V2:
        result, _ = run_hybrid_confirmatory_seed_arm_v2(
            protocol=protocol, arm=arm, seed=760101, device_name="cpu"
        )
        results.append(result)
        ledger = SampleLedgerV1.from_document(result["sample_ledger"])
        assert result["schema"] == HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2
        assert result["training_environment_interactions"] == 20
        assert ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        ) == 20
        assert ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        ) == 40
        assert result["tape_binding"]["training_tape_root"].endswith(":760101")
        assert result["scientific_success_claimed"] is False

    assert results[0]["network_parameter_count"] == RAW_STANDARD_PARAMETER_COUNT_V2
    assert {row["network_parameter_count"] for row in results[1:]} == {
        HYBRID_PARAMETER_COUNT_V2
    }
    assert results[0]["representation_telemetry"]["input_dimension"] == 16
    assert {
        row["representation_telemetry"]["input_dimension"] for row in results[1:]
    } == {32}


def test_complete_evidence_bound_paired_matrix_passes() -> None:
    pytest.importorskip("scipy")
    protocol = _protocol()
    result = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=_matrix(protocol)
    )
    primary = result["primary_seed_paired_gate"]
    assert result["artifact_count"] == 72
    assert result["evidence_complete"] is True
    assert result["primary_gate_checkpoints"] == [25_000, 100_000]
    assert result["diagnostic_only_checkpoints"] == [50_000]
    assert result["checkpoint_50000_can_change_joint_gate"] is False
    assert primary["candidate_25000_threshold_attainment"][
        "passes_registered_test"
    ] is True
    assert primary["raw_25000_threshold_nonattainment"][
        "passes_registered_test"
    ] is True
    assert primary["sample_tax_strictly_lower"] is True
    assert primary["candidate_100000_minus_raw_100000"][
        "passes_registered_test"
    ] is True
    assert primary["candidate_100000_minus_rotated_100000"][
        "passes_registered_test"
    ] is True
    assert result["candidate_and_rotated_control_parameter_count_equal"] is True
    assert result["candidate_and_raw_standard_parameter_count_equal"] is False
    assert "AT_REGISTERED_PRIMARY_25000_AND_100000_CHECKPOINTS" in result[
        "maximum_positive_claim_scope"
    ]
    assert set(
        result["economics_scalar_break_even_and_official_execution_gates"].values()
    ) == {"NOT_RUN"}
    assert result["seed_is_statistical_unit"] is True
    assert result["evaluation_episode_is_statistical_unit"] is False
    assert result[
        "fixed_evaluation_tapes_establish_iid_environment_generalization"
    ] is False
    assert result["primary_seed_paired_gate"]["global_null"].startswith(
        "AT_LEAST_ONE"
    )
    assert result["primary_seed_paired_gate"]["multiple_testing_rule"] == (
        "INTERSECTION_UNION_NO_ALPHA_SPLIT"
    )
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "PASS"
    assert result["scientific_success_claimed"] is True
    assert result["welch_sensitivity_not_gate"]["can_change_joint_gate"] is False


def test_one_failed_paired_component_fails_even_if_sensitivity_is_reported() -> None:
    pytest.importorskip("scipy")
    protocol = _protocol()
    artifacts = _matrix(protocol)
    for artifact in artifacts:
        if artifact["arm"] != ROTATED_CONTROL_ARM_V2:
            continue
        seed_index = protocol["training_seeds"].index(artifact["seed"])
        score = 1_600 + 15 * seed_index
        final = artifact["evaluations"][-1]
        final["mean_total_merge_score"] = score
        for episode in final["episodes"]:
            episode["total_merge_score"] = score
    result = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    assert result["primary_seed_paired_gate"][
        "candidate_100000_minus_rotated_100000"
    ]["passes_registered_test"] is False
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "FAIL"
    assert result["scientific_success_claimed"] is False
    assert result["primary_seed_paired_gate"][
        "component_results_descriptive_only_due_to_joint_failure"
    ] is True
    assert result["welch_sensitivity_not_gate"]["can_change_joint_gate"] is False


def test_candidate_attainment_alone_cannot_fake_lower_sample_tax() -> None:
    pytest.importorskip("scipy")
    protocol = _protocol()
    artifacts = _matrix(protocol)
    for artifact in artifacts:
        if artifact["arm"] != RAW_STANDARD_ARM_V2:
            continue
        seed_index = protocol["training_seeds"].index(artifact["seed"])
        score = 1_050 + 11 * seed_index
        early_25 = artifact["evaluations"][0]
        early_25["mean_total_merge_score"] = score
        for episode in early_25["episodes"]:
            episode["total_merge_score"] = score
    result = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    primary = result["primary_seed_paired_gate"]
    assert primary["candidate_25000_threshold_attainment"][
        "passes_registered_test"
    ] is True
    assert primary["raw_25000_threshold_nonattainment"][
        "passes_registered_test"
    ] is False
    assert primary["sample_tax_strictly_lower"] is False
    assert result["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "FAIL"
    assert result["scientific_success_claimed"] is False


def test_50000_checkpoint_is_diagnostic_and_cannot_change_gate() -> None:
    pytest.importorskip("scipy")
    protocol = _protocol()
    reference = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=_matrix(protocol)
    )
    artifacts = _matrix(protocol)
    for artifact in artifacts:
        seed_index = protocol["training_seeds"].index(artifact["seed"])
        diagnostic_score = 20_000 + 100 * seed_index
        checkpoint_50000 = artifact["evaluations"][1]
        checkpoint_50000["mean_total_merge_score"] = diagnostic_score
        for episode in checkpoint_50000["episodes"]:
            episode["total_merge_score"] = diagnostic_score
    changed = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=artifacts
    )
    assert changed["primary_seed_paired_gate"] == reference[
        "primary_seed_paired_gate"
    ]
    assert changed["JOINT_SCIENTIFIC_SUCCESS_GATE"] == (
        reference["JOINT_SCIENTIFIC_SUCCESS_GATE"]
    )
    assert changed["checkpoint_score_mean_sem_by_arm"] != reference[
        "checkpoint_score_mean_sem_by_arm"
    ]


def test_partial_or_unratified_matrix_cannot_run_gate() -> None:
    protocol = _protocol()
    partial = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=protocol, seed_arm_artifacts=_matrix(protocol)[:-1]
    )
    assert partial["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"
    template = build_hybrid_confirmatory_template_v2()
    unratified = evaluate_hybrid_confirmatory_joint_gate_v2(
        protocol=template, seed_arm_artifacts=[]
    )
    assert unratified["JOINT_SCIENTIFIC_SUCCESS_GATE"] == "NOT_RUN"


def test_contradictory_parameter_or_tape_evidence_is_rejected() -> None:
    protocol = _protocol()
    artifacts = _matrix(protocol)
    artifacts[0]["network_parameter_count"] = HYBRID_PARAMETER_COUNT_V2
    with pytest.raises(HybridConfirmatoryGateV2Error, match="parameter count"):
        evaluate_hybrid_confirmatory_joint_gate_v2(
            protocol=protocol, seed_arm_artifacts=artifacts
        )
    artifacts = _matrix(protocol)
    artifacts[-1]["tape_binding"]["evaluation_tape_root"] = "foreign"
    with pytest.raises(HybridConfirmatoryGateV2Error, match="tape binding"):
        evaluate_hybrid_confirmatory_joint_gate_v2(
            protocol=protocol, seed_arm_artifacts=artifacts
        )
    artifacts = _matrix(protocol)
    artifacts[-1]["execution_context"]["cuda_device_name"] = "FOREIGN GPU"
    with pytest.raises(HybridConfirmatoryGateV2Error, match="environments changed"):
        evaluate_hybrid_confirmatory_joint_gate_v2(
            protocol=protocol, seed_arm_artifacts=artifacts
        )
    artifacts = _matrix(protocol)
    artifacts[-1]["hybrid_confirmatory_joint_gate"] = "PASS"
    artifacts[-1]["scientific_success_claimed"] = True
    with pytest.raises(HybridConfirmatoryGateV2Error, match="single-job"):
        evaluate_hybrid_confirmatory_joint_gate_v2(
            protocol=protocol, seed_arm_artifacts=artifacts
        )


def test_manifest_status_and_artifact_triplets_close_exact_matrix(
    tmp_path: Path,
) -> None:
    protocol = _protocol()
    artifacts = _matrix(protocol)
    results = tmp_path / "results"
    (results / "artifacts").mkdir(parents=True)
    (results / "logs").mkdir()
    jobs = []
    status_rows: dict[int, list[dict]] = {0: [], 1: []}
    for ordinal, artifact in enumerate(artifacts):
        worker = ordinal % 2
        execution_id = artifact["execution_context"]["execution_id"]
        jobs.append(
            {
                "job_ordinal": ordinal,
                "arm": artifact["arm"],
                "seed": artifact["seed"],
                "execution_id": execution_id,
                "worker": worker,
                "device": f"cuda:{worker}",
            }
        )
        stem = f"{artifact['arm'].lower()}-seed-{artifact['seed']}"
        (results / "artifacts" / f"{stem}.json").write_text(
            json.dumps(artifact), encoding="utf-8"
        )
        (results / "artifacts" / f"{stem}.pt").write_bytes(b"model")
        (results / "logs" / f"{stem}.log").write_text(
            "JOB_COMPLETED\n", encoding="utf-8"
        )
        status_rows[worker].append(
            {"event": "JOB_COMPLETED", "execution_id": execution_id}
        )
    for worker in (0, 1):
        status_rows[worker].append({"event": "WORKER_COMPLETED"})
        (results / f"worker-{worker}-status.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in status_rows[worker]),
            encoding="utf-8",
        )
    manifest = {
        "schema": HYBRID_CONFIRMATORY_MANIFEST_SCHEMA_V2,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }
    loaded = load_evidence_bound_hybrid_confirmatory_matrix_v2(
        protocol=protocol, manifest=manifest, results_root=results
    )
    assert [(row["arm"], row["seed"]) for row in loaded] == [
        (row["arm"], row["seed"]) for row in artifacts
    ]

    (results / "logs" / "foreign.log").write_text("foreign\n", encoding="utf-8")
    with pytest.raises(HybridConfirmatoryEvaluatorV2Error, match="foreign"):
        load_evidence_bound_hybrid_confirmatory_matrix_v2(
            protocol=protocol, manifest=manifest, results_root=results
        )
    (results / "logs" / "foreign.log").unlink()

    missing_stem = f"{artifacts[-1]['arm'].lower()}-seed-{artifacts[-1]['seed']}"
    (results / "artifacts" / f"{missing_stem}.pt").unlink()
    with pytest.raises(HybridConfirmatoryEvaluatorV2Error, match="missing"):
        load_evidence_bound_hybrid_confirmatory_matrix_v2(
            protocol=protocol, manifest=manifest, results_root=results
        )


def test_ratifier_and_runner_preflight_are_source_bound_and_cuda_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ratifier = _load_script(
        "ratify_latent_resource_hybrid_confirmatory_v2",
        "scripts/ratify_latent_resource_hybrid_confirmatory_v2.py",
    )
    runner = _load_script(
        "run_matched_double_dqn_2048_hybrid_confirmatory_v2",
        "scripts/run_matched_double_dqn_2048_hybrid_confirmatory_v2.py",
    )
    repository = tmp_path / "source"
    repository.mkdir()
    output = tmp_path / "ratified" / "protocol.json"
    monkeypatch.setattr(
        ratifier, "bound_clean_source_commit_v1", lambda _repository: "2" * 40
    )
    protocol = ratifier.ratify_hybrid_confirmatory_protocol_file_v2(
        repository=repository, output=output
    )
    assert output.read_bytes() == canonical_json_bytes(protocol)
    with pytest.raises(FileExistsError):
        ratifier.ratify_hybrid_confirmatory_protocol_file_v2(
            repository=repository, output=output
        )

    runner._validate_execution_request(
        protocol=protocol,
        source_commit="2" * 40,
        arm=RESOURCE_CANDIDATE_ARM_V2,
        seed=760101,
        device="cuda:0",
    )
    with pytest.raises(
        LatentResourceHybridConfirmatoryProtocolV2Error, match="CUDA"
    ):
        runner._validate_execution_request(
            protocol=protocol,
            source_commit="2" * 40,
            arm=RESOURCE_CANDIDATE_ARM_V2,
            seed=760101,
            device="cpu",
        )
    with pytest.raises(
        LatentResourceHybridConfirmatoryProtocolV2Error, match="source commit"
    ):
        runner._validate_execution_request(
            protocol=protocol,
            source_commit="3" * 40,
            arm=RESOURCE_CANDIDATE_ARM_V2,
            seed=760101,
            device="cuda:0",
        )
