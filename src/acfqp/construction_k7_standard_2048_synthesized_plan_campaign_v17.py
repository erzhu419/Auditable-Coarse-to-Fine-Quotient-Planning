"""Fresh H=3 planning using only the observation-synthesized 2048 model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
from acfqp import construction_k7_standard_2048_spawn_program_v16 as spawn_v16
from acfqp import construction_k7_standard_2048_synthesized_plan_preregistration_v17 as pre
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_synthesized_plan_campaign_v17"
MAXIMUM_PROCESSES = 4
EXPECTED_CAMPAIGN_ID = "ef411b84bb88d8084bf9a4b9f65be6200a8459a1e26394a96cc5fa38aeba496e"
EXPECTED_CANONICAL_BYTE_COUNT = 464420
EXPECTED_CANONICAL_SHA256 = "a6048a9e1f9ce909f2262a7c39b94de05364f6cda83bea24fb58c06ec9864915"
EXPECTED_FACTORED_ACTION_ROW_COUNT = 718242
EXPECTED_FACTORED_SUPPORT_OUTCOME_COUNT = 14711528


class ConstructionK7Standard2048SynthesizedPlanCampaignV17Error(ValueError):
    """The synthesized planner, exact control, target, or claims changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SynthesizedPlanCampaignV17Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _canonical(board: tuple[int, ...]) -> tuple[int, ...]:
    candidates = []
    for transform in D4_ELEMENTS:
        result = [0] * 16
        for source, rank in enumerate(board):
            result[transform_cell(source, 4, transform)] = rank
        candidates.append(tuple(result))
    return min(candidates)


@lru_cache(maxsize=None)
def _swipe(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return swipe_v14.apply_observation_proposed_swipe_program_v14(
        board,
        action,
        candidate_key="COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
    )


@lru_cache(maxsize=None)
def _actions(board: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(
        action.value
        for action in ACTION_ORDER
        if _swipe(board, action.value)[0] != board
    )


@lru_cache(maxsize=None)
def _status(board: tuple[int, ...]) -> str:
    if max(board) >= GOAL_RANK:
        return Swipe2048Status.WON.value
    return Swipe2048Status.ACTIVE.value if _actions(board) else Swipe2048Status.LOST.value


@dataclass(frozen=True, slots=True)
class _Value:
    score: Fraction
    loss: Fraction
    action: str | None


def _better(candidate: _Value, current: _Value | None) -> bool:
    if current is None:
        return True
    if candidate.action is None or current.action is None:
        _fail("terminal value entered root comparison")
    order = tuple(action.value for action in ACTION_ORDER)
    return (candidate.score, -candidate.loss, -order.index(candidate.action)) > (
        current.score,
        -current.loss,
        -order.index(current.action),
    )


class _SynthesizedPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = 0
        self.misses = 0
        self.rows = 0
        self.outcomes = 0

    def _action_value(
        self, board: tuple[int, ...], action: str, remaining: int
    ) -> _Value:
        self.rows += 1
        moved, merge_score = _swipe(board, action)
        if moved == board:
            _fail("illegal synthesized action entered Bellman backup")
        spawn_rows = spawn_v16.apply_observation_proposed_spawn_program_v16(moved)
        self.outcomes += len(spawn_rows)
        score = Fraction()
        loss = Fraction()
        for cell, rank, probability in spawn_rows:
            child = list(moved)
            if child[cell] != 0:
                _fail("synthesized spawn row targets occupied cell")
            child[cell] = rank
            child_board = tuple(child)
            child_value = self._state_value(
                child_board, _status(child_board), remaining - 1
            )
            score += probability * (merge_score + child_value.score)
            loss += probability * child_value.loss
        return _Value(score, loss, action)

    def _state_value(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        if remaining == 0 or status == Swipe2048Status.WON.value:
            value = _Value(Fraction(), Fraction(), None)
        elif status == Swipe2048Status.LOST.value:
            value = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self._action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = value
        return value

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state.board, action, pre.PLANNING_HORIZON)
            for action in _actions(state.board)
        )


class _DirectPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = 0
        self.misses = 0
        self.rows = 0
        self.outcomes = 0

    @staticmethod
    @lru_cache(maxsize=None)
    def _legal(board: tuple[int, ...]) -> tuple[Swipe2048Action, ...]:
        return legal_actions_v1(board)

    @staticmethod
    @lru_cache(maxsize=None)
    def _row(
        board: tuple[int, ...], status: str, action: Swipe2048Action
    ) -> tuple[Any, ...]:
        return step_v1(Swipe2048State(board, Swipe2048Status(status)), action)

    def _action_value(
        self, state: Swipe2048State, action: Swipe2048Action, remaining: int
    ) -> _Value:
        self.rows += 1
        outcomes = self._row(state.board, state.status.value, action)
        self.outcomes += len(outcomes)
        score = Fraction()
        loss = Fraction()
        for outcome in outcomes:
            child = self._state_value(
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (outcome.merge_score + child.score)
            loss += outcome.probability * child.loss
        return _Value(score, loss, action.value)

    def _state_value(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            value = _Value(Fraction(), Fraction(), None)
        elif state.status is Swipe2048Status.LOST:
            value = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in self._legal(state.board):
                candidate = self._action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = value
        return value

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state, action, pre.PLANNING_HORIZON)
            for action in self._legal(state.board)
        )


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no selected action")
    return best


def _rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": value.action,
            "expected_merge_score": _fdoc(value.score),
            "loss_probability_within_horizon": _fdoc(value.loss),
        }
        for value in values
    ]


def _certificate(
    episode_index: int,
    decision_index: int,
    state: Swipe2048State,
    planner: _SynthesizedPlanner,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes, planner.hits, planner.misses)
    values = planner.roots(state)
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_certificate.v17",
        "schema_version": SCHEMA_VERSION,
        "synthesized_plan_preregistration_id": pre.PREREGISTRATION_ID,
        "synthesized_world_model_id": pre.V16_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "root_action_exact_values": _rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": _fdoc(selected.score),
        "selected_loss_probability_within_horizon": _fdoc(selected.loss),
        "selection_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
        "status": "CERTIFIED_EXACT_SYNTHESIZED_FACTORED_H3_BELLMAN_OPTIMALITY",
        "factored_action_row_evaluation_count": planner.rows - before[0],
        "factored_support_outcome_evaluation_count": planner.outcomes - before[1],
        "persistent_subproof_cache_hit_count": planner.hits - before[2],
        "persistent_subproof_cache_miss_count": planner.misses - before[3],
        "serialized_or_persistent_state_action_row_count": 0,
        "ground_step_v1_accessed_by_certificate": False,
        "matched_direct_accessed_by_certificate": False,
        "target_transition_accessed_before_certificate_freeze": False,
        "certificate_failure": False,
    }
    return (
        {
            **payload,
            "synthesized_plan_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], payload
            ),
        },
        values,
    )


def _direct(
    state: Swipe2048State, planner: _DirectPlanner
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes, planner.hits, planner.misses)
    values = planner.roots(state)
    selected = _best(values)
    return (
        {
            "root_action_exact_values": _rows(values),
            "selected_action": selected.action,
            "selected_expected_merge_score": _fdoc(selected.score),
            "selected_loss_probability_within_horizon": _fdoc(selected.loss),
            "ground_state_action_row_count": planner.rows - before[0],
            "ground_outcome_count": planner.outcomes - before[1],
            "persistent_subproof_cache_hit_count": planner.hits - before[2],
            "persistent_subproof_cache_miss_count": planner.misses - before[3],
            "lane": "STANDALONE_EVALUATION_ONLY",
            "route_or_certificate_authority": False,
        },
        values,
    )


def _episode(task: tuple[int, tuple[int, ...], str]) -> dict[str, Any]:
    episode_index, initial_board, seed = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state)
    synthesized = _SynthesizedPlanner()
    direct = _DirectPlanner()
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        certificate, model_values = _certificate(
            episode_index, decision_index, state, synthesized
        )
        control, direct_values = _direct(state, direct)
        model_map = {row.action: row for row in model_values}
        direct_map = {row.action: row for row in direct_values}
        equal = set(model_map) == set(direct_map) and all(
            model_map[action].score == direct_map[action].score
            and model_map[action].loss == direct_map[action].loss
            for action in model_map
        )
        selected = certificate["selected_action"]
        selected_equal = equal and selected == control["selected_action"]
        if not selected_equal:
            _fail("synthesized model and cold exact control differ")
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, Swipe2048Action(selected)),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "EXACT_SYNTHESIZED_FACTORED_MODEL_CERTIFIED",
                "local_ground_recovery_attempted": False,
                "operational_ground_state_action_row_count": 0,
                "operational_ground_outcome_count": 0,
                "matched_cold_direct": control,
                "all_root_action_values_exactly_equal": equal,
                "selected_action_exact_value_and_loss_equivalent": selected_equal,
                "certificate_frozen_before_target_transition": True,
                "executed_action": selected,
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_episode.v17",
        "schema_version": SCHEMA_VERSION,
        "synthesized_plan_preregistration_id": pre.PREREGISTRATION_ID,
        "synthesized_world_model_id": pre.V16_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "initial_state": initial,
        "execution_seed": seed,
        "planning_horizon": pre.PLANNING_HORIZON,
        "decisions": decisions,
        "decision_count": len(decisions),
        "synthesized_model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "final_state": _state_document(state),
        "all_root_action_values_exactly_equal": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
    }
    return {
        **payload,
        "synthesized_plan_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SynthesizedPlanCampaignV17:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("synthesized-plan campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("synthesized-plan campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "synthesized_plan_campaign_id"
        }
        if (
            document.get("synthesized_plan_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("synthesized-plan campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("synthesized-plan campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_synthesized_plan_campaign_v17(
) -> Standard2048SynthesizedPlanCampaignV17:
    preregistration = pre.freeze_standard_2048_synthesized_plan_preregistration_v17()
    model_binding = {
        "v16_spawn_program_campaign_id": pre.V16_SPAWN_CAMPAIGN_ID,
        "v16_synthesized_world_model_id": pre.V16_WORLD_MODEL_ID,
        "v16_independent_verification_id": pre.V16_INDEPENDENT_VERIFICATION_ID,
        "swipe_and_spawn_components_both_observation_proposed_and_exact_proved": True,
        "full_state_action_table_present": False,
    }
    tasks = tuple(
        (index, board, pre.TARGET_SEEDS[index])
        for index, board in enumerate(pre.TARGET_INITIAL_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    decision_count = len(decisions)
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_campaign.v17",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "synthesized_plan_preregistration": preregistration.to_document(),
        "synthesized_world_model_binding": model_binding,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": decision_count,
        "synthesized_model_certificate_count": decision_count,
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "joint_model_synthesis_transition_observation_count": 1152,
        "additional_model_acquisition_observation_count": 0,
        "matched_fixed_observation_control_count": 8192,
        "registered_offline_observation_difference": 7040,
        "online_target_transition_observation_count": decision_count,
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for row in decisions
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for row in decisions
        ),
        "evaluation_cold_direct_ground_state_action_row_count": sum(
            row["matched_cold_direct"]["ground_state_action_row_count"]
            for row in decisions
        ),
        "evaluation_cold_direct_ground_outcome_count": sum(
            row["matched_cold_direct"]["ground_outcome_count"]
            for row in decisions
        ),
        "all_root_action_values_exactly_equal": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
        "all_planning_performed_in_synthesized_factored_model": True,
        "ground_step_v1_used_by_operational_planner": False,
        "matched_direct_used_for_route_or_certificate": False,
        "sample_tax_result": "POSITIVE_CONDITIONAL_SYNTHESIZED_MODEL_PLANNING_RESULT",
        "registered_observation_axis_reduction_retained": True,
        "conditional_on_frozen_candidate_grammars_and_exact_proofs": True,
        "total_operational_work_saving_claimed": False,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(
            max(episode["final_state"]["board_ranks"]) >= GOAL_RANK
            for episode in episodes
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    campaign_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    canonical_bytes = canonical_json_bytes(
        {**payload, "synthesized_plan_campaign_id": campaign_id}
    )
    if (
        campaign_id != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest()
        != EXPECTED_CANONICAL_SHA256
        or payload["factored_action_row_evaluation_count"]
        != EXPECTED_FACTORED_ACTION_ROW_COUNT
        or payload["factored_support_outcome_evaluation_count"]
        != EXPECTED_FACTORED_SUPPORT_OUTCOME_COUNT
    ):
        _fail("frozen synthesized-plan campaign outcome changed")
    return Standard2048SynthesizedPlanCampaignV17(
        _ISSUER, canonical_bytes, campaign_id
    )


def verify_standard_2048_synthesized_plan_campaign_v17(
    value: Standard2048SynthesizedPlanCampaignV17,
) -> Standard2048SynthesizedPlanCampaignV17:
    if type(value) is not Standard2048SynthesizedPlanCampaignV17:
        _fail("synthesized-plan campaign verifier rejects foreign values")
    value.__post_init__()
    document = value.to_document()
    if (
        document["synthesized_plan_preregistration"][
            "synthesized_plan_preregistration_id"
        ]
        != pre.PREREGISTRATION_ID
        or document["all_root_action_values_exactly_equal"] is not True
        or document["all_selected_actions_exact_value_and_loss_equivalent"]
        is not True
        or document["local_ground_recovery_count"] != 0
        or document["ground_step_v1_used_by_operational_planner"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("synthesized-plan campaign semantics or locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048SynthesizedPlanCampaignV17Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048SynthesizedPlanCampaignV17",
    "run_standard_2048_synthesized_plan_campaign_v17",
    "verify_standard_2048_synthesized_plan_campaign_v17",
)
