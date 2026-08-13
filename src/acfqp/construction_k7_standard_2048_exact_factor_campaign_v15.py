"""Exact H=3 planning in an observation-proposed factored 2048 model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_exact_factor_preregistration_v15 as pre
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as program_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    SPAWN_DISTRIBUTION,
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
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = pre.PREREGISTRATION_ID
SELECTED_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
MAXIMUM_EPISODE_PROCESSES = 4
EXPECTED_CAMPAIGN_ID = "0c9be0ddd9895dd9162b6408493d56a16ae4f9ed70591c41117781701a697645"
EXPECTED_CANONICAL_BYTE_COUNT = 283773
EXPECTED_CANONICAL_SHA256 = "0e6232c3e3e68cf18367aa31f9f8bd06a49b80dd596ca70d667899159762ecca"
EXPECTED_FACTORED_ACTION_ROW_COUNT = 319506
EXPECTED_FACTORED_SUPPORT_OUTCOME_COUNT = 7007978


class ConstructionK7Standard2048ExactFactorCampaignV15Error(ValueError):
    """The source closure, factored certificate, target, or control changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExactFactorCampaignV15Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_document(board: tuple[int, ...], status: str) -> dict[str, Any]:
    return {"board_ranks": list(board), "status": status}


def _source_closure_document() -> dict[str, Any]:
    source_path = Path(__file__).resolve().parent / "domains" / "standard_2048.py"
    source_bytes = source_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    if (
        source_sha != pre.STANDARD_2048_SOURCE_SHA256
        or len(source_bytes) != pre.STANDARD_2048_SOURCE_BYTE_COUNT
        or SPAWN_DISTRIBUTION
        != ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    ):
        _fail("standard-2048 source closure changed")
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_source_closure.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "source_path": "src/acfqp/domains/standard_2048.py",
        "source_sha256": source_sha,
        "source_byte_count": len(source_bytes),
        "source_bytes_hex": source_bytes.hex(),
        "v14_program_proposal_id": pre.V14_PROGRAM_PROPOSAL_ID,
        "v14_program_line_proof_id": pre.V14_PROGRAM_LINE_PROOF_ID,
        "v14_factored_world_model_id": pre.V14_FACTORED_WORLD_MODEL_ID,
        "spawn_distribution": [
            {"rank": rank, "probability": _fdoc(probability)}
            for rank, probability in SPAWN_DISTRIBUTION
        ],
        "spawn_cell_law": "UNIFORM_OVER_ALL_POST_SWIPE_EMPTY_CELLS",
        "spawn_rank_independent_of_cell_given_registered_law": True,
        "selected_swipe_program": SELECTED_PROGRAM,
        "source_and_program_identities_verified_before_target": True,
        "target_identity_or_transition_bytes_present": False,
    }
    return {
        **payload,
        "exact_factor_source_closure_id": content_id(
            pre.FUTURE_DOMAINS["source_closure"], payload
        ),
    }


@lru_cache(maxsize=None)
def _canonical_board(board: tuple[int, ...]) -> tuple[int, ...]:
    candidates = []
    for transform in D4_ELEMENTS:
        transformed = [0] * 16
        for source, rank in enumerate(board):
            transformed[transform_cell(source, 4, transform)] = rank
        candidates.append(tuple(transformed))
    return min(candidates)


@lru_cache(maxsize=None)
def _factored_action_result(
    board: tuple[int, ...], action: str
) -> tuple[tuple[int, ...], int]:
    return program_v14.apply_observation_proposed_swipe_program_v14(
        board, action, candidate_key=SELECTED_PROGRAM
    )


@lru_cache(maxsize=None)
def _factored_actions(board: tuple[int, ...]) -> tuple[str, ...]:
    if type(board) is not tuple or len(board) != 16:
        _fail("factored board changed")
    if any(type(rank) is not int or not 0 <= rank <= 19 for rank in board):
        return ()
    return tuple(
        action.value
        for action in ACTION_ORDER
        if _factored_action_result(board, action.value)[0] != board
    )


@lru_cache(maxsize=None)
def _factored_status(board: tuple[int, ...]) -> str:
    if max(board) >= GOAL_RANK:
        return Swipe2048Status.WON.value
    return (
        Swipe2048Status.ACTIVE.value
        if _factored_actions(board)
        else Swipe2048Status.LOST.value
    )


@dataclass(frozen=True, slots=True)
class _Value:
    expected_score: Fraction
    loss_probability: Fraction
    action: str | None


def _better(candidate: _Value, current: _Value | None) -> bool:
    if current is None:
        return True
    if candidate.action is None or current.action is None:
        _fail("action comparison received a terminal value")
    candidate_key = (
        candidate.expected_score,
        -candidate.loss_probability,
        -tuple(action.value for action in ACTION_ORDER).index(candidate.action),
    )
    current_key = (
        current.expected_score,
        -current.loss_probability,
        -tuple(action.value for action in ACTION_ORDER).index(current.action),
    )
    return candidate_key > current_key


class _FactoredPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.state_cache_hits = 0
        self.state_cache_misses = 0
        self.action_row_evaluations = 0
        self.support_outcome_evaluations = 0

    def _outcomes(
        self, board: tuple[int, ...], action: str
    ) -> tuple[tuple[Fraction, tuple[int, ...], str, int], ...]:
        moved, merge_score = _factored_action_result(board, action)
        if moved == board:
            _fail("factored planner received a nonchanging action")
        empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
        if not empty:
            _fail("factored swipe left no spawn cell")
        rows = []
        for cell in empty:
            for rank, rank_probability in SPAWN_DISTRIBUTION:
                spawned = list(moved)
                spawned[cell] = rank
                next_board = tuple(spawned)
                rows.append(
                    (
                        rank_probability / len(empty),
                        next_board,
                        _factored_status(next_board),
                        merge_score,
                    )
                )
        self.support_outcome_evaluations += len(rows)
        return tuple(rows)

    def _action_value(
        self, board: tuple[int, ...], action: str, remaining: int
    ) -> _Value:
        self.action_row_evaluations += 1
        score = Fraction()
        loss = Fraction()
        for probability, next_board, next_status, merge_score in self._outcomes(
            board, action
        ):
            child = self._state_value(next_board, next_status, remaining - 1)
            score += probability * (merge_score + child.expected_score)
            loss += probability * child.loss_probability
        return _Value(score, loss, action)

    def _state_value(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> _Value:
        board = _canonical_board(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.state_cache_hits += 1
            return cached
        self.state_cache_misses += 1
        if remaining == 0 or status == Swipe2048Status.WON.value:
            result = _Value(Fraction(), Fraction(), None)
        elif status == Swipe2048Status.LOST.value:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _factored_actions(board):
                candidate = self._action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def root_values(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> tuple[_Value, ...]:
        if status != Swipe2048Status.ACTIVE.value:
            return ()
        return tuple(
            self._action_value(board, action, remaining)
            for action in _factored_actions(board)
        )


class _DirectPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.state_cache_hits = 0
        self.state_cache_misses = 0
        self.ground_action_rows = 0
        self.ground_outcomes = 0

    @staticmethod
    @lru_cache(maxsize=None)
    def _legal_actions(board: tuple[int, ...]) -> tuple[Swipe2048Action, ...]:
        return legal_actions_v1(board)

    @staticmethod
    @lru_cache(maxsize=None)
    def _outcomes(
        board: tuple[int, ...], status: str, action: Swipe2048Action
    ) -> tuple[Any, ...]:
        return step_v1(Swipe2048State(board, Swipe2048Status(status)), action)

    def _action_value(
        self, state: Swipe2048State, action: Swipe2048Action, remaining: int
    ) -> _Value:
        self.ground_action_rows += 1
        score = Fraction()
        loss = Fraction()
        outcomes = self._outcomes(state.board, state.status.value, action)
        self.ground_outcomes += len(outcomes)
        for outcome in outcomes:
            child = self._state_value(
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (
                outcome.merge_score + child.expected_score
            )
            loss += outcome.probability * child.loss_probability
        return _Value(score, loss, action.value)

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical_board(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.state_cache_hits += 1
            return cached
        self.state_cache_misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            result = _Value(Fraction(), Fraction(), None)
        elif state.status is Swipe2048Status.LOST:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in self._legal_actions(state.board):
                candidate = self._action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def root_values(self, state: Swipe2048State, remaining: int) -> tuple[_Value, ...]:
        if state.status is not Swipe2048Status.ACTIVE:
            return ()
        return tuple(
            self._action_value(state, action, remaining)
            for action in self._legal_actions(state.board)
        )


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root produced no selected action")
    return best


def _value_rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": value.action,
            "expected_merge_score": _fdoc(value.expected_score),
            "loss_probability_within_horizon": _fdoc(value.loss_probability),
        }
        for value in values
    ]


def _certificate_document(
    *,
    episode_index: int,
    decision_index: int,
    state: Swipe2048State,
    source_closure_id: str,
    planner: _FactoredPlanner,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before_rows = planner.action_row_evaluations
    before_outcomes = planner.support_outcome_evaluations
    before_hits = planner.state_cache_hits
    before_misses = planner.state_cache_misses
    values = planner.root_values(
        state.board, state.status.value, pre.PLANNING_HORIZON
    )
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_exact_factored_h3_certificate.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "exact_factor_source_closure_id": source_closure_id,
        "v14_factored_world_model_id": pre.V14_FACTORED_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state.board, state.status.value),
        "planning_horizon": pre.PLANNING_HORIZON,
        "root_action_exact_values": _value_rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": _fdoc(selected.expected_score),
        "selected_loss_probability_within_horizon": _fdoc(
            selected.loss_probability
        ),
        "selection_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
        "status": "CERTIFIED_EXACT_FACTORED_H3_BELLMAN_OPTIMALITY",
        "factored_action_row_evaluation_count": (
            planner.action_row_evaluations - before_rows
        ),
        "factored_support_outcome_evaluation_count": (
            planner.support_outcome_evaluations - before_outcomes
        ),
        "persistent_subproof_cache_hit_count": planner.state_cache_hits - before_hits,
        "persistent_subproof_cache_miss_count": planner.state_cache_misses - before_misses,
        "serialized_state_action_row_count": 0,
        "persistent_state_action_row_count": 0,
        "ground_step_v1_accessed_by_certificate": False,
        "matched_direct_accessed_by_certificate": False,
        "target_transition_accessed_before_certificate_freeze": False,
        "certificate_failure": False,
    }
    return (
        {
            **payload,
            "exact_factor_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], payload
            ),
        },
        values,
    )


def _direct_document(
    state: Swipe2048State, planner: _DirectPlanner
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before_rows = planner.ground_action_rows
    before_outcomes = planner.ground_outcomes
    before_hits = planner.state_cache_hits
    before_misses = planner.state_cache_misses
    values = planner.root_values(state, pre.PLANNING_HORIZON)
    selected = _best(values)
    return (
        {
            "root_action_exact_values": _value_rows(values),
            "selected_action": selected.action,
            "selected_expected_merge_score": _fdoc(selected.expected_score),
            "selected_loss_probability_within_horizon": _fdoc(
                selected.loss_probability
            ),
            "ground_state_action_row_count": planner.ground_action_rows - before_rows,
            "ground_outcome_count": planner.ground_outcomes - before_outcomes,
            "persistent_subproof_cache_hit_count": planner.state_cache_hits - before_hits,
            "persistent_subproof_cache_miss_count": planner.state_cache_misses - before_misses,
            "lane": "STANDALONE_EVALUATION_ONLY",
            "route_or_certificate_authority": False,
        },
        values,
    )


def _episode_task(
    task: tuple[int, tuple[int, ...], str, str]
) -> dict[str, Any]:
    episode_index, initial_board, seed, source_closure_id = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state.board, state.status.value)
    factored = _FactoredPlanner()
    direct = _DirectPlanner()
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        certificate, factored_values = _certificate_document(
            episode_index=episode_index,
            decision_index=decision_index,
            state=state,
            source_closure_id=source_closure_id,
            planner=factored,
        )
        direct_control, direct_values = _direct_document(state, direct)
        factored_by_action = {row.action: row for row in factored_values}
        direct_by_action = {row.action: row for row in direct_values}
        all_action_values_equal = (
            set(factored_by_action) == set(direct_by_action)
            and all(
                factored_by_action[action].expected_score
                == direct_by_action[action].expected_score
                and factored_by_action[action].loss_probability
                == direct_by_action[action].loss_probability
                for action in factored_by_action
            )
        )
        selected_action = certificate["selected_action"]
        selected_equivalent = (
            all_action_values_equal
            and selected_action == direct_control["selected_action"]
        )
        if not selected_equivalent:
            _fail("factored certificate differs from cold exact ground control")
        action = Swipe2048Action(selected_action)
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=decision_index
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state.board, state.status.value),
                "certificate": certificate,
                "route": "EXACT_FACTORED_MODEL_CERTIFIED",
                "local_ground_recovery_attempted": False,
                "operational_ground_state_action_row_count": 0,
                "operational_ground_outcome_count": 0,
                "matched_cold_direct": direct_control,
                "all_root_action_values_exactly_equal": all_action_values_equal,
                "selected_action_exact_value_and_loss_equivalent": selected_equivalent,
                "certificate_frozen_before_target_transition": True,
                "executed_action": selected_action,
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(
                    outcome.next_state.board, outcome.next_state.status.value
                ),
                "online_target_transition_observation_count": 1,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_episode.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "exact_factor_source_closure_id": source_closure_id,
        "episode_index": episode_index,
        "initial_state": initial,
        "execution_seed": seed,
        "planning_horizon": pre.PLANNING_HORIZON,
        "decisions": decisions,
        "decision_count": len(decisions),
        "exact_factored_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "final_state": _state_document(state.board, state.status.value),
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
        "exact_factor_episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_exact_factor_preregistration_v15()
    pre.verify_standard_2048_exact_factor_preregistration_v15(preregistration)
    v14_model = program_v14.prove_standard_2048_swipe_program_and_build_world_model_v14()
    v14_model.__post_init__()
    if v14_model.factored_world_model_id != pre.V14_FACTORED_WORLD_MODEL_ID:
        _fail("V14 factored world model identity changed")
    source_closure = _source_closure_document()
    tasks = tuple(
        (
            episode_index,
            tuple(board),
            seed,
            source_closure["exact_factor_source_closure_id"],
        )
        for episode_index, (board, seed) in enumerate(
            zip(
                pre.v13.TARGET_INITIAL_BOARDS,
                pre.v13.TARGET_EPISODE_SEEDS,
                strict=True,
            )
        )
    )
    with ProcessPoolExecutor(
        max_workers=min(MAXIMUM_EPISODE_PROCESSES, len(tasks))
    ) as executor:
        episodes = list(executor.map(_episode_task, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decision_count = sum(row["decision_count"] for row in episodes)
    all_equivalent = all(
        row["all_root_action_values_exactly_equal"]
        and row["all_selected_actions_exact_value_and_loss_equivalent"]
        for row in episodes
    )
    saving = 8192 - 768
    positive = all_equivalent and saving > 0 and decision_count > 0
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_campaign.v15",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "exact_factor_preregistration": preregistration.to_document(),
        "exact_factor_source_closure": source_closure,
        "v14_factored_world_model": v14_model.to_document(),
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": decision_count,
        "exact_factored_certificate_count": decision_count,
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "program_arm_offline_transition_observation_count": 768,
        "matched_fixed_observation_control_count": 8192,
        "offline_transition_observation_saving": saving,
        "program_proof_compute_evaluation_count": 160000,
        "online_target_transition_observation_count": decision_count,
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for episode in episodes
            for row in episode["decisions"]
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for episode in episodes
            for row in episode["decisions"]
        ),
        "evaluation_cold_direct_ground_state_action_row_count": sum(
            row["matched_cold_direct"]["ground_state_action_row_count"]
            for episode in episodes
            for row in episode["decisions"]
        ),
        "evaluation_cold_direct_ground_outcome_count": sum(
            row["matched_cold_direct"]["ground_outcome_count"]
            for episode in episodes
            for row in episode["decisions"]
        ),
        "all_root_action_values_exactly_equal": all_equivalent,
        "all_selected_actions_exact_value_and_loss_equivalent": all_equivalent,
        "all_planning_performed_in_exact_factored_model": True,
        "ground_step_v1_used_by_operational_planner": False,
        "matched_direct_used_for_route_or_certificate": False,
        "observation_compute_ground_and_target_axes_reported_separately": True,
        "registered_sample_tax_outcome": (
            "POSITIVE_CONDITIONAL_SOURCE_CLOSED_SAMPLE_TAX_RESULT"
            if positive
            else "NEGATIVE_REGISTERED_SAMPLE_TAX_RESULT"
        ),
        "sample_tax_reduced_on_registered_offline_observation_axis": positive,
        "conditional_on_source_closed_standard_2048_family": True,
        "total_operational_work_saving_claimed": False,
        "broad_domain_or_physical_iid_sample_efficiency_claimed": False,
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
    document = {
        **payload,
        "exact_factor_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }
    if (
        document["exact_factor_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or document["decision_count"] != 64
        or document["exact_factored_certificate_count"] != 64
        or document["factored_action_row_evaluation_count"]
        != EXPECTED_FACTORED_ACTION_ROW_COUNT
        or document["factored_support_outcome_evaluation_count"]
        != EXPECTED_FACTORED_SUPPORT_OUTCOME_COUNT
        or document["evaluation_cold_direct_ground_state_action_row_count"]
        != EXPECTED_FACTORED_ACTION_ROW_COUNT
        or document["evaluation_cold_direct_ground_outcome_count"]
        != EXPECTED_FACTORED_SUPPORT_OUTCOME_COUNT
    ):
        _fail("registered exact-factor campaign outcome changed")
    return document


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExactFactorCampaignV15:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("exact-factor campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("exact_factor_campaign_id") != self.campaign_id
        ):
            _fail("exact-factor campaign bytes changed")
        payload = {key: value for key, value in document.items() if key != "exact_factor_campaign_id"}
        if content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id:
            _fail("exact-factor campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("exact-factor campaign is not an object")
        return document


def run_standard_2048_exact_factor_campaign_v15() -> Standard2048ExactFactorCampaignV15:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if (
        len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("registered exact-factor campaign canonical bytes changed")
    return Standard2048ExactFactorCampaignV15(
        _ISSUER,
        canonical_bytes,
        document["exact_factor_campaign_id"],
    )


def verify_standard_2048_exact_factor_campaign_v15(
    value: Standard2048ExactFactorCampaignV15,
) -> Standard2048ExactFactorCampaignV15:
    if type(value) is not Standard2048ExactFactorCampaignV15:
        _fail("exact-factor campaign verifier rejects foreign values")
    value.__post_init__()
    expected = run_standard_2048_exact_factor_campaign_v15()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("exact-factor campaign differs from full replay")
    return value


__all__ = (
    "ConstructionK7Standard2048ExactFactorCampaignV15Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048ExactFactorCampaignV15",
    "run_standard_2048_exact_factor_campaign_v15",
    "verify_standard_2048_exact_factor_campaign_v15",
)
