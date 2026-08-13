"""Run the preregistered long real-start V22 expression-model workload."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as target
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as pre
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_expression_long_campaign_v23"
EXPECTED_CAMPAIGN_ID = "cd198082b21cd1d6365f17081669bbdeac1172ac3da8247b68db4b649a3b0660"
EXPECTED_CANONICAL_BYTE_COUNT = 330447
EXPECTED_CANONICAL_SHA256 = "41fcecf933765a02e60213113cc71ec16d8c48b0b3339c40d3609bf0f195ee71"
MAXIMUM_PROCESSES = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/construction_k7_standard_2048_commit_reveal_target_kernel_v22.py",
    "src/acfqp/construction_k7_standard_2048_blind_expression_independent_verifier_v22.py",
    "src/acfqp/domains/standard_2048.py",
)


class ConstructionK7Standard2048ExpressionLongCampaignV23Error(ValueError):
    """A source binding, certificate, transition, or long claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionLongCampaignV23Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _source_binding() -> dict[str, Any]:
    rows = []
    for relative in SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        rows.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_expression_long_source_binding.v23",
        "schema_version": SCHEMA_VERSION,
        "expression_long_preregistration_id": pre.PREREGISTRATION_ID,
        "v22_campaign_id": pre.V22_CAMPAIGN_ID,
        "v22_independent_verification_id": pre.V22_VERIFICATION_ID,
        "v22_expression_proof_id": pre.V22_PROOF_ID,
        "v22_world_model_id": pre.V22_WORLD_MODEL_ID,
        "v22_target_kernel_id": pre.V22_TARGET_KERNEL_ID,
        "source_facts": rows,
        "expression_ast": {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 1,
        },
        "threshold": 2,
        "base_probability": Fraction(1, 10),
        "override_probability": Fraction(3, 20),
        "planning_horizon": pre.PLANNING_HORIZON,
        "persistent_subproof_cache_enabled": True,
        "target_probability_query_count_after_v22": 0,
        "binding_frozen_before_long_target_execution": True,
    }
    return {
        **payload,
        "expression_long_source_binding_id": content_id(
            pre.FUTURE_DOMAINS["source_binding"], payload
        ),
    }


def _episode(task: tuple[int, tuple[int, ...], str, dict[str, Any]]) -> dict[str, Any]:
    episode_index, initial_board, seed, binding = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state)
    session = planner.create_expression_planning_session_v1(
        expression_ast=binding["expression_ast"],
        threshold=binding["threshold"],
        base_probability=binding["base_probability"],
        override_probability=binding["override_probability"],
        horizon=binding["planning_horizon"],
    )
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = session.plan_root(state)
        certificate_payload = {
            "schema": "acfqp.standard_2048_expression_long_certificate.v23",
            "schema_version": SCHEMA_VERSION,
            "expression_long_preregistration_id": pre.PREREGISTRATION_ID,
            "expression_long_source_binding_id": binding[
                "expression_long_source_binding_id"
            ],
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": pre.PLANNING_HORIZON,
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model["selected_expected_merge_score"],
            "selected_loss_probability_within_horizon": model[
                "selected_loss_probability_within_horizon"
            ],
            "factored_action_row_evaluation_count": model[
                "factored_action_row_evaluation_count"
            ],
            "factored_support_outcome_evaluation_count": model[
                "factored_support_outcome_evaluation_count"
            ],
            "subproof_cache_hit_count": model["subproof_cache_hit_count"],
            "subproof_cache_miss_count": model["subproof_cache_miss_count"],
            "cross_decision_subproof_cache_hit_count": model[
                "cross_decision_subproof_cache_hit_count"
            ],
            "persistent_subproof_cache_entry_count": model[
                "persistent_subproof_cache_entry_count"
            ],
            "operational_target_probability_query_count": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_PERSISTENT_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "expression_long_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        cold = None
        if decision_index in pre.COLD_EVALUATION_CHECKPOINTS:
            cold = planner.evaluate_ground_root_v1(
                state,
                outcome_provider=target.target_outcomes_v22,
                horizon=pre.PLANNING_HORIZON,
            )
            if (
                cold["root_action_exact_values"] != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("long expression checkpoint differs from cold target ground")
        outcome, tape = select_seeded_outcome_v1(
            target.target_outcomes_v22(
                state, Swipe2048Action(model["selected_action"])
            ),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "PERSISTENT_EXPRESSION_WORLD_MODEL_CERTIFIED",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None or (
                    cold["root_action_exact_values"] == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": model["selected_action"],
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoint_rows = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    payload = {
        "schema": "acfqp.standard_2048_expression_long_episode.v23",
        "schema_version": SCHEMA_VERSION,
        "expression_long_preregistration_id": pre.PREREGISTRATION_ID,
        "expression_long_source_binding_id": binding[
            "expression_long_source_binding_id"
        ],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": pre.MAXIMUM_DECISIONS_PER_EPISODE,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_evaluation_checkpoint_count": len(checkpoint_rows),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoint_rows
        ),
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for row in decisions
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for row in decisions
        ),
        "subproof_cache_hit_count": sum(
            row["certificate"]["subproof_cache_hit_count"] for row in decisions
        ),
        "subproof_cache_miss_count": sum(
            row["certificate"]["subproof_cache_miss_count"] for row in decisions
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            row["certificate"]["cross_decision_subproof_cache_hit_count"]
            for row in decisions
        ),
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    return {
        **payload,
        "expression_long_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_expression_long_preregistration_v23()
    binding = _source_binding()
    tasks = tuple(
        (index, board, pre.EPISODE_SEEDS[index], binding)
        for index, board in enumerate(pre.INITIAL_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    checkpoints = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    payload = {
        "schema": "acfqp.standard_2048_expression_long_campaign.v23",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "expression_long_preregistration": preregistration.to_document(),
        "source_binding": binding,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "inherited_target_probability_label_count": 4,
        "additional_model_acquisition_label_count": 0,
        "strict_no_prior_context_label_count": 8,
        "target_label_difference_against_no_prior": 4,
        "inherited_label_fraction_of_no_prior": Fraction(1, 2),
        "certified_decisions_per_acquired_target_label": Fraction(
            len(decisions), 4
        ),
        "online_target_transition_observation_count": len(decisions),
        "factored_action_row_evaluation_count": sum(
            episode["factored_action_row_evaluation_count"] for episode in episodes
        ),
        "factored_support_outcome_evaluation_count": sum(
            episode["factored_support_outcome_evaluation_count"] for episode in episodes
        ),
        "subproof_cache_hit_count": sum(
            episode["subproof_cache_hit_count"] for episode in episodes
        ),
        "subproof_cache_miss_count": sum(
            episode["subproof_cache_miss_count"] for episode in episodes
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            episode["cross_decision_subproof_cache_hit_count"] for episode in episodes
        ),
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["cold_target_checkpoint"]["ground_state_action_row_count"]
            for row in checkpoints
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["cold_target_checkpoint"]["ground_outcome_count"]
            for row in checkpoints
        ),
        "persistent_subproof_cache_preserved_exact_values": True,
        "all_planning_performed_in_v22_expression_world_model": True,
        "operational_target_probability_query_count_during_long_planning": 0,
        "operational_ground_state_action_row_count_during_long_planning": 0,
        "sample_tax_outcome": (
            "POSITIVE_AMORTIZED_TARGET_LABEL_REUSE_OVER_LONG_REAL_START_WORKLOAD"
        ),
        "sample_tax_reduced_on_registered_target_label_axis": True,
        "proof_planning_execution_and_evaluation_axes_reported_separately": True,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(episode["tile_2048_reached"] for episode in episodes),
        "maximum_final_board_tile_rank": max(
            episode["maximum_final_board_tile_rank"] for episode in episodes
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "expression_long_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionLongCampaignV23:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("long expression campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("long expression campaign bytes changed")
        payload = {
            key: value for key, value in document.items()
            if key != "expression_long_campaign_id"
        }
        if (
            document.get("expression_long_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("long expression campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("long expression campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_expression_long_campaign_v23(
) -> Standard2048ExpressionLongCampaignV23:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["expression_long_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen long expression campaign outcome changed")
    return Standard2048ExpressionLongCampaignV23(
        _ISSUER, canonical_bytes, document["expression_long_campaign_id"]
    )


def verify_standard_2048_expression_long_campaign_v23(
    value: Standard2048ExpressionLongCampaignV23,
) -> Standard2048ExpressionLongCampaignV23:
    if type(value) is not Standard2048ExpressionLongCampaignV23:
        _fail("long expression campaign verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_expression_long_campaign_v23().canonical_bytes:
        _fail("long expression campaign differs from semantic replay")
    document = value.to_document()
    if (
        document["additional_model_acquisition_label_count"] != 0
        or document["all_checkpoint_root_values_and_actions_exactly_equal"] is not True
        or document["cross_decision_subproof_cache_hit_count"] <= 0
        or document["official_execution_allowed"] is not False
    ):
        _fail("long expression outcome or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048ExpressionLongCampaignV23Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048ExpressionLongCampaignV23",
    "run_standard_2048_expression_long_campaign_v23",
    "verify_standard_2048_expression_long_campaign_v23",
)
