"""Outcome-free protocols for the latent-resource Double-DQN experiment."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


PROTOCOL_DOMAIN = "acfqp:latent-resource-matched-double-dqn-protocol:v1"
ARMS = (
    "RAW_BOARD",
    "RESOURCE_STATE_ONLY",
    "RESOURCE_STATE_ONLY_DROP_ANCHOR",
    "RESOURCE_STATE_ONLY_DROP_LIQUIDITY",
)


class LatentResourceProtocolV1Error(ValueError):
    """The pilot or confirmatory protocol changed shape."""


def _fail(message: str) -> NoReturn:
    raise LatentResourceProtocolV1Error(message)


def _training_contract(
    *, environment_steps: int, checkpoints: tuple[int, ...], evaluation_episodes: int
) -> dict[str, Any]:
    if (
        type(environment_steps) is not int
        or environment_steps <= 0
        or type(checkpoints) is not tuple
        or not checkpoints
        or checkpoints[-1] != environment_steps
        or tuple(sorted(set(checkpoints))) != checkpoints
        or any(type(value) is not int or value <= 0 for value in checkpoints)
        or type(evaluation_episodes) is not int
        or evaluation_episodes <= 0
    ):
        _fail("training schedule is invalid")
    return {
        "environment_steps_per_seed_arm": environment_steps,
        "evaluation_checkpoints": list(checkpoints),
        "evaluation_episodes_per_checkpoint": evaluation_episodes,
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
            "decay_steps": min(200_000, environment_steps),
        },
        "reward_transform": "log2(merge_score)/11_if_positive_else_zero",
        "episode_ends_on": ["WON_AT_TILE_2048", "NO_LEGAL_ACTION"],
        "training_evaluation_separation": True,
    }


def _common_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.science.latent_resource_matched_double_dqn_protocol.v1",
        "research_question": (
            "Does a deterministic state-only hidden-resource representation reach "
            "a stronger 2048 policy with fewer target interactions than matched "
            "raw-state Double-DQN?"
        ),
        "domain": {
            "name": "STANDARD_4X4_2048",
            "state_semantics": "acfqp.domains.standard_2048.Swipe2048State",
            "action_order": ["UP", "DOWN", "LEFT", "RIGHT"],
            "goal_rank": 11,
            "spawn_rank_distribution": {"rank_1": "9/10", "rank_2": "1/10"},
            "spawn_cell_distribution": "UNIFORM_OVER_POST_SWIPE_EMPTY_CELLS",
            "stable_sha256_tapes": True,
            "symbolic_primary_experiment": True,
            "visual_perception_layer_present": False,
        },
        "representation_contract": {
            "input_dimension_for_every_arm": 16,
            "raw_board": "sixteen rank values normalized to the registered rank cap",
            "resource_phi_shared_coordinates": [
                "capacity_slack",
                "locked_mass",
                "frontier_exposure",
                "consolidation_potential",
                "option_value",
                "irreversibility_risk",
            ],
            "standard_2048_state_only_adapter": [
                "max_tile_corner_anchor",
                "snake_monotonic_order",
                "empty_cell_slack",
                "visible_adjacent_merge_density",
                "directional_flow_liquidity",
                "anchor_displacement_risk",
                "action_oriented_visible_merge_opportunity",
            ],
            "state_only_resource_is_deterministic_from_the_same_board": True,
            "state_only_resource_calls_no_transition_or_successor_kernel": True,
            "state_only_resource_receives_no_extra_environment_information": True,
            "state_only_resource_is_a_registered_human_inductive_bias_not_learned_discovery": True,
            "known_model_one_step_resource_control_implemented_but_not_a_registered_arm": True,
            "known_model_control_cannot_by_itself_establish_pure_representation_advantage": True,
            "future_second_domain": "LAYERED_MATCHING_BUFFER",
            "cross_domain_transfer_claimed_in_this_protocol": False,
        },
        "network_contract": {
            "algorithm": "DOUBLE_DQN",
            "mlp_hidden_widths": [256, 256],
            "activation": "RELU",
            "output_action_count": 4,
            "online_and_target_networks": True,
            "online_argmax_target_evaluation": True,
            "illegal_actions_masked_in_all_arms": True,
            "same_parameter_count_for_all_arms": True,
            "same_optimizer_replay_target_update_epsilon_reward_and_budget": True,
        },
        "sample_ledger_contract": {
            "evidence_classes": [
                "ENVIRONMENT_INTERACTION",
                "GENERATIVE_ORACLE_SAMPLE",
                "EXACT_KERNEL_QUERY",
                "OFFLINE_LOGGED_OBSERVATION",
                "SYNTHETIC_MODEL_ROLLOUT",
            ],
            "lanes": [
                "offline_source",
                "online_target",
                "operational_query",
                "standalone_evaluation",
            ],
            "all_twenty_rows_materialized_including_native_zero": True,
            "replay_draws_gradient_updates_and_latency_reported_as_separate_compute_axes": True,
            "primary_sample_tax_axis": "online_target.ENVIRONMENT_INTERACTION",
            "shared_legal_action_mask_is_one_exact_kernel_query_per_explicit_mask_call": True,
            "environment_transition_internal_work_is_classified_as_the_environment_interaction_not_double_charged": True,
            "state_only_representation_adds_zero_exact_kernel_queries": True,
        },
        "outcome_metrics": {
            "primary": "heldout_episode_total_merge_score",
            "secondary": [
                "tile_2048_win_fraction",
                "maximum_tile_rank",
                "episode_decisions",
            ],
            "training_reward_is_not_substituted_for_heldout_outcome": True,
        },
        "claim_boundary": {
            "neural_representation_discovery_claimed": False,
            "cross_domain_transfer_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "total_operational_work_dominance_claimed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "official_execution_allowed": False,
            "scientific_success_claimed": False,
        },
    }


def _with_identity(payload: dict[str, Any]) -> dict[str, Any]:
    protocol_id = hashlib.sha256(
        PROTOCOL_DOMAIN.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


def build_pilot_protocol_v1() -> dict[str, Any]:
    """Return a nonconfirmatory implementation/calibration protocol."""

    payload = {
        **_common_payload(),
        "campaign_kind": "PILOT_NONCONFIRMATORY",
        "arms": ["RAW_BOARD", "RESOURCE_STATE_ONLY"],
        "training_seeds": [41001, 41002],
        "evaluation_tape_prefix": "acfqp-latent-resource-pilot-eval-v1",
        "training": _training_contract(
            environment_steps=20_000,
            checkpoints=(5_000, 10_000, 20_000),
            evaluation_episodes=8,
        ),
        "statistics_gate": "NOT_RUN_PILOT",
        "sample_efficiency_gate": "NOT_RUN_PILOT",
        "pilot_outcomes_may_change_confirmatory_budget_but_not_be_pooled": True,
    }
    return _with_identity(payload)


def build_confirmatory_template_v1() -> dict[str, Any]:
    """Return the frozen-shape template to ratify only after the pilot."""

    payload = {
        **_common_payload(),
        "campaign_kind": "CONFIRMATORY_TEMPLATE_NOT_YET_AUTHORIZED",
        "arms": list(ARMS),
        "training_seeds": list(range(730101, 730111)),
        "evaluation_tape_prefix": "acfqp-latent-resource-confirmatory-eval-v1",
        "training": _training_contract(
            environment_steps=500_000,
            checkpoints=(25_000, 50_000, 100_000, 200_000, 350_000, 500_000),
            evaluation_episodes=64,
        ),
        "statistics_gate": {
            "seed_count": 10,
            "summary": "MEAN_AND_SEM",
            "primary_test": "TWO_SIDED_WELCH_T_TEST",
            "alpha": {"numerator": 1, "denominator": 20},
            "effect_confidence_interval": "WELCH_95_PERCENT",
        },
        "joint_success_gate": {
            "reference_arm": "RAW_BOARD",
            "candidate_arm": "RESOURCE_STATE_ONLY",
            "performance_threshold": "99_PERCENT_OF_RAW_FINAL_MEAN_PRIMARY_OUTCOME",
            "candidate_earliest_threshold_interactions_strictly_less": True,
            "candidate_final_mean_primary_outcome_strictly_greater": True,
            "welch_two_sided_p_less_than_alpha": True,
            "welch_95_percent_difference_lower_bound_strictly_positive": True,
            "same_fixed_training_interaction_budget": True,
            "same_network_parameter_count": True,
            "decision_latency_and_compute_reported": True,
            "representation_compression_reported": True,
        },
        "authorization": "NOT_AUTHORIZED_UNTIL_PILOT_AND_CODE_FREEZE_COMPLETE",
    }
    return _with_identity(payload)


__all__ = (
    "ARMS",
    "LatentResourceProtocolV1Error",
    "PROTOCOL_DOMAIN",
    "build_confirmatory_template_v1",
    "build_pilot_protocol_v1",
)
