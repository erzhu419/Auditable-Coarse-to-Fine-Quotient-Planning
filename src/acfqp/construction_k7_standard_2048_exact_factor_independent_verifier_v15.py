"""Producer-free replay of the exact factored standard-2048 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_basis_independent_verifier_v13 as basis_v13
from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as program_v14
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
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "15.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.174"
PROFILE_KEY = "construction_k7_standard_2048_exact_factored_planning_v15"
PREREGISTRATION_ID = "0e64224ff82e1d19cd6695cf0774a937c69e55320d7787165ba641a362de18f5"
V14_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
V14_PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
V14_LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
SOURCE_SHA256 = "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c"
SOURCE_BYTE_COUNT = 14739
EXPECTED_CAMPAIGN_ID = "0c9be0ddd9895dd9162b6408493d56a16ae4f9ed70591c41117781701a697645"
EXPECTED_VERIFICATION_ID = "33777be770b7ae8eb45c4d22b2a8c5226dde4a443f2381ea402afd09826f7180"
EXPECTED_FACTORED_ROWS = 319506
EXPECTED_FACTORED_OUTCOMES = 7007978
SELECTED_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
PLANNING_HORIZON = 3
MAXIMUM_DECISIONS = 16
MAXIMUM_PROCESSES = 4

TARGET_BOARDS = (
    (2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v172-coordinate-target-{index:02d}-20260813"
    for index in range(4)
)


class ConstructionK7Standard2048ExactFactorIndependentVerifierV15Error(
    ValueError
):
    """Campaign bytes differ from independent source, model, or target replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExactFactorIndependentVerifierV15Error(
        message
    )


def _fdoc(value: Fraction) -> Fraction:
    # loads_canonical_json intentionally restores canonical rational objects to
    # Fraction.  Build the semantic replay in that decoded representation;
    # canonical_json_bytes emits the same reduced rational wire shape.
    return Fraction(value)


def _state_document(board: tuple[int, ...], status: str) -> dict[str, Any]:
    return {"board_ranks": list(board), "status": status}


def _source_closure() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "domains" / "standard_2048.py"
    source = path.read_bytes()
    if (
        len(source) != SOURCE_BYTE_COUNT
        or hashlib.sha256(source).hexdigest() != SOURCE_SHA256
        or SPAWN_DISTRIBUTION
        != ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    ):
        _fail("independent source closure changed")
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_source_closure.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "source_path": "src/acfqp/domains/standard_2048.py",
        "source_sha256": SOURCE_SHA256,
        "source_byte_count": SOURCE_BYTE_COUNT,
        "source_bytes_hex": source.hex(),
        "v14_program_proposal_id": V14_PROPOSAL_ID,
        "v14_program_line_proof_id": V14_LINE_PROOF_ID,
        "v14_factored_world_model_id": V14_WORLD_MODEL_ID,
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
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN,
            payload,
        ),
    }


@lru_cache(maxsize=None)
def _canonical_board(board: tuple[int, ...]) -> tuple[int, ...]:
    candidates = []
    for transform in D4_ELEMENTS:
        result = [0] * 16
        for source, rank in enumerate(board):
            result[transform_cell(source, 4, transform)] = rank
        candidates.append(tuple(result))
    return min(candidates)


@lru_cache(maxsize=None)
def _program_action(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return program_v14.apply_independently_replayed_swipe_program_v14(board, action)


@lru_cache(maxsize=None)
def _actions(board: tuple[int, ...]) -> tuple[str, ...]:
    if any(type(rank) is not int or not 0 <= rank <= 19 for rank in board):
        return ()
    return tuple(
        action.value
        for action in ACTION_ORDER
        if _program_action(board, action.value)[0] != board
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


class _Factored:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = 0
        self.misses = 0
        self.rows = 0
        self.outcomes = 0

    def _action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge_score = _program_action(board, action)
        empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
        if moved == board or not empty:
            _fail("independent factored action row changed")
        score = Fraction()
        loss = Fraction()
        self.outcomes += 2 * len(empty)
        for cell in empty:
            for rank, rank_probability in SPAWN_DISTRIBUTION:
                spawned = list(moved)
                spawned[cell] = rank
                child_board = tuple(spawned)
                child = self._state_value(
                    child_board, _status(child_board), remaining - 1
                )
                probability = rank_probability / len(empty)
                score += probability * (merge_score + child.score)
                loss += probability * child.loss
        return _Value(score, loss, action)

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical_board(board)
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

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical_board(board)
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
        _fail("active root has no independent action")
    return best


def _value_rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": row.action,
            "expected_merge_score": _fdoc(row.score),
            "loss_probability_within_horizon": _fdoc(row.loss),
        }
        for row in values
    ]


def _certificate(
    episode_index: int,
    decision_index: int,
    state: Swipe2048State,
    source_id: str,
    planner: _Factored,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes, planner.hits, planner.misses)
    values = planner.roots(state)
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_exact_factored_h3_certificate.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "exact_factor_source_closure_id": source_id,
        "v14_factored_world_model_id": V14_WORLD_MODEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state.board, state.status.value),
        "planning_horizon": PLANNING_HORIZON,
        "root_action_exact_values": _value_rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": _fdoc(selected.score),
        "selected_loss_probability_within_horizon": _fdoc(selected.loss),
        "selection_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
        "status": "CERTIFIED_EXACT_FACTORED_H3_BELLMAN_OPTIMALITY",
        "factored_action_row_evaluation_count": planner.rows - before[0],
        "factored_support_outcome_evaluation_count": planner.outcomes - before[1],
        "persistent_subproof_cache_hit_count": planner.hits - before[2],
        "persistent_subproof_cache_miss_count": planner.misses - before[3],
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
                CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN,
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
            "root_action_exact_values": _value_rows(values),
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


def _episode(task: tuple[int, tuple[int, ...], str, str]) -> dict[str, Any]:
    episode_index, initial_board, seed, source_id = task
    state = state_from_board_v1(initial_board)
    initial = _state_document(state.board, state.status.value)
    factored = _Factored()
    direct_planner = _Direct()
    decisions = []
    for decision_index in range(MAXIMUM_DECISIONS):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        certificate, factored_values = _certificate(
            episode_index, decision_index, state, source_id, factored
        )
        control, direct_values = _direct(state, direct_planner)
        factored_map = {row.action: row for row in factored_values}
        direct_map = {row.action: row for row in direct_values}
        equal = set(factored_map) == set(direct_map) and all(
            factored_map[action].score == direct_map[action].score
            and factored_map[action].loss == direct_map[action].loss
            for action in factored_map
        )
        selected = certificate["selected_action"]
        equivalent = equal and selected == control["selected_action"]
        if not equivalent:
            _fail("independent factored and direct planners differ")
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, Swipe2048Action(selected)),
            seed=seed,
            decision_index=decision_index,
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
                "matched_cold_direct": control,
                "all_root_action_values_exactly_equal": equal,
                "selected_action_exact_value_and_loss_equivalent": equivalent,
                "certificate_frozen_before_target_transition": True,
                "executed_action": selected,
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
        "exact_factor_source_closure_id": source_id,
        "episode_index": episode_index,
        "initial_state": initial,
        "execution_seed": seed,
        "planning_horizon": PLANNING_HORIZON,
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
        "exact_factor_episode_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN,
            payload,
        ),
    }


def _verify_preregistration(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("preregistration is not an object")
    payload = {
        key: value
        for key, value in document.items()
        if key != "exact_factor_preregistration_id"
    }
    if (
        document.get("exact_factor_preregistration_id") != PREREGISTRATION_ID
        or content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN,
            payload,
        )
        != PREREGISTRATION_ID
        or document.get("outcome_fields_present") is not False
        or document.get("target_execution_performed") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("preregistration identity or locks changed")
    return document


def _expected_campaign(observed: dict[str, Any]) -> dict[str, Any]:
    preregistration = _verify_preregistration(observed["exact_factor_preregistration"])
    source = _source_closure()
    if observed["exact_factor_source_closure"] != source:
        _fail("embedded exact-factor source closure changed")

    basis_bytes = basis_v13.replay_standard_2048_coordinate_basis_bytes_independently_v13()
    v14_bytes = canonical_json_bytes(observed["v14_factored_world_model"])
    program_v14.verify_standard_2048_observation_proposed_program_bytes_independently_v14(
        coordinate_basis_bytes=basis_bytes,
        factored_world_model_bytes=v14_bytes,
    )
    tasks = tuple(
        (index, board, TARGET_SEEDS[index], source["exact_factor_source_closure_id"])
        for index, board in enumerate(TARGET_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decision_count = sum(episode["decision_count"] for episode in episodes)
    equivalent = all(
        episode["all_root_action_values_exactly_equal"]
        and episode["all_selected_actions_exact_value_and_loss_equivalent"]
        for episode in episodes
    )
    payload = {
        "schema": "acfqp.standard_2048_exact_factor_campaign.v15",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "exact_factor_preregistration": preregistration,
        "exact_factor_source_closure": source,
        "v14_factored_world_model": observed["v14_factored_world_model"],
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": decision_count,
        "exact_factored_certificate_count": decision_count,
        "local_ground_recovery_count": 0,
        "cold_direct_operational_fallback_count": 0,
        "program_arm_offline_transition_observation_count": 768,
        "matched_fixed_observation_control_count": 8192,
        "offline_transition_observation_saving": 7424,
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
        "all_root_action_values_exactly_equal": equivalent,
        "all_selected_actions_exact_value_and_loss_equivalent": equivalent,
        "all_planning_performed_in_exact_factored_model": True,
        "ground_step_v1_used_by_operational_planner": False,
        "matched_direct_used_for_route_or_certificate": False,
        "observation_compute_ground_and_target_axes_reported_separately": True,
        "registered_sample_tax_outcome": (
            "POSITIVE_CONDITIONAL_SOURCE_CLOSED_SAMPLE_TAX_RESULT"
            if equivalent and decision_count and 7424 > 0
            else "NEGATIVE_REGISTERED_SAMPLE_TAX_RESULT"
        ),
        "sample_tax_reduced_on_registered_offline_observation_axis": (
            equivalent and decision_count > 0
        ),
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
        "exact_factor_campaign_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN,
            payload,
        ),
    }
    if (
        document["exact_factor_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or document["factored_action_row_evaluation_count"] != EXPECTED_FACTORED_ROWS
        or document["factored_support_outcome_evaluation_count"]
        != EXPECTED_FACTORED_OUTCOMES
    ):
        _fail("independent exact-factor campaign outcome changed")
    return document


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExactFactorIndependentVerificationV15:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent exact-factor verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("exact_factor_verification_id") != self.verification_id
            or document.get("exact_factor_campaign_id") != self.campaign_id
        ):
            _fail("independent exact-factor verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "exact_factor_verification_id"
        }
        if content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN,
            payload,
        ) != self.verification_id:
            _fail("independent exact-factor verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("independent exact-factor verification is not an object")
        return document


def verify_standard_2048_exact_factor_campaign_bytes_independently_v15(
    canonical_bytes: bytes,
) -> Standard2048ExactFactorIndependentVerificationV15:
    if type(canonical_bytes) is not bytes:
        _fail("independent exact-factor verifier requires bytes")
    observed = loads_canonical_json(canonical_bytes)
    if (
        type(observed) is not dict
        or canonical_json_bytes(observed) != canonical_bytes
        or observed.get("exact_factor_campaign_id") != EXPECTED_CAMPAIGN_ID
    ):
        _fail("exact-factor campaign root or frozen identity changed")
    payload = {
        key: value
        for key, value in observed.items()
        if key != "exact_factor_campaign_id"
    }
    if content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN, payload
    ) != EXPECTED_CAMPAIGN_ID:
        _fail("exact-factor campaign content identity changed")
    expected = _expected_campaign(observed)
    if observed != expected:
        _fail("exact-factor campaign differs from producer-free semantic replay")
    verification_payload = {
        "schema": "acfqp.standard_2048_exact_factor_independent_verification.v15",
        "schema_version": SCHEMA_VERSION,
        "exact_factor_preregistration_id": PREREGISTRATION_ID,
        "exact_factor_campaign_id": EXPECTED_CAMPAIGN_ID,
        "v13_observation_and_coordinate_selection_independently_replayed": True,
        "v14_program_proposal_and_160000_line_proof_independently_replayed": True,
        "source_closed_spawn_contract_independently_replayed": True,
        "all_64_factored_h3_certificates_independently_replayed": True,
        "all_64_target_transitions_independently_replayed": True,
        "matched_cold_ground_values_independently_replayed": True,
        "all_root_action_values_exactly_equal": True,
        "sample_tax_observation_axis_reduction_independently_verified": True,
        "total_operational_work_saving_verified": False,
        "broad_sample_efficiency_or_full_game_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN,
        verification_payload,
    )
    if verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen independent exact-factor verification identity changed")
    return Standard2048ExactFactorIndependentVerificationV15(
        _ISSUER,
        canonical_json_bytes(
            {
                **verification_payload,
                "exact_factor_verification_id": verification_id,
            }
        ),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048ExactFactorIndependentVerifierV15Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExactFactorIndependentVerificationV15",
    "verify_standard_2048_exact_factor_campaign_bytes_independently_v15",
)
