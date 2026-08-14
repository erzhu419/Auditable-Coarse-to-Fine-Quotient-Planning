"""Resource-bounded successor for the failed four-worker V38 continuation."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35
from acfqp import construction_k7_standard_2048_adaptive_expression_target_v35 as target
from acfqp import construction_k7_standard_2048_adaptive_checkpoint_preregistration_v39 as pre
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_adaptive_checkpoint_campaign_v39"
EXPECTED_CAMPAIGN_ID = "a904911478f4202734f8ba6aa2cebd57f36c5626e80bc278241469309bb6dccb"
EXPECTED_CANONICAL_BYTE_COUNT = 2_747_305
EXPECTED_CANONICAL_SHA256 = "b3c22a22f59817cb9a6a3484977a6d071040a29369a127e6e54f5755712b3a72"
MAXIMUM_PROCESSES = 2
TASKS_PER_WAVE = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/acfqp/construction_k7_standard_2048_adaptive_checkpoint_preregistration_v39.py",
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
    "src/acfqp/domains/standard_2048.py",
)


class ConstructionK7Standard2048AdaptiveCheckpointCampaignV39Error(ValueError):
    """The predecessor, checkpoint plan, transition, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveCheckpointCampaignV39Error(message)


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _source_binding() -> dict[str, Any]:
    source_facts = []
    for relative in SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        source_facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_source_binding.v39",
        "schema_version": SCHEMA_VERSION,
        "adaptive_checkpoint_preregistration_id": pre.PREREGISTRATION_ID,
        "v35_adaptive_expression_campaign_id": pre.V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": pre.V35_VERIFICATION_ID,
        "v36r4_accounted_campaign_id": pre.V36R4_CAMPAIGN_ID,
        "v36r4_accounting_verification_id": pre.V36R4_VERIFICATION_ID,
        "v37_adaptive_checkpoint_preregistration_id": pre.V37_PREREGISTRATION_ID,
        "v37_adaptive_checkpoint_campaign_id": pre.V37_CAMPAIGN_ID,
        "v37_adaptive_checkpoint_verification_id": pre.V37_VERIFICATION_ID,
        "failed_v38_adaptive_checkpoint_preregistration_id": (
            pre.FAILED_V38_PREREGISTRATION_ID
        ),
        "failed_v38_runner_source_byte_count": (
            pre.FAILED_V38_RUNNER_SOURCE_BYTE_COUNT
        ),
        "failed_v38_runner_source_sha256": pre.FAILED_V38_RUNNER_SOURCE_SHA256,
        "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        "adaptive_expression_candidate_id": pre.ADAPTIVE_EXPRESSION_CANDIDATE_ID,
        "target_kernel_id": pre.TARGET_KERNEL_ID,
        "source_facts": source_facts,
        "expression_ast": {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 2,
        },
        "direction": "LE_OVERRIDE",
        "threshold": 1,
        "base_probability": Fraction(1, 10),
        "override_probability": Fraction(1, 4),
        "planning_horizon": pre.PLANNING_HORIZON,
        "empty_cache_at_checkpoint_start": True,
        "persistent_cache_within_segment": True,
        "target_probability_query_count_in_segment": 0,
        "binding_frozen_before_checkpoint_target_execution": True,
        "maximum_concurrent_worker_processes": MAXIMUM_PROCESSES,
        "execution_wave_count": 2,
        "episode_tasks_per_wave": TASKS_PER_WAVE,
        "fresh_executor_for_each_wave": True,
        "failed_v38_partial_outputs_reused": False,
    }


def _episode(task: tuple[int, dict[str, Any]]) -> dict[str, Any]:
    episode_index, binding = task
    state = state_from_board_v1(pre.CHECKPOINT_BOARDS[episode_index])
    initial = _state_document(state)
    session = planner.create_expression_planning_session_v1(
        expression_ast=binding["expression_ast"],
        threshold=binding["threshold"],
        base_probability=binding["base_probability"],
        override_probability=binding["override_probability"],
        horizon=binding["planning_horizon"],
    )
    decisions = []
    for local_index in range(pre.SEGMENT_DECISION_LIMIT):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        global_index = pre.GLOBAL_DECISION_START + local_index
        model = session.plan_root(state)
        if model.get("target_transition_accessed") is not False:
            _fail("checkpoint planner accessed target before certificate")
        certificate_payload = {
            "schema": "acfqp.standard_2048_adaptive_checkpoint_certificate.v39",
            "schema_version": SCHEMA_VERSION,
            "adaptive_checkpoint_preregistration_id": pre.PREREGISTRATION_ID,
            "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
            "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
            "source_episode_id": pre.CHECKPOINT_EPISODE_IDS[episode_index],
            "episode_index": episode_index,
            "local_decision_index": local_index,
            "global_decision_index": global_index,
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
            "status": "CERTIFIED_CHECKPOINT_PROVED_ADAPTIVE_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "adaptive_checkpoint_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        cold = None
        if local_index in pre.LOCAL_COLD_CHECKPOINTS:
            cold = planner.evaluate_ground_root_v1(
                state,
                outcome_provider=target.target_outcomes_v35,
                horizon=pre.PLANNING_HORIZON,
            )
            if (
                cold["root_action_exact_values"] != model["root_action_exact_values"]
                or cold["selected_action"] != model["selected_action"]
            ):
                _fail("checkpoint cold target differs from expression model")
        selected = Swipe2048Action(model["selected_action"])
        outcome, tape = select_seeded_outcome_v1(
            target.target_outcomes_v35(state, selected),
            seed=v35.EPISODE_SEEDS[episode_index],
            decision_index=global_index,
        )
        decisions.append(
            {
                "local_decision_index": local_index,
                "global_decision_index": global_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "CHECKPOINT_PROVED_ADAPTIVE_EXPRESSION_WORLD_MODEL_CERTIFIED",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None
                or (
                    cold["root_action_exact_values"]
                    == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": selected.value,
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoints = [row for row in decisions if row["cold_target_checkpoint"] is not None]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_episode.v39",
        "schema_version": SCHEMA_VERSION,
        "adaptive_checkpoint_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        "source_episode_id": pre.CHECKPOINT_EPISODE_IDS[episode_index],
        "episode_index": episode_index,
        "execution_seed": v35.EPISODE_SEEDS[episode_index],
        "global_decision_start_inclusive": pre.GLOBAL_DECISION_START,
        "initial_state": initial,
        "decisions": decisions,
        "segment_decision_count": len(decisions),
        "cumulative_decision_count": pre.SOURCE_DECISION_COUNT + len(decisions),
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_CHECKPOINT_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "additional_model_acquisition_label_count": 0,
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
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
        "adaptive_checkpoint_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.verify_standard_2048_adaptive_checkpoint_preregistration_v39(
        pre.freeze_standard_2048_adaptive_checkpoint_preregistration_v39()
    )
    binding = _source_binding()
    episodes = []
    for wave_start in range(0, len(pre.CHECKPOINT_BOARDS), TASKS_PER_WAVE):
        wave_stop = min(wave_start + TASKS_PER_WAVE, len(pre.CHECKPOINT_BOARDS))
        with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
            episodes.extend(
                executor.map(
                    _episode,
                    ((index, binding) for index in range(wave_start, wave_stop)),
                    chunksize=1,
                )
            )
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    checkpoints = [row for row in decisions if row["cold_target_checkpoint"] is not None]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_campaign.v39",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "adaptive_checkpoint_preregistration": preregistration.to_document(),
        "source_binding": binding,
        "resource_successor_execution": {
            "failed_v38_preregistration_id": pre.FAILED_V38_PREREGISTRATION_ID,
            "maximum_concurrent_worker_processes": MAXIMUM_PROCESSES,
            "execution_wave_count": 2,
            "episode_tasks_per_wave": TASKS_PER_WAVE,
            "fresh_executor_used_for_each_wave": True,
            "failed_v38_partial_outputs_reused": False,
            "scientific_workload_changed_from_v38": False,
        },
        "episodes": episodes,
        "episode_count": len(episodes),
        "segment_decision_count": len(decisions),
        "cumulative_decision_count_across_episodes": (
            len(pre.CHECKPOINT_BOARDS) * pre.SOURCE_DECISION_COUNT + len(decisions)
        ),
        "model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "inherited_target_probability_label_count": pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
        "additional_model_acquisition_label_count": 0,
        "strict_no_prior_context_label_count": pre.STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT,
        "inherited_label_fraction_of_no_prior": Fraction(1, 400),
        "cumulative_certified_decisions_per_acquired_target_label": Fraction(
            len(pre.CHECKPOINT_BOARDS) * pre.SOURCE_DECISION_COUNT + len(decisions),
            pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
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
        "exact_cache_checkpoint_reset_preserved_values_and_actions": True,
        "all_segment_planning_performed_in_expression_world_model": True,
        "all_segment_planning_bound_to_v35_proof_and_overlay": True,
        "operational_target_probability_query_count_in_segment": 0,
        "operational_ground_state_action_row_count_in_segment": 0,
        "registered_label_axis_sample_tax_reduction_preserved": True,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": all(
            episode["closure_reason"] == "TERMINAL_STATE" for episode in episodes
        ),
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
        "adaptive_checkpoint_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveCheckpointCampaignV39:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("checkpoint campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("checkpoint campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_checkpoint_campaign_id"
        }
        if (
            document.get("adaptive_checkpoint_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("checkpoint campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("checkpoint campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_adaptive_checkpoint_campaign_v39(
) -> Standard2048AdaptiveCheckpointCampaignV39:
    document = _campaign_document()
    raw = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["adaptive_checkpoint_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint campaign outcome changed")
    return Standard2048AdaptiveCheckpointCampaignV39(
        _ISSUER, raw, document["adaptive_checkpoint_campaign_id"]
    )


def verify_standard_2048_adaptive_checkpoint_campaign_v39(
    value: Standard2048AdaptiveCheckpointCampaignV39,
) -> Standard2048AdaptiveCheckpointCampaignV39:
    if type(value) is not Standard2048AdaptiveCheckpointCampaignV39:
        _fail("checkpoint campaign verifier rejects foreign values")
    value.__post_init__()
    return value


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048AdaptiveCheckpointCampaignV39",
    "run_standard_2048_adaptive_checkpoint_campaign_v39",
    "verify_standard_2048_adaptive_checkpoint_campaign_v39",
)
