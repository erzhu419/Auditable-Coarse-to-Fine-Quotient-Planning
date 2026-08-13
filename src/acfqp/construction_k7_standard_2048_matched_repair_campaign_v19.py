"""Matched active-program and no-prior-table local repair campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
from acfqp import construction_k7_standard_2048_local_repair_preregistration_v18 as v18
from acfqp import construction_k7_standard_2048_matched_repair_preregistration_v19 as pre
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    support_outcomes_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_matched_repair_campaign_v19"
EXPECTED_CAMPAIGN_ID = "1154337025f11c493a1805744f27ea7e9057fd2f2b4884c8e3eb46e4535847b7"
EXPECTED_CANONICAL_BYTE_COUNT = 129401
EXPECTED_CANONICAL_SHA256 = "74dbf6ef96f2fccb18b1f08fd04732a088db24bb50ef435fa3dded36066a049c"
PROGRAM_ARM = pre.ARMS[0]
TABLE_ARM = pre.ARMS[1]
Candidate = tuple[str, int, Fraction]


class ConstructionK7Standard2048MatchedRepairCampaignV19Error(ValueError):
    """The matched acquisition, model, plan, target, or result changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MatchedRepairCampaignV19Error(message)


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


def _predict(candidate: Candidate, count: int) -> Fraction:
    _, threshold, override = candidate
    return override if threshold and count <= threshold else v18.BASE_RATE


def _frontier(root: Swipe2048State) -> tuple[int, ...]:
    counts: set[int] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(board: tuple[int, ...], status: str, remaining: int) -> None:
        board = _canonical(board)
        key = (board, status, remaining)
        if remaining == 0 or status != "ACTIVE" or key in visited:
            return
        visited.add(key)
        for action in _actions(board):
            moved, _ = _swipe(board, action)
            empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
            counts.add(len(empty))
            for cell in empty:
                for rank in (1, 2):
                    child = list(moved)
                    child[cell] = rank
                    child_board = tuple(child)
                    walk(child_board, _status(child_board), remaining - 1)

    walk(root.board, root.status.value, pre.PLANNING_HORIZON)
    return tuple(sorted(counts))


def _failure(
    *, arm: str, episode_index: int, decision_index: int, state: Swipe2048State,
    frontier: tuple[int, ...], unresolved: tuple[int, ...], model_before_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_failure.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "frontier_empty_counts": list(frontier),
        "unresolved_empty_counts": list(unresolved),
        "model_before_id": model_before_id,
        "status": "FAILED_FRONTIER_MODEL_COMPLETENESS_CERTIFICATE",
        "ground_query_count_before_failure": 0,
        "target_transition_accessed_before_failure": False,
        "cold_ground_planner_accessed_before_failure": False,
        "failure_frozen_before_acquisition": True,
    }
    return {
        **payload,
        "matched_repair_failure_id": content_id(pre.FUTURE_DOMAINS["failure"], payload),
    }


def _query_record(
    *, arm: str, failure_id: str, ordinal: int, empty_count: int,
    before_count: int | None, after_count: int | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_acquisition.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "matched_repair_failure_id": failure_id,
        "arm": arm,
        "query_ordinal_within_arm": ordinal,
        "queried_empty_count": empty_count,
        "observed_rank_two_probability": kernel.query_rank_two_probability_v18(empty_count),
        "candidate_count_before": before_count,
        "candidate_count_after": after_count,
        "query_was_in_frozen_failed_frontier": True,
        "query_after_failure_freeze": True,
        "full_ground_state_action_row_materialized": False,
    }
    return {
        **payload,
        "matched_repair_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], payload
        ),
    }


def _active_query(candidates: tuple[Candidate, ...], frontier: tuple[int, ...]) -> int:
    choices = []
    for count in frontier:
        buckets: dict[Fraction, int] = {}
        for candidate in candidates:
            value = _predict(candidate, count)
            buckets[value] = buckets.get(value, 0) + 1
        if len(buckets) > 1:
            choices.append((max(buckets.values()), count))
    if not choices:
        _fail("active query requested without candidate disagreement")
    return min(choices)[1]


def _program_acquire(
    failure: dict[str, Any], candidates: tuple[Candidate, ...], query_offset: int,
) -> tuple[tuple[Candidate, ...], list[dict[str, Any]]]:
    frontier = tuple(failure["frontier_empty_counts"])
    rows = []
    while len(candidates) > 1:
        count = _active_query(candidates, frontier)
        observed = kernel.query_rank_two_probability_v18(count)
        before = candidates
        candidates = tuple(row for row in candidates if _predict(row, count) == observed)
        if not candidates or len(candidates) >= len(before):
            _fail("active program query did not shrink its version space")
        rows.append(
            _query_record(
                arm=PROGRAM_ARM,
                failure_id=failure["matched_repair_failure_id"],
                ordinal=query_offset + len(rows),
                empty_count=count,
                before_count=len(before),
                after_count=len(candidates),
            )
        )
    return candidates, rows


def _table_acquire(
    failure: dict[str, Any], table: dict[int, Fraction], query_offset: int,
) -> list[dict[str, Any]]:
    rows = []
    for count in failure["unresolved_empty_counts"]:
        if count in table:
            _fail("no-prior table attempted to query an existing row")
        table[count] = kernel.query_rank_two_probability_v18(count)
        rows.append(
            _query_record(
                arm=TABLE_ARM,
                failure_id=failure["matched_repair_failure_id"],
                ordinal=query_offset + len(rows),
                empty_count=count,
                before_count=None,
                after_count=None,
            )
        )
    return rows


def _program_overlay(candidate: Candidate, acquisitions: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_overlay.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "arm": PROGRAM_ARM,
        "acquisition_ids": [row["matched_repair_acquisition_id"] for row in acquisitions],
        "selected_candidate_key": candidate[0],
        "candidate_version_space_count": 1,
        "context_table": [],
        "prediction_table": [
            {"empty_count": count, "rank_two_probability": _predict(candidate, count)}
            for count in range(1, 17)
        ],
        "persistent_reuse": True,
        "full_state_action_table_materialized": False,
    }
    return {
        **payload,
        "matched_repair_overlay_id": content_id(pre.FUTURE_DOMAINS["overlay"], payload),
    }


def _table_overlay(table: Mapping[int, Fraction], acquisitions: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_overlay.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "arm": TABLE_ARM,
        "acquisition_ids": [row["matched_repair_acquisition_id"] for row in acquisitions],
        "selected_candidate_key": None,
        "candidate_version_space_count": 0,
        "context_table": [
            {"empty_count": count, "rank_two_probability": table[count]}
            for count in sorted(table)
        ],
        "prediction_table": [],
        "persistent_reuse": True,
        "full_state_action_table_materialized": False,
    }
    return {
        **payload,
        "matched_repair_overlay_id": content_id(pre.FUTURE_DOMAINS["overlay"], payload),
    }


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
        current.score, -current.loss, -order.index(current.action)
    )


class _Planner:
    def __init__(self, probability) -> None:
        self.probability = probability
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.rows = self.outcomes = 0

    def action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge = _swipe(board, action)
        empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
        p2 = self.probability(len(empty))
        self.outcomes += 2 * len(empty)
        score = Fraction()
        loss = Fraction()
        for cell in empty:
            for rank, mass in ((1, 1 - p2), (2, p2)):
                child = list(moved)
                child[cell] = rank
                child_board = tuple(child)
                value = self.state_value(child_board, _status(child_board), remaining - 1)
                probability = mass / len(empty)
                score += probability * (merge + value.score)
                loss += probability * value.loss
        return _Value(score, loss, action)

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        if key in self.cache:
            return self.cache[key]
        if remaining == 0 or status == "WON":
            result = _Value(Fraction(), Fraction(), None)
        elif status == "LOST":
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                value = self.action_value(board, action, remaining)
                if _better(value, best):
                    best = value
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self.action_value(state.board, action, pre.PLANNING_HORIZON)
            for action in _actions(state.board)
        )


class _Direct:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.rows = self.outcomes = 0

    def action_value(self, state: Swipe2048State, action: Swipe2048Action, remaining: int) -> _Value:
        self.rows += 1
        outcomes = kernel.target_outcomes_v18(state, action)
        self.outcomes += len(outcomes)
        score = loss = Fraction()
        for outcome in outcomes:
            value = self.state_value(outcome.next_state.board, outcome.next_state.status.value, remaining - 1)
            score += outcome.probability * (outcome.merge_score + value.score)
            loss += outcome.probability * value.loss
        return _Value(score, loss, action.value)

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        if key in self.cache:
            return self.cache[key]
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            result = _Value(Fraction(), Fraction(), None)
        elif state.status is Swipe2048Status.LOST:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in legal_actions_v1(state.board):
                value = self.action_value(state, action, remaining)
                if _better(value, best):
                    best = value
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(self.action_value(state, action, pre.PLANNING_HORIZON) for action in legal_actions_v1(state.board))


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no action")
    return best


def _rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {"action": value.action, "expected_merge_score": value.score, "loss_probability_within_horizon": value.loss}
        for value in values
    ]


def _certificate(
    *, arm: str, episode_index: int, decision_index: int, state: Swipe2048State,
    overlay: dict[str, Any], planner: _Planner,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes)
    values = planner.roots(state)
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_certificate.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "matched_repair_overlay_id": overlay["matched_repair_overlay_id"],
        "root_action_exact_values": _rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": selected.score,
        "selected_loss_probability_within_horizon": selected.loss,
        "factored_action_row_evaluation_count": planner.rows - before[0],
        "factored_support_outcome_evaluation_count": planner.outcomes - before[1],
        "ground_query_count_during_planning": 0,
        "ground_state_action_row_count": 0,
        "target_transition_accessed_before_certificate_freeze": False,
        "status": "CERTIFIED_MATCHED_REPAIRED_FACTORED_H3",
    }
    return (
        {**payload, "matched_repair_certificate_id": content_id(pre.FUTURE_DOMAINS["certificate"], payload)},
        values,
    )


def _arm_step(
    *, arm: str, episode_index: int, decision_index: int, state: Swipe2048State,
    frontier: tuple[int, ...], candidates: tuple[Candidate, ...], table: dict[int, Fraction],
    all_acquisitions: list[dict[str, Any]], overlay: dict[str, Any] | None,
    planner: _Planner | None,
) -> tuple[dict[str, Any], tuple[Candidate, ...], dict[str, Any], _Planner]:
    if arm == PROGRAM_ARM:
        unresolved = tuple(
            count for count in frontier
            if len({_predict(candidate, count) for candidate in candidates}) > 1
        )
    else:
        unresolved = tuple(count for count in frontier if count not in table)
    failure = None
    acquisitions = []
    if unresolved:
        failure = _failure(
            arm=arm, episode_index=episode_index, decision_index=decision_index,
            state=state, frontier=frontier, unresolved=unresolved,
            model_before_id=None if overlay is None else overlay["matched_repair_overlay_id"],
        )
        if arm == PROGRAM_ARM:
            candidates, acquisitions = _program_acquire(failure, candidates, len(all_acquisitions))
            all_acquisitions.extend(acquisitions)
            overlay = _program_overlay(candidates[0], all_acquisitions)
            planner = _Planner(lambda count, row=candidates[0]: _predict(row, count))
        else:
            acquisitions = _table_acquire(failure, table, len(all_acquisitions))
            all_acquisitions.extend(acquisitions)
            overlay = _table_overlay(table, all_acquisitions)
            planner = _Planner(lambda count: table[count])
    if overlay is None or planner is None:
        _fail("matched arm has no complete model after acquisition")
    certificate, values = _certificate(
        arm=arm, episode_index=episode_index, decision_index=decision_index,
        state=state, overlay=overlay, planner=planner,
    )
    return (
        {
            "arm": arm,
            "failure": failure,
            "acquisitions": acquisitions,
            "overlay": overlay,
            "certificate": certificate,
            "root_values": values,
            "ground_distinction_query_count": len(acquisitions),
        },
        candidates,
        overlay,
        planner,
    )


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_matched_repair_preregistration_v19()
    candidates = v18.candidate_programs_v18()
    table: dict[int, Fraction] = {}
    program_acquisitions: list[dict[str, Any]] = []
    table_acquisitions: list[dict[str, Any]] = []
    program_overlay = table_overlay = None
    program_planner = table_planner = None
    episodes = []
    direct_rows = direct_outcomes = 0
    for episode_index, (board, seed) in enumerate(zip(pre.TARGET_INITIAL_BOARDS, pre.TARGET_SEEDS, strict=True)):
        state = state_from_board_v1(board)
        initial = _state_document(state)
        decisions = []
        for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
            if state.status is not Swipe2048Status.ACTIVE:
                break
            frontier = _frontier(state)
            program, candidates, program_overlay, program_planner = _arm_step(
                arm=PROGRAM_ARM, episode_index=episode_index, decision_index=decision_index,
                state=state, frontier=frontier, candidates=candidates, table=table,
                all_acquisitions=program_acquisitions, overlay=program_overlay, planner=program_planner,
            )
            table_row, candidates, table_overlay, table_planner = _arm_step(
                arm=TABLE_ARM, episode_index=episode_index, decision_index=decision_index,
                state=state, frontier=frontier, candidates=candidates, table=table,
                all_acquisitions=table_acquisitions, overlay=table_overlay, planner=table_planner,
            )
            direct = _Direct()
            direct_values = direct.roots(state)
            direct_best = _best(direct_values)
            direct_rows += direct.rows
            direct_outcomes += direct.outcomes
            program_values = program.pop("root_values")
            table_values = table_row.pop("root_values")
            expected = {row.action: row for row in direct_values}
            for arm_row, values in ((program, program_values), (table_row, table_values)):
                observed = {row.action: row for row in values}
                if set(observed) != set(expected) or any(
                    observed[action].score != expected[action].score
                    or observed[action].loss != expected[action].loss
                    for action in expected
                ) or _best(values).action != direct_best.action:
                    _fail("matched repaired arm differs from cold target-ground")
                arm_row["all_root_values_exactly_match_cold_target_ground"] = True
                arm_row["selected_action_matches_cold_target_ground"] = True
            if program["certificate"]["selected_action"] != table_row["certificate"]["selected_action"]:
                _fail("matched arms selected different target actions")
            selected = direct_best.action
            outcome, tape = select_seeded_outcome_v1(
                kernel.target_outcomes_v18(state, Swipe2048Action(selected)),
                seed=seed, decision_index=decision_index,
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "predecision_state": _state_document(state),
                    "frontier_empty_counts": list(frontier),
                    "program_prior_arm": program,
                    "no_prior_table_arm": table_row,
                    "cold_target_ground_control": {
                        "root_action_exact_values": _rows(direct_values),
                        "selected_action": direct_best.action,
                        "ground_state_action_row_count": direct.rows,
                        "ground_outcome_count": direct.outcomes,
                        "lane": "STANDALONE_EVALUATION_ONLY",
                        "route_or_certificate_authority": False,
                    },
                    "both_arms_exactly_match_cold_target_ground": True,
                    "certificate_frozen_before_target_transition": True,
                    "executed_action": selected,
                    "execution_tape_sha256": tape,
                    "executed_next_state": _state_document(outcome.next_state),
                    "online_target_transition_observation_count": 1,
                    "target_observation_used_for_either_model": False,
                }
            )
            state = outcome.next_state
        episode_payload = {
            "schema": "acfqp.standard_2048_matched_repair_episode.v19",
            "schema_version": SCHEMA_VERSION,
            "matched_repair_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "execution_seed": seed,
            "initial_state": initial,
            "decisions": decisions,
            "decision_count": len(decisions),
            "final_state": _state_document(state),
            "all_matched_arm_values_and_actions_exact": True,
        }
        episodes.append(
            {**episode_payload, "matched_repair_episode_id": content_id(pre.FUTURE_DOMAINS["episode"], episode_payload)}
        )
    decisions = [row for episode in episodes for row in episode["decisions"]]
    program_queries = len(program_acquisitions)
    table_queries = len(table_acquisitions)
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_campaign.v19",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "matched_repair_preregistration": preregistration.to_document(),
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "program_prior_unique_ground_distinction_query_count": program_queries,
        "no_prior_unique_ground_distinction_query_count": table_queries,
        "strict_ground_distinction_query_reduction": table_queries - program_queries,
        "program_prior_query_fraction_of_no_prior": Fraction(program_queries, table_queries),
        "program_prior_failure_count": sum(row["program_prior_arm"]["failure"] is not None for row in decisions),
        "no_prior_failure_count": sum(row["no_prior_table_arm"]["failure"] is not None for row in decisions),
        "program_prior_final_overlay_id": program_overlay["matched_repair_overlay_id"],
        "no_prior_final_overlay_id": table_overlay["matched_repair_overlay_id"],
        "program_prior_selected_candidate_key": candidates[0][0],
        "no_prior_final_context_count": len(table),
        "all_12_program_prior_plans_exact": True,
        "all_12_no_prior_table_plans_exact": True,
        "all_12_arm_actions_identical": True,
        "all_12_target_transitions_shared": True,
        "evaluation_cold_target_ground_state_action_row_count": direct_rows,
        "evaluation_cold_target_ground_outcome_count": direct_outcomes,
        "online_target_transition_observation_count": len(decisions),
        "matched_active_program_prior_sample_result": "POSITIVE_STRICT_GROUND_DISTINCTION_QUERY_REDUCTION",
        "strict_reduction_observed": program_queries < table_queries,
        "conditional_on_v18_candidate_grammar_and_target_kernel": True,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(max(row["final_state"]["board_ranks"]) >= GOAL_RANK for row in episodes),
        "broad_world_model_synthesis_completed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {**payload, "matched_repair_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MatchedRepairCampaignV19:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("matched campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("matched campaign bytes changed")
        payload = {key: value for key, value in document.items() if key != "matched_repair_campaign_id"}
        if document.get("matched_repair_campaign_id") != self.campaign_id or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id:
            _fail("matched campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("matched campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_matched_repair_campaign_v19() -> Standard2048MatchedRepairCampaignV19:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["matched_repair_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen matched campaign outcome changed")
    return Standard2048MatchedRepairCampaignV19(_ISSUER, canonical_bytes, document["matched_repair_campaign_id"])


def verify_standard_2048_matched_repair_campaign_v19(
    value: Standard2048MatchedRepairCampaignV19,
) -> Standard2048MatchedRepairCampaignV19:
    if type(value) is not Standard2048MatchedRepairCampaignV19:
        _fail("matched campaign verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_matched_repair_campaign_v19().canonical_bytes:
        _fail("matched campaign differs from semantic replay")
    document = value.to_document()
    if document["strict_reduction_observed"] is not True or document["official_execution_allowed"] is not False:
        _fail("matched result or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048MatchedRepairCampaignV19Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048MatchedRepairCampaignV19",
    "run_standard_2048_matched_repair_campaign_v19",
    "verify_standard_2048_matched_repair_campaign_v19",
)
