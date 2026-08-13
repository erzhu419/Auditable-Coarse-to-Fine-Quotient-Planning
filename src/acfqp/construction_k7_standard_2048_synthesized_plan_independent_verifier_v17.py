"""Producer-free replay of fresh planning in the synthesized 2048 model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
from acfqp import construction_k7_standard_2048_spawn_program_independent_verifier_v16 as spawn_v16
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
PROFILE_KEY = "construction_k7_standard_2048_synthesized_plan_campaign_v17"
PREREGISTRATION_ID = "b2904f79fa0dc9dc843f8674a91197798e3c9e3b18c96cdedf5d5513be7cb268"
V16_SPAWN_CAMPAIGN_ID = "c6d490d140676a9d045e678f1484635d925a655f4c67605afde28690e246aa53"
V16_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
V16_VERIFICATION_ID = "a6fa6e31d8ee765e4a6c352384baed87ef7a38bba58af7590b85b666e94a8198"
EXPECTED_CAMPAIGN_ID = "ef411b84bb88d8084bf9a4b9f65be6200a8459a1e26394a96cc5fa38aeba496e"
EXPECTED_FACTORED_ROWS = 718242
EXPECTED_FACTORED_OUTCOMES = 14711528
EXPECTED_VERIFICATION_ID = "fe132b3f4be8f6b83b59e7f04c5e8c963872c233862c6796a242b87f9ced42d8"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS = 32
MAXIMUM_PROCESSES = 4
TARGET_BOARDS = (
    (2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v176-synthesized-plan-target-{index:02d}-20260813"
    for index in range(4)
)


class ConstructionK7Standard2048SynthesizedPlanIndependentVerifierV17Error(ValueError):
    """Campaign differs from independent model, control, or target replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SynthesizedPlanIndependentVerifierV17Error(
        message
    )


def _fdoc(value: Fraction) -> Fraction:
    return Fraction(value)


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
    return swipe_v14.apply_independently_replayed_swipe_program_v14(board, action)


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
        _fail("terminal value entered action comparison")
    order = tuple(action.value for action in ACTION_ORDER)
    return (candidate.score, -candidate.loss, -order.index(candidate.action)) > (
        current.score,
        -current.loss,
        -order.index(current.action),
    )


class _Synthesized:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def _action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge_score = _swipe(board, action)
        if moved == board:
            _fail("independent synthesized planner used illegal action")
        spawn_rows = spawn_v16.apply_independently_replayed_spawn_program_v16(moved)
        self.outcomes += len(spawn_rows)
        score = Fraction()
        loss = Fraction()
        for cell, rank, probability in spawn_rows:
            child = list(moved)
            child[cell] = rank
            child_board = tuple(child)
            value = self._state_value(child_board, _status(child_board), remaining - 1)
            score += probability * (merge_score + value.score)
            loss += probability * value.loss
        return _Value(score, loss, action)

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        if remaining == 0 or status == Swipe2048Status.WON.value:
            result = _Value(Fraction(), Fraction(), None)
        elif status == Swipe2048Status.LOST.value:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self._action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state.board, action, PLANNING_HORIZON)
            for action in _actions(state.board)
        )


class _Direct:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

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
            value = self._state_value(
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (outcome.merge_score + value.score)
            loss += outcome.probability * value.loss
        return _Value(score, loss, action.value)

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            result = _Value(Fraction(), Fraction(), None)
        elif state.status is Swipe2048Status.LOST:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in self._legal(state.board):
                candidate = self._action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state, action, PLANNING_HORIZON)
            for action in self._legal(state.board)
        )


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("independent active root has no action")
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
    planner: _Synthesized,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes, planner.hits, planner.misses)
    values = planner.roots(state)
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_certificate.v17",
        "schema_version": SCHEMA_VERSION,
        "synthesized_plan_preregistration_id": PREREGISTRATION_ID,
        "synthesized_world_model_id": V16_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": PLANNING_HORIZON,
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
                CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CERTIFICATE_V17_DOMAIN,
                payload,
            ),
        },
        values,
    )


def _direct(state: Swipe2048State, planner: _Direct) -> tuple[dict[str, Any], tuple[_Value, ...]]:
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
    episode_index, board, seed = task
    state = state_from_board_v1(board)
    initial = _state_document(state)
    synthesized = _Synthesized()
    direct = _Direct()
    decisions = []
    for decision_index in range(MAXIMUM_DECISIONS):
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
            _fail("independent synthesized and direct planners differ")
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, Swipe2048Action(selected)),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append({
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
        })
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_episode.v17",
        "schema_version": SCHEMA_VERSION,
        "synthesized_plan_preregistration_id": PREREGISTRATION_ID,
        "synthesized_world_model_id": V16_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "initial_state": initial,
        "execution_seed": seed,
        "planning_horizon": PLANNING_HORIZON,
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
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_EPISODE_V17_DOMAIN,
            payload,
        ),
    }


def _verify_preregistration(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("embedded synthesized-plan preregistration changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "synthesized_plan_preregistration_id"
    }
    if (
        document.get("synthesized_plan_preregistration_id") != PREREGISTRATION_ID
        or content_id(
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_PREREGISTRATION_V17_DOMAIN,
            payload,
        )
        != PREREGISTRATION_ID
        or document.get("outcome_fields_present") is not False
        or document.get("target_execution_performed") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("embedded synthesized-plan preregistration identity changed")
    return document


def _expected(observed: dict[str, Any]) -> dict[str, Any]:
    preregistration = _verify_preregistration(
        observed["synthesized_plan_preregistration"]
    )
    binding = {
        "v16_spawn_program_campaign_id": V16_SPAWN_CAMPAIGN_ID,
        "v16_synthesized_world_model_id": V16_WORLD_MODEL_ID,
        "v16_independent_verification_id": V16_VERIFICATION_ID,
        "swipe_and_spawn_components_both_observation_proposed_and_exact_proved": True,
        "full_state_action_table_present": False,
    }
    tasks = tuple(
        (index, board, TARGET_SEEDS[index])
        for index, board in enumerate(TARGET_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_campaign.v17",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "synthesized_plan_preregistration": preregistration,
        "synthesized_world_model_binding": binding,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "synthesized_model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "joint_model_synthesis_transition_observation_count": 1152,
        "additional_model_acquisition_observation_count": 0,
        "matched_fixed_observation_control_count": 8192,
        "registered_offline_observation_difference": 7040,
        "online_target_transition_observation_count": len(decisions),
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
        "all_root_action_values_exactly_equal": True,
        "all_selected_actions_exact_value_and_loss_equivalent": True,
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
    expected = {
        **payload,
        "synthesized_plan_campaign_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
            payload,
        ),
    }
    if (
        expected["synthesized_plan_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or expected["factored_action_row_evaluation_count"]
        != EXPECTED_FACTORED_ROWS
        or expected["factored_support_outcome_evaluation_count"]
        != EXPECTED_FACTORED_OUTCOMES
    ):
        _fail("independent synthesized-plan outcome changed")
    return expected


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SynthesizedPlanIndependentVerificationV17:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("synthesized-plan verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("synthesized-plan verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "synthesized_plan_verification_id"
        }
        if (
            document.get("synthesized_plan_verification_id") != self.verification_id
            or document.get("synthesized_plan_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("synthesized-plan verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("synthesized-plan verification is not an object")
        return document


def verify_standard_2048_synthesized_plan_bytes_independently_v17(
    canonical_bytes: bytes,
) -> Standard2048SynthesizedPlanIndependentVerificationV17:
    observed = loads_canonical_json(canonical_bytes)
    if (
        type(observed) is not dict
        or canonical_json_bytes(observed) != canonical_bytes
        or observed.get("synthesized_plan_campaign_id") != EXPECTED_CAMPAIGN_ID
    ):
        _fail("synthesized-plan campaign root or identity changed")
    payload = {
        key: value
        for key, value in observed.items()
        if key != "synthesized_plan_campaign_id"
    }
    if content_id(
        CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
        payload,
    ) != EXPECTED_CAMPAIGN_ID:
        _fail("synthesized-plan campaign content identity changed")
    if observed != _expected(observed):
        _fail("synthesized-plan campaign differs from producer-free replay")
    verification_payload = {
        "schema": "acfqp.standard_2048_synthesized_plan_independent_verification.v17",
        "schema_version": SCHEMA_VERSION,
        "synthesized_plan_preregistration_id": PREREGISTRATION_ID,
        "synthesized_plan_campaign_id": EXPECTED_CAMPAIGN_ID,
        "v16_independent_world_model_identity_bound": True,
        "all_128_synthesized_h3_certificates_independently_replayed": True,
        "all_128_target_transitions_independently_replayed": True,
        "all_cold_ground_root_values_independently_replayed": True,
        "all_root_action_values_and_selected_actions_exactly_equal": True,
        "registered_observation_axis_reduction_independently_verified": True,
        "local_ground_recovery_count": 0,
        "target_planning_or_full_game_completed": False,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN,
        verification_payload,
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen synthesized-plan verification identity changed")
    return Standard2048SynthesizedPlanIndependentVerificationV17(
        _ISSUER,
        canonical_json_bytes(
            {**verification_payload, "synthesized_plan_verification_id": verification_id}
        ),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048SynthesizedPlanIndependentVerifierV17Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048SynthesizedPlanIndependentVerificationV17",
    "verify_standard_2048_synthesized_plan_bytes_independently_v17",
)
