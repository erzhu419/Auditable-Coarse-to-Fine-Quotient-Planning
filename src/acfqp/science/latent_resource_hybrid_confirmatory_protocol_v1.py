"""Outcome-free protocol for the raw-preserving hybrid confirmation.

This protocol is a fresh successor to the retained u003 failure and the
nonconfirmatory hybrid pilot.  Neither predecessor contributes observations to
the matrix.  The primary gate uses the ten fresh seeds as paired statistical
units and is frozen before the source commit is ratified.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


HYBRID_CONFIRMATORY_PROTOCOL_DOMAIN_V1 = (
    "acfqp:latent-resource-hybrid-confirmatory-protocol:v1"
)
U003_PROTOCOL_ID_V1 = (
    "8b77cfe4f3549f7f6ba6e586a8fca41aefa29feb0d03ab8aa27ab694f7e98b3e"
)
HYBRID_PILOT_PROTOCOL_ID_V1 = (
    "82b470e09dbb846dac2e858c8f0c0a5450f5008173751985faf1cf14fe6a69be"
)
HYBRID_CONFIRMATORY_ARMS_V1 = (
    "RAW_BOARD_STANDARD",
    "RAW_PLUS_ROTATED_RAW_CONTROL",
    "RAW_PLUS_RESOURCE_STATE_ONLY",
)
RAW_STANDARD_ARM_V1 = HYBRID_CONFIRMATORY_ARMS_V1[0]
ROTATED_CONTROL_ARM_V1 = HYBRID_CONFIRMATORY_ARMS_V1[1]
RESOURCE_CANDIDATE_ARM_V1 = HYBRID_CONFIRMATORY_ARMS_V1[2]
HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1 = tuple(range(750101, 750111))
HYBRID_CONFIRMATORY_DEVICE_BY_SEED_V1 = tuple(
    (seed, f"cuda:{index % 2}")
    for index, seed in enumerate(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1)
)
HYBRID_CONFIRMATORY_CHECKPOINTS_V1 = (25_000, 50_000, 100_000)
RAW_STANDARD_INPUT_DIMENSION_V1 = 16
HYBRID_INPUT_DIMENSION_V1 = 32
RAW_STANDARD_PARAMETER_COUNT_V1 = 71_172
HYBRID_PARAMETER_COUNT_V1 = 75_268


class LatentResourceHybridConfirmatoryProtocolV1Error(ValueError):
    """The successor protocol changed shape or identity."""


def _fail(message: str) -> NoReturn:
    raise LatentResourceHybridConfirmatoryProtocolV1Error(message)


def _with_identity_v1(payload: dict[str, Any]) -> dict[str, Any]:
    protocol_id = hashlib.sha256(
        HYBRID_CONFIRMATORY_PROTOCOL_DOMAIN_V1.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


def _training_contract_v1() -> dict[str, Any]:
    return {
        "environment_steps_per_seed_arm": 100_000,
        "evaluation_checkpoints": list(HYBRID_CONFIRMATORY_CHECKPOINTS_V1),
        "evaluation_episodes_per_checkpoint": 64,
        "replay_capacity": 250_000,
        "replay_warmup_environment_steps": 10_000,
        "batch_size": 256,
        "train_every_environment_steps": 4,
        "gradient_updates_per_train_event": 1,
        "target_network_sync_environment_steps": 2_000,
        "discount": {"numerator": 99, "denominator": 100},
        "adam_learning_rate": {"numerator": 3, "denominator": 10_000},
        "huber_delta": 1,
        "epsilon_schedule": {
            "kind": "LINEAR_BY_ONLINE_TARGET_ENVIRONMENT_INTERACTION",
            "start": {"numerator": 1, "denominator": 1},
            "end": {"numerator": 1, "denominator": 20},
            "decay_steps": 100_000,
        },
        "reward_transform": "log2(merge_score)/11_if_positive_else_zero",
        "episode_ends_on": ["WON_AT_TILE_2048", "NO_LEGAL_ACTION"],
        "training_evaluation_separation": True,
        "schedule_frozen_from_hybrid_pilot": True,
    }


def registered_hybrid_confirmatory_device_v1(seed: int) -> str:
    """Return the preregistered CUDA ordinal for one fresh training seed."""

    if type(seed) is not int:
        _fail("hybrid confirmatory seed must be exact")
    for registered_seed, device in HYBRID_CONFIRMATORY_DEVICE_BY_SEED_V1:
        if seed == registered_seed:
            return device
    _fail("seed is not registered by the hybrid confirmatory device blocks")


def build_hybrid_confirmatory_template_v1() -> dict[str, Any]:
    """Return the frozen template, without execution authority."""

    payload: dict[str, Any] = {
        "schema": "acfqp.science.latent_resource_hybrid_confirmatory_protocol.v1",
        "campaign_kind": "HYBRID_CONFIRMATORY_TEMPLATE_NOT_YET_AUTHORIZED",
        "research_question": (
            "Does a deterministic state-only resource vector preserve its early "
            "sample advantage and improve final 2048 policy quality when the "
            "lossless raw board remains available?"
        ),
        "predecessor_evidence_contract": {
            "u003_protocol_id": U003_PROTOCOL_ID_V1,
            "u003_joint_gate": "FAIL_RETAINED_WITHOUT_REINTERPRETATION",
            "hybrid_pilot_protocol_id": HYBRID_PILOT_PROTOCOL_ID_V1,
            "hybrid_pilot_role": "DESIGN_ONLY_NOT_IN_CONFIRMATORY_MATRIX",
            "predecessor_seeds_or_outcomes_pooled": False,
        },
        "arms": list(HYBRID_CONFIRMATORY_ARMS_V1),
        "training_seeds": list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1),
        "training_tape_prefix": (
            "acfqp-latent-resource-hybrid-confirmatory-train-v1"
        ),
        "evaluation_tape_prefix": (
            "acfqp-latent-resource-hybrid-confirmatory-eval-v1"
        ),
        "representation_contract": {
            "RAW_BOARD_STANDARD": {
                "input_dimension": RAW_STANDARD_INPUT_DIMENSION_V1,
                "network_parameter_count": RAW_STANDARD_PARAMETER_COUNT_V1,
                "observation": "sixteen normalized lossless board ranks",
                "role": "GENERAL_MATCHED_DOUBLE_DQN_SAMPLE_TAX_BENCHMARK",
            },
            "RAW_PLUS_ROTATED_RAW_CONTROL": {
                "input_dimension": HYBRID_INPUT_DIMENSION_V1,
                "network_parameter_count": HYBRID_PARAMETER_COUNT_V1,
                "first_block": "sixteen normalized lossless board ranks",
                "second_block": "fixed 180-degree rotation of the raw board",
                "second_block_adds_information": False,
                "role": "ACTIVE_WIDTH_AND_PARAMETER_MATCHED_CONTROL",
            },
            "RAW_PLUS_RESOURCE_STATE_ONLY": {
                "input_dimension": HYBRID_INPUT_DIMENSION_V1,
                "network_parameter_count": HYBRID_PARAMETER_COUNT_V1,
                "first_block": "sixteen normalized lossless board ranks",
                "second_block": "frozen sixteen-coordinate state-only resource adapter",
                "second_block_is_deterministic_from_current_board": True,
                "second_block_calls_transition_or_successor_kernel": False,
                "role": "RESOURCE_AUGMENTED_CANDIDATE",
            },
            "candidate_and_rotated_control_equal_parameter_count": True,
            "candidate_and_raw_standard_equal_parameter_count": False,
            "raw_standard_comparison_is_not_a_pure_representation_causal_claim": True,
            "all_arms_retain_the_same_lossless_raw_board": True,
        },
        "network_contract": {
            "algorithm": "DOUBLE_DQN",
            "mlp_hidden_widths": [256, 256],
            "activation": "RELU",
            "output_action_count": 4,
            "online_and_target_networks": True,
            "online_argmax_target_evaluation": True,
            "illegal_actions_masked_in_all_arms": True,
            "same_optimizer_replay_target_update_epsilon_reward_and_budget": True,
        },
        "sample_ledger_contract": {
            "primary_sample_tax_axis": "online_target.ENVIRONMENT_INTERACTION",
            "all_twenty_rows_materialized_including_native_zero": True,
            "representation_adds_zero_exact_kernel_queries": True,
            "same_training_lane_authorities_and_counts_required_for_all_arms": True,
            "standalone_evaluation_authorities_are_the_same_for_all_arms": True,
            "standalone_evaluation_counts_may_vary_with_policy_survival_length": True,
            "standalone_evaluation_counts_replay_from_each_fixed_64_episode_tape": True,
            "replay_draws_gradient_updates_and_latency_are_compute_not_samples": True,
        },
        "training": _training_contract_v1(),
        "statistics_gate": {
            "seed_is_statistical_unit": True,
            "seed_count": 10,
            "uncertainty_is_across_ten_training_seeds": True,
            (
                "evaluation_episodes_are_fixed_tape_measurements_"
                "not_statistical_units"
            ): True,
            (
                "fixed_evaluation_tapes_do_not_establish_"
                "iid_environment_generalization"
            ): True,
            "same_seed_training_tape_across_arms": True,
            "same_evaluation_tapes_across_all_seed_arms": True,
            "alpha": {"numerator": 1, "denominator": 20},
            "primary_tests_are_seed_paired": True,
            "welch_tests_are_sensitivity_only_and_cannot_change_gate": True,
        },
        "joint_success_gate": {
            "kind": "STRICT_CONJUNCTION_OF_FOUR_SEED_PAIRED_TESTS",
            "global_null": "AT_LEAST_ONE_OF_THE_FOUR_COMPONENT_CLAIMS_IS_FALSE",
            "global_alternative": "ALL_FOUR_COMPONENT_CLAIMS_ARE_TRUE",
            "multiple_testing_rule": "INTERSECTION_UNION_NO_ALPHA_SPLIT",
            "multiple_testing_rationale": (
                "EACH_COMPONENT_AT_ALPHA_0.05_CONTROLS_THE_GLOBAL_SIZE_BECAUSE_"
                "THE_JOINT_CLAIM_REQUIRES_REJECTION_OF_ALL_FOUR_COMPONENT_NULLS"
            ),
            "candidate_arm": RESOURCE_CANDIDATE_ARM_V1,
            "general_rl_reference_arm": RAW_STANDARD_ARM_V1,
            "active_width_control_arm": ROTATED_CONTROL_ARM_V1,
            "candidate_50000_threshold_attainment_test": {
                "per_seed_difference": (
                    "candidate_mean_score_at_50000_minus_0.99_times_"
                    "raw_standard_mean_score_at_100000"
                ),
                "test": "ONE_SAMPLE_T_TEST_GREATER_THAN_ZERO",
                "one_sided_p_less_than_alpha": True,
                "one_sided_95_percent_lower_bound_strictly_positive": True,
            },
            "raw_early_threshold_nonattainment_test": {
                "per_seed_difference": (
                    "0.99_times_raw_standard_mean_score_at_100000_minus_max_of_"
                    "raw_standard_mean_score_at_25000_and_50000"
                ),
                "test": "ONE_SAMPLE_T_TEST_GREATER_THAN_ZERO",
                "one_sided_p_less_than_alpha": True,
                "one_sided_95_percent_lower_bound_strictly_positive": True,
                "maximum_handles_nonmonotone_early_learning_curve": True,
            },
            "sample_tax_strictly_lower_requires_both_early_tests": True,
            "candidate_vs_raw_final_test": {
                "per_seed_difference": (
                    "candidate_mean_score_at_100000_minus_"
                    "raw_standard_mean_score_at_100000"
                ),
                "test": "TWO_SIDED_PAIRED_T_TEST",
                "two_sided_p_less_than_alpha": True,
                "two_sided_95_percent_lower_bound_strictly_positive": True,
            },
            "candidate_vs_rotated_final_test": {
                "per_seed_difference": (
                    "candidate_mean_score_at_100000_minus_"
                    "rotated_control_mean_score_at_100000"
                ),
                "test": "TWO_SIDED_PAIRED_T_TEST",
                "two_sided_p_less_than_alpha": True,
                "two_sided_95_percent_lower_bound_strictly_positive": True,
            },
            "all_four_tests_must_pass": True,
            "confirmatory_primary_claim_allowed_only_if_joint_gate_passes": True,
            "component_results_are_descriptive_if_joint_gate_fails": True,
            "complete_30_of_30_matrix_required": True,
        },
        "confirmatory_execution_contract": {
            "required_device_type": "CUDA",
            "worker_count": 2,
            "worker_device_bindings": {"0": "cuda:0", "1": "cuda:1"},
            "jobs_per_worker": 15,
            "seeds_per_cuda_ordinal": 5,
            "same_seed_all_three_arms_share_cuda_ordinal": True,
            "device_by_seed": {
                str(seed): device
                for seed, device in HYBRID_CONFIRMATORY_DEVICE_BY_SEED_V1
            },
            "exact_manifest_30_job_identity_closure_required": True,
            "completed_job_artifact_triplet": ["JSON_RESULT", "PT_MODEL", "LOG"],
            "matching_job_completed_status_required_for_every_job": True,
            "job_failed_status_forbids_evaluation": True,
            "exactly_one_worker_completed_status_required_per_worker": True,
            "same_execution_environment_tuple_required_for_all_30_jobs": [
                "hostname",
                "python_version",
                "numpy_version",
                "torch_version",
                "torch_cuda_runtime_version",
                "torch_cudnn_version",
                "cuda_device_name",
            ],
            "source_commit_derived_from_clean_checkout": True,
            "protocol_and_result_outputs_outside_source_checkout": True,
            "fresh_execution_identity_required_for_every_seed_arm": True,
            "failed_execution_identity_may_not_be_retried": True,
            "pilot_artifacts_excluded_from_confirmatory_matrix": True,
        },
        "claim_boundary": {
            "u003_success_reinterpreted": False,
            "pilot_scientific_success_claimed": False,
            "pure_representation_causality_claimed_against_raw_standard": False,
            "neural_representation_discovery_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "cross_domain_transfer_claimed": False,
            "total_operational_work_dominance_claimed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "official_execution_allowed": False,
            "maximum_positive_claim_scope": (
                "SYMBOLIC_STANDARD_4X4_2048_ON_REGISTERED_FIXED_EVALUATION_TAPES_"
                "AT_REGISTERED_25000_50000_100000_CHECKPOINTS_WITHIN_100000_"
                "TARGET_INTERACTIONS"
            ),
            "sample_tax_claim_only_at_registered_checkpoints": True,
            "unobserved_intermediate_threshold_crossing_order_claimed": False,
            "scientific_success_claimed": False,
        },
        "confirmatory_execution_authorized": False,
        "authorization": "NOT_AUTHORIZED_UNTIL_CLEAN_SOURCE_COMMIT_IS_RATIFIED",
    }
    return _with_identity_v1(payload)


def build_ratified_hybrid_confirmatory_protocol_v1(
    source_commit: str,
) -> dict[str, Any]:
    """Bind the unchanged template to one clean source commit."""

    if (
        type(source_commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
    ):
        _fail("ratification source commit must be one lowercase full Git object ID")
    template = build_hybrid_confirmatory_template_v1()
    payload = dict(template)
    del payload["protocol_id"]
    payload["campaign_kind"] = "HYBRID_CONFIRMATORY_RATIFIED"
    payload["authorization"] = "RATIFIED_FOR_EXECUTION"
    payload["confirmatory_protocol_ratified"] = True
    payload["confirmatory_execution_authorized"] = True
    payload["source_commit"] = source_commit
    return _with_identity_v1(payload)


def validate_hybrid_confirmatory_protocol_identity_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the successor identity without granting execution authority."""

    if type(protocol) is not dict:
        _fail("hybrid confirmatory protocol must be a plain object")
    protocol_id = protocol.get("protocol_id")
    if (
        type(protocol_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", protocol_id) is None
    ):
        _fail("hybrid confirmatory protocol identity changed shape")
    payload = dict(protocol)
    del payload["protocol_id"]
    expected = _with_identity_v1(payload)
    if expected["protocol_id"] != protocol_id:
        _fail("hybrid confirmatory protocol identity is not replayable")
    return dict(protocol)


def validate_ratified_hybrid_confirmatory_protocol_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept only the exact frozen template bound to its source commit."""

    replayed = validate_hybrid_confirmatory_protocol_identity_v1(protocol)
    source_commit = replayed.get("source_commit")
    if type(source_commit) is not str:
        _fail("ratified hybrid confirmatory protocol has no source commit")
    expected = build_ratified_hybrid_confirmatory_protocol_v1(source_commit)
    if replayed != expected:
        _fail("ratified hybrid confirmatory protocol differs from the frozen template")
    return replayed


__all__ = (
    "HYBRID_CONFIRMATORY_ARMS_V1",
    "HYBRID_CONFIRMATORY_CHECKPOINTS_V1",
    "HYBRID_CONFIRMATORY_DEVICE_BY_SEED_V1",
    "HYBRID_CONFIRMATORY_PROTOCOL_DOMAIN_V1",
    "HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1",
    "HYBRID_INPUT_DIMENSION_V1",
    "HYBRID_PARAMETER_COUNT_V1",
    "HYBRID_PILOT_PROTOCOL_ID_V1",
    "LatentResourceHybridConfirmatoryProtocolV1Error",
    "RAW_STANDARD_ARM_V1",
    "RAW_STANDARD_INPUT_DIMENSION_V1",
    "RAW_STANDARD_PARAMETER_COUNT_V1",
    "RESOURCE_CANDIDATE_ARM_V1",
    "ROTATED_CONTROL_ARM_V1",
    "U003_PROTOCOL_ID_V1",
    "build_hybrid_confirmatory_template_v1",
    "build_ratified_hybrid_confirmatory_protocol_v1",
    "registered_hybrid_confirmatory_device_v1",
    "validate_hybrid_confirmatory_protocol_identity_v1",
    "validate_ratified_hybrid_confirmatory_protocol_v1",
)
