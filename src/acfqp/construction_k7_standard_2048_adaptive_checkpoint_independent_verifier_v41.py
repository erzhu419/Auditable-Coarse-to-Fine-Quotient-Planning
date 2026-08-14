"""Producer-free exact replay of the V41 checkpoint continuation."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as v35verify
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35
from acfqp import construction_k7_standard_2048_adaptive_checkpoint_preregistration_v41 as pre
from acfqp.domains.standard_2048 import (
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
VERIFICATION_SCHEMA_VERSION = "41.0.0"
EXPECTED_CAMPAIGN_ID = "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
EXPECTED_VERIFICATION_ID = "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT = 1_602
EXPECTED_VERIFICATION_CANONICAL_SHA256 = "9e9808e081c5b2d0d65534e4d0a99618329060608e59bad48c5e856f923c4395"
MAXIMUM_CONCURRENT_VERIFICATION_PROCESSES = 2
EPISODES_PER_VERIFICATION_WAVE = 2
SOURCE_FACTS = [
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_adaptive_checkpoint_preregistration_v41.py",
        "byte_count": 13651,
        "sha256": "c0653aea51a85c8796e890a119b1a26c11142cb901be9e3e18ed28fc287a7962",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
        "byte_count": 15747,
        "sha256": "c2f06fcd78e41683544d243d23a4bdb5891b0523fbaa84ce771614c551f0aae2",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
        "byte_count": 3853,
        "sha256": "3cc08eb7c86008e236205f2a1f48dcd8189ebb97f7c210312794c0f703b4c17b",
    },
    {
        "relative_path": "src/acfqp/domains/standard_2048.py",
        "byte_count": 14739,
        "sha256": "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c",
    },
]


class ConstructionK7Standard2048AdaptiveCheckpointIndependentVerifierV41Error(
    ValueError
):
    """The checkpoint campaign differs from producer-free exact replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveCheckpointIndependentVerifierV41Error(
        message
    )


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state(document: Any) -> Any:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("checkpoint state shape changed")
    state = state_from_board_v1(tuple(document["board_ranks"]))
    if state.status.value != document["status"]:
        _fail("checkpoint state status changed")
    return state


def _binding_expected() -> dict[str, Any]:
    return {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_source_binding.v41",
        "schema_version": SCHEMA_VERSION,
        "adaptive_checkpoint_preregistration_id": pre.PREREGISTRATION_ID,
        "v35_adaptive_expression_campaign_id": pre.V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": pre.V35_VERIFICATION_ID,
        "v36r4_accounted_campaign_id": pre.V36R4_CAMPAIGN_ID,
        "v36r4_accounting_verification_id": pre.V36R4_VERIFICATION_ID,
        "v40_adaptive_checkpoint_preregistration_id": pre.V40_PREREGISTRATION_ID,
        "v40_adaptive_checkpoint_campaign_id": pre.V40_CAMPAIGN_ID,
        "v40_adaptive_checkpoint_verification_id": pre.V40_VERIFICATION_ID,
        "adaptive_expression_overlay_id": pre.ADAPTIVE_EXPRESSION_OVERLAY_ID,
        "adaptive_expression_proof_id": pre.ADAPTIVE_EXPRESSION_PROOF_ID,
        "adaptive_expression_candidate_id": pre.ADAPTIVE_EXPRESSION_CANDIDATE_ID,
        "target_kernel_id": pre.TARGET_KERNEL_ID,
        "source_facts": SOURCE_FACTS,
        "expression_ast": {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 2,
        },
        "direction": "LE_OVERRIDE",
        "threshold": 1,
        "base_probability": Fraction(1, 10),
        "override_probability": Fraction(1, 4),
        "planning_horizon": 3,
        "empty_cache_at_checkpoint_start": True,
        "persistent_cache_within_segment": True,
        "target_probability_query_count_in_segment": 0,
        "binding_frozen_before_checkpoint_target_execution": True,
        "maximum_concurrent_worker_processes": 2,
        "execution_wave_count": 2,
        "episode_tasks_per_wave": 2,
        "fresh_executor_for_each_wave": True,
        "same_resource_schedule_as_verified_v40": True,
    }


def _candidate() -> tuple[str, dict[str, Any], int, Fraction, str]:
    return (
        pre.ADAPTIVE_EXPRESSION_CANDIDATE_ID,
        {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 2,
        },
        1,
        Fraction(1, 4),
        "LE_OVERRIDE",
    )


def _verify_episode(task: tuple[int, dict[str, Any]]) -> dict[str, int]:
    episode_index, episode = task
    _verify_id(
        episode,
        "adaptive_checkpoint_episode_id",
        pre.FUTURE_DOMAINS["episode"],
        "checkpoint episode",
    )
    state = state_from_board_v1(pre.CHECKPOINT_BOARDS[episode_index])
    if (
        episode.get("episode_index") != episode_index
        or episode.get("source_episode_id") != pre.CHECKPOINT_EPISODE_IDS[episode_index]
        or episode.get("execution_seed") != v35.EPISODE_SEEDS[episode_index]
        or episode.get("adaptive_expression_overlay_id")
        != pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
        or episode.get("adaptive_expression_proof_id")
        != pre.ADAPTIVE_EXPRESSION_PROOF_ID
        or _state(episode.get("initial_state")) != state
    ):
        _fail("checkpoint episode predecessor binding changed")
    rows = episode.get("decisions")
    if (
        type(rows) is not list
        or not rows
        or len(rows) > pre.SEGMENT_DECISION_LIMIT
    ):
        _fail("checkpoint decision inventory changed")
    planning = v35verify._PersistentPlanner(_candidate())  # noqa: SLF001
    totals = {
        "rows": 0,
        "outcomes": 0,
        "hits": 0,
        "misses": 0,
        "cross": 0,
        "checkpoints": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
    }
    for local_index, decision in enumerate(rows):
        global_index = pre.GLOBAL_DECISION_START + local_index
        replay = planning.plan_root(state)
        certificate = _verify_id(
            decision.get("certificate"),
            "adaptive_checkpoint_certificate_id",
            pre.FUTURE_DOMAINS["certificate"],
            "checkpoint certificate",
        )
        if (
            decision.get("local_decision_index") != local_index
            or decision.get("global_decision_index") != global_index
            or _state(decision.get("predecision_state")) != state
            or certificate.get("source_episode_id") != pre.CHECKPOINT_EPISODE_IDS[episode_index]
            or certificate.get("adaptive_expression_overlay_id")
            != pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
            or certificate.get("adaptive_expression_proof_id")
            != pre.ADAPTIVE_EXPRESSION_PROOF_ID
            or certificate.get("root_action_exact_values") != replay["root_action_exact_values"]
            or certificate.get("selected_action") != replay["selected_action"]
            or certificate.get("selected_expected_merge_score") != replay["selected_expected_merge_score"]
            or certificate.get("selected_loss_probability_within_horizon") != replay["selected_loss_probability_within_horizon"]
            or certificate.get("factored_action_row_evaluation_count")
            != replay["factored_action_row_evaluation_count"]
            or certificate.get("factored_support_outcome_evaluation_count")
            != replay["factored_support_outcome_evaluation_count"]
            or certificate.get("subproof_cache_hit_count")
            != replay["subproof_cache_hit_count"]
            or certificate.get("subproof_cache_miss_count")
            != replay["subproof_cache_miss_count"]
            or certificate.get("cross_decision_subproof_cache_hit_count")
            != replay["cross_decision_subproof_cache_hit_count"]
            or certificate.get("persistent_subproof_cache_entry_count")
            != replay["persistent_subproof_cache_entry_count"]
            or certificate.get("operational_target_probability_query_count") != 0
            or certificate.get("operational_ground_state_action_row_count") != 0
            or certificate.get("status")
            != "CERTIFIED_CHECKPOINT_PROVED_ADAPTIVE_EXPRESSION_MODEL_H3"
        ):
            _fail("checkpoint certificate differs from exact independent replay")
        cold = decision.get("cold_target_checkpoint")
        if local_index in pre.LOCAL_COLD_CHECKPOINTS:
            expected = v35verify._GroundPlanner().root(state)  # noqa: SLF001
            if cold != expected:
                _fail("checkpoint cold target differs from independent replay")
            totals["checkpoints"] += 1
            totals["evaluation_rows"] += expected["ground_state_action_row_count"]
            totals["evaluation_outcomes"] += expected["ground_outcome_count"]
        elif cold is not None:
            _fail("unregistered checkpoint cold target appeared")
        outcomes = v35verify._target_outcomes(  # noqa: SLF001
            state, Swipe2048Action(replay["selected_action"])
        )
        outcome, tape = select_seeded_outcome_v1(
            outcomes,
            seed=v35.EPISODE_SEEDS[episode_index],
            decision_index=global_index,
        )
        if (
            decision.get("route")
            != "CHECKPOINT_PROVED_ADAPTIVE_EXPRESSION_WORLD_MODEL_CERTIFIED"
            or decision.get("executed_action") != replay["selected_action"]
            or decision.get("execution_tape_sha256") != tape
            or _state(decision.get("executed_next_state")) != outcome.next_state
            or decision.get("checkpoint_root_values_and_action_exactly_equal") is not True
            or decision.get("certificate_frozen_before_cold_checkpoint_and_target_transition") is not True
            or decision.get("online_target_transition_observation_count") != 1
            or decision.get("execution_transition_used_to_modify_world_model") is not False
        ):
            _fail("checkpoint transition differs from independent replay")
        state = outcome.next_state
        totals["rows"] += replay["factored_action_row_evaluation_count"]
        totals["outcomes"] += replay["factored_support_outcome_evaluation_count"]
        totals["hits"] += replay["subproof_cache_hit_count"]
        totals["misses"] += replay["subproof_cache_miss_count"]
        totals["cross"] += replay["cross_decision_subproof_cache_hit_count"]
    if (
        _state(episode.get("final_state")) != state
        or episode.get("global_decision_start_inclusive") != pre.GLOBAL_DECISION_START
        or episode.get("segment_decision_count") != len(rows)
        or episode.get("cumulative_decision_count")
        != pre.SOURCE_DECISION_COUNT + len(rows)
        or episode.get("model_certificate_count") != len(rows)
        or episode.get("local_ground_recovery_count") != 0
        or episode.get("additional_model_acquisition_label_count") != 0
        or episode.get("cold_evaluation_checkpoint_count") != totals["checkpoints"]
        or episode.get("all_checkpoint_root_values_and_actions_exactly_equal") is not True
        or episode.get("factored_action_row_evaluation_count") != totals["rows"]
        or episode.get("factored_support_outcome_evaluation_count") != totals["outcomes"]
        or episode.get("subproof_cache_hit_count") != totals["hits"]
        or episode.get("subproof_cache_miss_count") != totals["misses"]
        or episode.get("cross_decision_subproof_cache_hit_count") != totals["cross"]
        or episode.get("maximum_final_board_tile_rank") != max(state.board)
        or episode.get("tile_2048_reached") is not (max(state.board) >= GOAL_RANK)
        or episode.get("closure_reason")
        != (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_CHECKPOINT_LIMIT"
        )
    ):
        _fail("checkpoint episode aggregate changed")
    return totals


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveCheckpointIndependentVerificationV41:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("checkpoint verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("checkpoint verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_checkpoint_verification_id"
        }
        if (
            document.get("adaptive_checkpoint_verification_id")
            != self.verification_id
            or document.get("adaptive_checkpoint_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["verification"], payload)
            != self.verification_id
        ):
            _fail("checkpoint verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("checkpoint verification is not an object")
        return document


def verify_standard_2048_adaptive_checkpoint_bytes_independently_v41(
    campaign_bytes: bytes,
) -> Standard2048AdaptiveCheckpointIndependentVerificationV41:
    try:
        campaign = loads_canonical_json(campaign_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AdaptiveCheckpointIndependentVerifierV41Error(
            "checkpoint campaign is not canonical"
        ) from error
    if type(campaign) is not dict or canonical_json_bytes(campaign) != campaign_bytes:
        _fail("checkpoint campaign canonical bytes changed")
    _verify_id(
        campaign,
        "adaptive_checkpoint_campaign_id",
        pre.FUTURE_DOMAINS["campaign"],
        "checkpoint campaign",
    )
    campaign_id = campaign["adaptive_checkpoint_campaign_id"]
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and campaign_id != EXPECTED_CAMPAIGN_ID:
        _fail("frozen checkpoint campaign identity changed")
    if campaign.get("adaptive_checkpoint_preregistration") != pre.freeze_standard_2048_adaptive_checkpoint_preregistration_v41().to_document():
        _fail("checkpoint preregistration binding changed")
    if campaign.get("source_binding") != _binding_expected():
        _fail("checkpoint source binding changed")
    if campaign.get("execution_resource_schedule") != {
        "v40_adaptive_checkpoint_verification_id": pre.V40_VERIFICATION_ID,
        "maximum_concurrent_worker_processes": 2,
        "execution_wave_count": 2,
        "episode_tasks_per_wave": 2,
        "fresh_executor_used_for_each_wave": True,
        "maximum_tasks_per_worker_process": 1,
        "same_resource_schedule_as_verified_v40": True,
    }:
        _fail("checkpoint execution resource schedule changed")
    episodes = campaign.get("episodes")
    if type(episodes) is not list or len(episodes) != 4:
        _fail("checkpoint episode inventory changed")
    totals = []
    for wave_start in range(0, len(episodes), EPISODES_PER_VERIFICATION_WAVE):
        wave_stop = min(
            wave_start + EPISODES_PER_VERIFICATION_WAVE, len(episodes)
        )
        with ProcessPoolExecutor(
            max_workers=MAXIMUM_CONCURRENT_VERIFICATION_PROCESSES
        ) as executor:
            totals.extend(
                executor.map(
                    _verify_episode,
                    (
                        (index, episodes[index])
                        for index in range(wave_start, wave_stop)
                    ),
                    chunksize=1,
                )
            )
    aggregate = {
        key: sum(row[key] for row in totals)
        for key in (
            "rows",
            "outcomes",
            "hits",
            "misses",
            "cross",
            "checkpoints",
            "evaluation_rows",
            "evaluation_outcomes",
        )
    }
    decision_count = sum(len(episode["decisions"]) for episode in episodes)
    cumulative_count = (
        len(pre.CHECKPOINT_BOARDS) * pre.SOURCE_DECISION_COUNT + decision_count
    )
    if (
        campaign.get("episode_count") != 4
        or campaign.get("segment_decision_count") != decision_count
        or campaign.get("cumulative_decision_count_across_episodes")
        != cumulative_count
        or campaign.get("model_certificate_count") != decision_count
        or campaign.get("local_ground_recovery_count") != 0
        or campaign.get("cold_evaluation_checkpoint_count")
        != aggregate["checkpoints"]
        or campaign.get("all_checkpoint_root_values_and_actions_exactly_equal")
        is not True
        or campaign.get("inherited_target_probability_label_count")
        != pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT
        or campaign.get("additional_model_acquisition_label_count") != 0
        or campaign.get("strict_no_prior_context_label_count")
        != pre.STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT
        or campaign.get("inherited_label_fraction_of_no_prior")
        != Fraction(1, 400)
        or campaign.get("cumulative_certified_decisions_per_acquired_target_label")
        != Fraction(cumulative_count, pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT)
        or campaign.get("factored_action_row_evaluation_count") != aggregate["rows"]
        or campaign.get("factored_support_outcome_evaluation_count") != aggregate["outcomes"]
        or campaign.get("subproof_cache_hit_count") != aggregate["hits"]
        or campaign.get("subproof_cache_miss_count") != aggregate["misses"]
        or campaign.get("cross_decision_subproof_cache_hit_count") != aggregate["cross"]
        or campaign.get("evaluation_cold_target_ground_state_action_row_count")
        != aggregate["evaluation_rows"]
        or campaign.get("evaluation_cold_target_ground_outcome_count")
        != aggregate["evaluation_outcomes"]
        or campaign.get("online_target_transition_observation_count")
        != decision_count
        or campaign.get("exact_cache_checkpoint_reset_preserved_values_and_actions") is not True
        or campaign.get("all_segment_planning_performed_in_expression_world_model") is not True
        or campaign.get("all_segment_planning_bound_to_v35_proof_and_overlay")
        is not True
        or campaign.get("operational_target_probability_query_count_in_segment") != 0
        or campaign.get("operational_ground_state_action_row_count_in_segment") != 0
        or campaign.get("registered_label_axis_sample_tax_reduction_preserved") is not True
        or campaign.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or campaign.get("total_operational_work_saving_claimed") is not False
        or campaign.get("full_standard_2048_game_completed")
        != all(episode["closure_reason"] == "TERMINAL_STATE" for episode in episodes)
        or campaign.get("tile_2048_reached")
        != any(episode["tile_2048_reached"] for episode in episodes)
        or campaign.get("maximum_final_board_tile_rank")
        != max(episode["maximum_final_board_tile_rank"] for episode in episodes)
        or campaign.get("official_execution_allowed") is not False
        or campaign.get("official_scalar_cost") is not None
        or campaign.get("official_N_break_even") is not None
        or campaign.get("counter_completeness_gate_status") != "NOT_RUN"
        or campaign.get("workload_economics_gate_status") != "NOT_RUN"
    ):
        _fail("checkpoint campaign aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_independent_verification.v41",
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "adaptive_checkpoint_preregistration_id": pre.PREREGISTRATION_ID,
        "adaptive_checkpoint_campaign_id": campaign_id,
        "producer_module_imported": False,
        "retained_campaign_bytes_replayed": True,
        "verification_resource_schedule": {
            "maximum_concurrent_worker_processes": (
                MAXIMUM_CONCURRENT_VERIFICATION_PROCESSES
            ),
            "execution_wave_count": 2,
            "episode_tasks_per_wave": EPISODES_PER_VERIFICATION_WAVE,
            "fresh_executor_used_for_each_wave": True,
        },
        "verified_v40_predecessor_and_resource_schedule_reused": True,
        "replayed_checkpoint_h3_certificate_count": decision_count,
        "all_checkpoint_h3_certificates_independently_replayed": True,
        "replayed_global_index_seeded_transition_count": decision_count,
        "all_global_index_seeded_transitions_independently_replayed": True,
        "replayed_cold_target_checkpoint_count": aggregate["checkpoints"],
        "all_registered_cold_target_checkpoints_independently_replayed": True,
        "cache_reset_exact_value_invariance_verified": True,
        "zero_additional_model_labels_verified": True,
        "six_labels_amortized_over_cumulative_certificates": Fraction(
            cumulative_count, pre.INHERITED_TARGET_PROBABILITY_LABEL_COUNT
        ),
        "v35_proof_and_overlay_binding_verified": True,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_completion_verified": bool(
            campaign.get("full_standard_2048_game_completed")
        ),
        "tile_2048_reached_verified": bool(campaign.get("tile_2048_reached")),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(pre.FUTURE_DOMAINS["verification"], payload)
    raw = canonical_json_bytes(
        {**payload, "adaptive_checkpoint_verification_id": verification_id}
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen checkpoint verification identity changed")
    if EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT and (
        len(raw) != EXPECTED_VERIFICATION_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_VERIFICATION_CANONICAL_SHA256
    ):
        _fail("frozen checkpoint verification bytes changed")
    return Standard2048AdaptiveCheckpointIndependentVerificationV41(
        _ISSUER, raw, verification_id, campaign_id
    )


__all__ = (
    "EXPECTED_VERIFICATION_ID",
    "Standard2048AdaptiveCheckpointIndependentVerificationV41",
    "verify_standard_2048_adaptive_checkpoint_bytes_independently_v41",
)
