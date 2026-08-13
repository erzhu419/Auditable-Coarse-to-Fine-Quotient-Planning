"""Outcome-free Gate for planning entirely in the synthesized 2048 model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CERTIFICATE_V17_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_EPISODE_V17_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_PREREGISTRATION_V17_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "17.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.176"
PROFILE_KEY = "construction_k7_standard_2048_synthesized_model_planning_v17"
PREREGISTRATION_ID = "b2904f79fa0dc9dc843f8674a91197798e3c9e3b18c96cdedf5d5513be7cb268"
V16_SPAWN_PREREGISTRATION_ID = "9b868b003846c0ad0a966537922ef621ab5c1166533b00cfb02187d78399300a"
V16_SPAWN_CAMPAIGN_ID = "c6d490d140676a9d045e678f1484635d925a655f4c67605afde28690e246aa53"
V16_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
V16_INDEPENDENT_VERIFICATION_ID = "a6fa6e31d8ee765e4a6c352384baed87ef7a38bba58af7590b85b666e94a8198"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS_PER_EPISODE = 32
TARGET_INITIAL_BOARDS = (
    (2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v176-synthesized-plan-target-{index:02d}-20260813"
    for index in range(4)
)
FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_PREREGISTRATION_V17_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CERTIFICATE_V17_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_EPISODE_V17_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN,
}


class ConstructionK7Standard2048SynthesizedPlanPreregistrationV17Error(ValueError):
    """World-model identity, fresh workload, route, or Gate changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SynthesizedPlanPreregistrationV17Error(message)


def _canonical_orbits() -> tuple[tuple[int, ...], ...]:
    return tuple(
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in TARGET_INITIAL_BOARDS
    )


def _document() -> dict[str, Any]:
    orbits = _canonical_orbits()
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_preregistration.v17",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "v16_spawn_program_preregistration_id": V16_SPAWN_PREREGISTRATION_ID,
        "v16_spawn_program_campaign_id": V16_SPAWN_CAMPAIGN_ID,
        "v16_synthesized_world_model_id": V16_WORLD_MODEL_ID,
        "v16_independent_verification_id": V16_INDEPENDENT_VERIFICATION_ID,
        "v16_result_frozen_before_v17_target_execution": True,
        "v17_target_or_route_outcomes_read_before_freeze": False,
        "model_contract": {
            "swipe_component": "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM_V14",
            "spawn_component": "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM_V16",
            "full_state_action_table_present": False,
            "factored_successor_generation": True,
            "exact_rational_probability_arithmetic": True,
            "d4_subproof_memoization_allowed": True,
            "model_identity_reused_across_all_decisions_and_episodes": True,
            "ground_kernel_access_before_certificate_failure": False,
        },
        "certificate_protocol": {
            "planning_horizon": PLANNING_HORIZON,
            "certificate_kind": "EXACT_SYNTHESIZED_FACTORED_H3_BELLMAN_OPTIMALITY",
            "selection_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
            "certificate_frozen_before_target_transition": True,
            "source_closed_ground_step_used_by_certificate": False,
            "matched_direct_used_by_certificate": False,
            "local_ground_recovery_only_after_certificate_failure": True,
            "rank_scope": [0, 19],
            "out_of_scope_or_identity_failure_route": "COLD_EXACT_GROUND_FALLBACK",
        },
        "target_workload": {
            "initial_boards": [list(board) for board in TARGET_INITIAL_BOARDS],
            "initial_board_d4_representatives": [list(board) for board in orbits],
            "all_target_orbits_distinct": len(set(orbits)) == len(orbits),
            "episode_seeds": list(TARGET_SEEDS),
            "episode_count": len(TARGET_INITIAL_BOARDS),
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": (
                len(TARGET_INITIAL_BOARDS) * MAXIMUM_DECISIONS_PER_EPISODE
            ),
            "early_won_or_lost_terminal_closure_allowed": True,
        },
        "matched_direct_control": {
            "cold_exact_ground_h3_at_every_decision": True,
            "standalone_evaluation_lane_only": True,
            "route_or_certificate_authority": False,
            "all_root_action_exact_value_and_loss_equality_required": True,
            "all_selected_action_equality_required": True,
        },
        "sample_tax_accounting": {
            "joint_model_synthesis_transition_observation_count": 1152,
            "additional_model_acquisition_observation_budget": 0,
            "matched_fixed_observation_control_count": 8192,
            "registered_offline_observation_difference": 7040,
            "online_target_transitions_reported_separately": True,
            "program_proof_compute_reported_separately": True,
            "factored_and_ground_compute_reported_separately": True,
            "positive_result_requires_all_exact_control_equalities": True,
            "broad_or_physical_iid_sample_efficiency_claimed": False,
            "total_operational_work_saving_claimed": False,
        },
        "outcome_fields_present": False,
        "target_execution_performed": False,
        "synthesized_model_certificate_count": 0,
        "local_ground_recovery_count": 0,
        "sample_tax_reduction_claimed": False,
        "full_standard_2048_game_claimed": False,
        "tile_2048_reached": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "synthesized_plan_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SynthesizedPlanPreregistrationV17:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("synthesized-plan preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("synthesized-plan preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "synthesized_plan_preregistration_id"
        }
        if (
            document.get("synthesized_plan_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("synthesized-plan preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("synthesized-plan preregistration is not an object")
        return document


def freeze_standard_2048_synthesized_plan_preregistration_v17(
) -> Standard2048SynthesizedPlanPreregistrationV17:
    document = _document()
    if document["synthesized_plan_preregistration_id"] != PREREGISTRATION_ID:
        _fail("frozen synthesized-plan preregistration identity changed")
    return Standard2048SynthesizedPlanPreregistrationV17(
        _ISSUER,
        canonical_json_bytes(document),
        document["synthesized_plan_preregistration_id"],
    )


def verify_standard_2048_synthesized_plan_preregistration_v17(
    value: Standard2048SynthesizedPlanPreregistrationV17,
) -> Standard2048SynthesizedPlanPreregistrationV17:
    if type(value) is not Standard2048SynthesizedPlanPreregistrationV17:
        _fail("synthesized-plan preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("synthesized-plan preregistration differs from frozen semantics")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNING_HORIZON",
    "PREREGISTRATION_ID",
    "Standard2048SynthesizedPlanPreregistrationV17",
    "TARGET_INITIAL_BOARDS",
    "TARGET_SEEDS",
    "freeze_standard_2048_synthesized_plan_preregistration_v17",
    "verify_standard_2048_synthesized_plan_preregistration_v17",
)
