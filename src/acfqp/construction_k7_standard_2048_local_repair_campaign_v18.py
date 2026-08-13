"""Certificate-triggered local program repair for a synthesized 2048 model.

The V16 model is treated as a frozen meta-prior.  A structural H=3 audit first
discovers exactly which post-swipe empty-count contexts the proof needs.  Only
after that audit fails may the campaign query the fresh target kernel.  Exact
answers eliminate preregistered candidate programs; the surviving overlay is
then reused for all later planning.  Cold target-ground planning is evaluation
only and never supplies the operational route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
from acfqp import construction_k7_standard_2048_local_repair_preregistration_v18 as pre
from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
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
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_local_program_repair_campaign_v18"
EXPECTED_CAMPAIGN_ID = "666509cc46b596fb1241fb5d066440e31547cbbd540b79f5bd535acfa3232ede"
EXPECTED_CANONICAL_BYTE_COUNT = 66713
EXPECTED_CANONICAL_SHA256 = "c2856c4819f64473310009cee2718df6dfc4579d581a1ae93c2c57d68731805a"

Candidate = tuple[str, int, Fraction]


class ConstructionK7Standard2048LocalRepairCampaignV18Error(ValueError):
    """The failure order, acquisition, overlay, plan, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LocalRepairCampaignV18Error(message)


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


def _predict(candidate: Candidate, empty_count: int) -> Fraction:
    _, threshold, override = candidate
    if threshold > 0 and empty_count <= threshold:
        return override
    return pre.BASE_RATE


def _support_rows(
    moved: tuple[int, ...], probability_two: Fraction
) -> tuple[tuple[int, int, Fraction, tuple[int, ...]], ...]:
    empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
    if not empty:
        _fail("legal swipe has no spawn support")
    rows = []
    by_rank = {1: 1 - probability_two, 2: probability_two}
    for cell in empty:
        for rank in (1, 2):
            child = list(moved)
            child[cell] = rank
            rows.append((cell, rank, by_rank[rank] / len(empty), tuple(child)))
    if sum((row[2] for row in rows), Fraction()) != 1:
        _fail("overlay spawn row is not normalized")
    return tuple(rows)


def _structural_frontier(
    root: Swipe2048State, horizon: int
) -> tuple[tuple[int, ...], int, int]:
    counts: set[int] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()
    row_count = 0
    support_count = 0

    def walk(board: tuple[int, ...], status: str, remaining: int) -> None:
        nonlocal row_count, support_count
        board = _canonical(board)
        key = (board, status, remaining)
        if remaining == 0 or status != Swipe2048Status.ACTIVE.value or key in visited:
            return
        visited.add(key)
        for action in _actions(board):
            row_count += 1
            moved, _ = _swipe(board, action)
            empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
            counts.add(len(empty))
            support_count += 2 * len(empty)
            for cell in empty:
                for rank in (1, 2):
                    child = list(moved)
                    child[cell] = rank
                    child_board = tuple(child)
                    walk(child_board, _status(child_board), remaining - 1)

    walk(root.board, root.status.value, horizon)
    return tuple(sorted(counts)), row_count, support_count


def _disagreement_counts(
    candidates: tuple[Candidate, ...], frontier: tuple[int, ...]
) -> tuple[int, ...]:
    return tuple(
        count
        for count in frontier
        if len({_predict(candidate, count) for candidate in candidates}) > 1
    )


def _candidate_keys(candidates: tuple[Candidate, ...]) -> list[str]:
    return [candidate[0] for candidate in candidates]


def _failure_document(
    *,
    episode_index: int,
    decision_index: int,
    state: Swipe2048State,
    candidates: tuple[Candidate, ...],
    frontier: tuple[int, ...],
    row_count: int,
    support_count: int,
) -> dict[str, Any]:
    disagreement = _disagreement_counts(candidates, frontier)
    payload = {
        "schema": "acfqp.standard_2048_local_repair_failure.v18",
        "schema_version": SCHEMA_VERSION,
        "local_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "v16_synthesized_world_model_id": pre.V16_WORLD_MODEL_ID,
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "structural_frontier_empty_counts": list(frontier),
        "structural_state_action_row_count": row_count,
        "structural_support_outcome_count": support_count,
        "candidate_version_space_before_failure": _candidate_keys(candidates),
        "candidate_version_space_count": len(candidates),
        "disagreement_empty_counts": list(disagreement),
        "disagreement_empty_count_count": len(disagreement),
        "status": "FAILED_BASE_MODEL_APPLICABILITY_CERTIFICATE",
        "ground_probability_query_count_before_failure": 0,
        "target_transition_accessed_before_failure": False,
        "matched_direct_accessed_before_failure": False,
        "failure_frozen_before_recovery": True,
    }
    return {
        **payload,
        "local_repair_failure_id": content_id(pre.FUTURE_DOMAINS["failure"], payload),
    }


def _acquire_overlay(
    failure: dict[str, Any], candidates: tuple[Candidate, ...]
) -> tuple[tuple[Candidate, ...], list[dict[str, Any]], dict[str, Any]]:
    frontier = tuple(failure["structural_frontier_empty_counts"])
    observations: list[dict[str, Any]] = []
    while True:
        disagreement = _disagreement_counts(candidates, frontier)
        if not disagreement:
            break
        if len(observations) >= pre.MAXIMUM_GROUND_DISTINCTION_QUERIES:
            _fail("local distinction query budget exhausted")
        empty_count = max(disagreement)
        before = candidates
        probability = kernel.query_rank_two_probability_v18(empty_count)
        candidates = tuple(
            candidate for candidate in candidates if _predict(candidate, empty_count) == probability
        )
        if not candidates or len(candidates) >= len(before):
            _fail("adaptive local query did not shrink the candidate version space")
        query_payload = {
            "schema": "acfqp.standard_2048_local_repair_acquisition.v18",
            "schema_version": SCHEMA_VERSION,
            "local_repair_preregistration_id": pre.PREREGISTRATION_ID,
            "local_repair_failure_id": failure["local_repair_failure_id"],
            "query_ordinal": len(observations),
            "queried_empty_count": empty_count,
            "observed_rank_two_probability": probability,
            "candidate_count_before": len(before),
            "candidate_count_after": len(candidates),
            "candidate_keys_after": _candidate_keys(candidates),
            "query_context_was_in_failed_frontier": empty_count in frontier,
            "ground_query_after_failure_freeze": True,
            "full_ground_state_action_row_materialized": False,
        }
        observations.append(
            {
                **query_payload,
                "local_repair_acquisition_id": content_id(
                    pre.FUTURE_DOMAINS["acquisition"], query_payload
                ),
            }
        )
    if len(candidates) != 1:
        _fail("frontier agreement did not identify one reusable overlay program")
    selected = candidates[0]
    overlay_payload = {
        "schema": "acfqp.standard_2048_local_repair_overlay.v18",
        "schema_version": SCHEMA_VERSION,
        "local_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "base_synthesized_world_model_id": pre.V16_WORLD_MODEL_ID,
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "triggering_failure_id": failure["local_repair_failure_id"],
        "acquisition_ids": [row["local_repair_acquisition_id"] for row in observations],
        "selected_candidate_key": selected[0],
        "selected_override_threshold": selected[1],
        "selected_override_rank_two_probability": selected[2],
        "base_rank_two_probability": pre.BASE_RATE,
        "prediction_table": [
            {"post_swipe_empty_count": count, "rank_two_probability": _predict(selected, count)}
            for count in range(1, 17)
        ],
        "candidate_version_space_count": 1,
        "program_selected_from_preregistered_grammar": True,
        "ground_distinction_query_count": len(observations),
        "full_state_action_table_materialized": False,
        "persistent_across_later_decisions_and_episodes": True,
        "authority_conditional_on_registered_candidate_grammar": True,
    }
    overlay = {
        **overlay_payload,
        "local_repair_overlay_id": content_id(
            pre.FUTURE_DOMAINS["overlay"], overlay_payload
        ),
    }
    return candidates, observations, overlay


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


class _OverlayPlanner:
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def _action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge_score = _swipe(board, action)
        empty_count = sum(rank == 0 for rank in moved)
        rows = _support_rows(moved, _predict(self.candidate, empty_count))
        self.outcomes += len(rows)
        score = Fraction()
        loss = Fraction()
        for _, _, probability, child_board in rows:
            child = self._state_value(child_board, _status(child_board), remaining - 1)
            score += probability * (merge_score + child.score)
            loss += probability * child.loss
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
                row = self._action_value(board, action, remaining)
                if _better(row, best):
                    best = row
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state.board, action, pre.PLANNING_HORIZON)
            for action in _actions(state.board)
        )


class _DirectPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.rows = self.outcomes = 0

    def _action_value(
        self, state: Swipe2048State, action: Swipe2048Action, remaining: int
    ) -> _Value:
        self.rows += 1
        outcomes = kernel.target_outcomes_v18(state, action)
        self.outcomes += len(outcomes)
        score = Fraction()
        loss = Fraction()
        for outcome in outcomes:
            child = self._state_value(
                outcome.next_state.board, outcome.next_state.status.value, remaining - 1
            )
            score += outcome.probability * (outcome.merge_score + child.score)
            loss += outcome.probability * child.loss
        return _Value(score, loss, action.value)

    def _state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
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
                row = self._action_value(state, action, remaining)
                if _better(row, best):
                    best = row
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(
            self._action_value(state, action, pre.PLANNING_HORIZON)
            for action in legal_actions_v1(state.board)
        )


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no selected action")
    return best


def _value_rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": value.action,
            "expected_merge_score": _fdoc(value.score),
            "loss_probability_within_horizon": _fdoc(value.loss),
        }
        for value in values
    ]


def _certificate(
    *,
    episode_index: int,
    decision_index: int,
    state: Swipe2048State,
    overlay: dict[str, Any],
    planner: _OverlayPlanner,
    failure_id: str | None,
) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    before = (planner.rows, planner.outcomes, planner.hits, planner.misses)
    values = planner.roots(state)
    selected = _best(values)
    payload = {
        "schema": "acfqp.standard_2048_local_repair_certificate.v18",
        "schema_version": SCHEMA_VERSION,
        "local_repair_preregistration_id": pre.PREREGISTRATION_ID,
        "local_repair_overlay_id": overlay["local_repair_overlay_id"],
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "root_action_exact_values": _value_rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": selected.score,
        "selected_loss_probability_within_horizon": selected.loss,
        "triggering_failure_id": failure_id,
        "status": "CERTIFIED_REPAIRED_FACTORED_H3_BELLMAN_OPTIMALITY",
        "factored_action_row_evaluation_count": planner.rows - before[0],
        "factored_support_outcome_evaluation_count": planner.outcomes - before[1],
        "persistent_subproof_cache_hit_count": planner.hits - before[2],
        "persistent_subproof_cache_miss_count": planner.misses - before[3],
        "ground_probability_query_count_during_planning": 0,
        "ground_state_action_row_count": 0,
        "matched_direct_accessed_by_certificate": False,
        "target_transition_accessed_before_certificate_freeze": False,
    }
    return (
        {
            **payload,
            "local_repair_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], payload
            ),
        },
        values,
    )


def _direct_control(state: Swipe2048State) -> tuple[dict[str, Any], tuple[_Value, ...]]:
    planner = _DirectPlanner()
    values = planner.roots(state)
    selected = _best(values)
    return (
        {
            "root_action_exact_values": _value_rows(values),
            "selected_action": selected.action,
            "selected_expected_merge_score": selected.score,
            "selected_loss_probability_within_horizon": selected.loss,
            "ground_state_action_row_count": planner.rows,
            "ground_outcome_count": planner.outcomes,
            "cold_model_per_decision": True,
            "lane": "STANDALONE_EVALUATION_ONLY",
            "route_or_certificate_authority": False,
        },
        values,
    )


def _run_campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_local_repair_preregistration_v18()
    candidates = pre.candidate_programs_v18()
    overlay: dict[str, Any] | None = None
    planner: _OverlayPlanner | None = None
    all_acquisitions: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    total_failures = 0
    first_failed_frontier_count = 0
    evaluation_rows = evaluation_outcomes = 0
    factored_rows = factored_outcomes = 0
    for episode_index, (initial_board, seed) in enumerate(
        zip(pre.TARGET_INITIAL_BOARDS, pre.TARGET_SEEDS, strict=True)
    ):
        state = state_from_board_v1(initial_board)
        decisions: list[dict[str, Any]] = []
        initial_state = _state_document(state)
        for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
            if state.status is not Swipe2048Status.ACTIVE:
                break
            frontier, structural_rows, structural_outcomes = _structural_frontier(
                state, pre.PLANNING_HORIZON
            )
            disagreement = _disagreement_counts(candidates, frontier)
            failure = None
            acquisitions: list[dict[str, Any]] = []
            route_events: list[dict[str, Any]] = []
            if disagreement:
                failure = _failure_document(
                    episode_index=episode_index,
                    decision_index=decision_index,
                    state=state,
                    candidates=candidates,
                    frontier=frontier,
                    row_count=structural_rows,
                    support_count=structural_outcomes,
                )
                total_failures += 1
                if first_failed_frontier_count == 0:
                    first_failed_frontier_count = len(frontier)
                route_events.append(
                    {
                        "sequence": 0,
                        "event": "BASE_APPLICABILITY_CERTIFICATE_FAILED",
                        "artifact_id": failure["local_repair_failure_id"],
                    }
                )
                candidates, acquisitions, overlay = _acquire_overlay(failure, candidates)
                all_acquisitions.extend(acquisitions)
                for ordinal, row in enumerate(acquisitions, start=1):
                    route_events.append(
                        {
                            "sequence": ordinal,
                            "event": "LOCAL_GROUND_DISTINCTION_ACQUIRED",
                            "artifact_id": row["local_repair_acquisition_id"],
                        }
                    )
                route_events.append(
                    {
                        "sequence": len(route_events),
                        "event": "PERSISTENT_PROGRAM_OVERLAY_FROZEN",
                        "artifact_id": overlay["local_repair_overlay_id"],
                    }
                )
                planner = _OverlayPlanner(candidates[0])
            elif overlay is None or planner is None or len(candidates) != 1:
                _fail("certifiable frontier has no frozen overlay authority")
            else:
                route_events.append(
                    {
                        "sequence": 0,
                        "event": "PERSISTENT_OVERLAY_APPLICABILITY_CERTIFIED",
                        "artifact_id": overlay["local_repair_overlay_id"],
                    }
                )
            assert overlay is not None and planner is not None
            certificate, model_values = _certificate(
                episode_index=episode_index,
                decision_index=decision_index,
                state=state,
                overlay=overlay,
                planner=planner,
                failure_id=(failure or {}).get("local_repair_failure_id"),
            )
            route_events.append(
                {
                    "sequence": len(route_events),
                    "event": "REPAIRED_MODEL_CERTIFICATE_FROZEN",
                    "artifact_id": certificate["local_repair_certificate_id"],
                }
            )
            control, direct_values = _direct_control(state)
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
                _fail("repaired abstract model and cold target-ground control differ")
            outcome, tape = select_seeded_outcome_v1(
                kernel.target_outcomes_v18(state, Swipe2048Action(selected)),
                seed=seed,
                decision_index=decision_index,
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "predecision_state": _state_document(state),
                    "structural_frontier_empty_counts": list(frontier),
                    "base_failure": failure,
                    "local_acquisitions": acquisitions,
                    "local_repair_overlay_id": overlay["local_repair_overlay_id"],
                    "certificate": certificate,
                    "route_events": route_events,
                    "route": "LOCAL_PROGRAM_REPAIR_THEN_ABSTRACT_CERTIFICATE" if failure else "REUSED_REPAIRED_ABSTRACT_MODEL",
                    "operational_ground_probability_query_count": len(acquisitions),
                    "operational_ground_state_action_row_count": 0,
                    "matched_cold_target_ground_control": control,
                    "all_root_action_values_exactly_equal": equal,
                    "selected_action_exact_value_and_loss_equivalent": selected_equal,
                    "certificate_frozen_before_target_transition": True,
                    "executed_action": selected,
                    "execution_tape_sha256": tape,
                    "executed_next_state": _state_document(outcome.next_state),
                    "online_target_transition_observation_count": 1,
                    "target_observation_used_for_future_model_update": False,
                }
            )
            evaluation_rows += control["ground_state_action_row_count"]
            evaluation_outcomes += control["ground_outcome_count"]
            factored_rows += certificate["factored_action_row_evaluation_count"]
            factored_outcomes += certificate["factored_support_outcome_evaluation_count"]
            state = outcome.next_state
        episode_payload = {
            "schema": "acfqp.standard_2048_local_repair_episode.v18",
            "schema_version": SCHEMA_VERSION,
            "local_repair_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "execution_seed": seed,
            "initial_state": initial_state,
            "decisions": decisions,
            "decision_count": len(decisions),
            "certificate_failure_count": sum(row["base_failure"] is not None for row in decisions),
            "ground_distinction_query_count": sum(
                row["operational_ground_probability_query_count"] for row in decisions
            ),
            "repaired_model_certificate_count": len(decisions),
            "final_state": _state_document(state),
            "all_selected_actions_match_cold_target_ground": all(
                row["selected_action_exact_value_and_loss_equivalent"] for row in decisions
            ),
        }
        episodes.append(
            {
                **episode_payload,
                "local_repair_episode_id": content_id(
                    pre.FUTURE_DOMAINS["episode"], episode_payload
                ),
            }
        )
    if overlay is None or len(candidates) != 1:
        _fail("campaign did not issue one reusable local overlay program")
    decisions = [row for episode in episodes for row in episode["decisions"]]
    query_count = len(all_acquisitions)
    no_prior_count = first_failed_frontier_count
    payload = {
        "schema": "acfqp.standard_2048_local_repair_campaign.v18",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "local_repair_preregistration": preregistration.to_document(),
        "target_kernel_binding": kernel.kernel_semantics_document_v18(),
        "persistent_local_repair_overlay": overlay,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "certificate_failure_count": total_failures,
        "local_recovery_transaction_count": total_failures,
        "ground_distinction_query_count": query_count,
        "operational_ground_state_action_row_count": 0,
        "repaired_abstract_model_certificate_count": len(decisions),
        "persistent_overlay_reuse_decision_count": len(decisions) - total_failures,
        "selected_overlay_candidate_key": candidates[0][0],
        "matched_no_prior_first_failure_frontier_query_count": no_prior_count,
        "program_prior_ground_query_difference": no_prior_count - query_count,
        "program_prior_ground_query_fraction": Fraction(query_count, no_prior_count),
        "v16_joint_model_synthesis_transition_observation_count": 1152,
        "v16_matched_fixed_observation_control_count": 8192,
        "v16_registered_observation_difference": 7040,
        "online_target_transition_observation_count": len(decisions),
        "factored_action_row_evaluation_count": factored_rows,
        "factored_support_outcome_evaluation_count": factored_outcomes,
        "evaluation_cold_target_ground_state_action_row_count": evaluation_rows,
        "evaluation_cold_target_ground_outcome_count": evaluation_outcomes,
        "base_certificate_failed_before_any_ground_query": True,
        "all_ground_queries_restricted_to_failed_frontier": True,
        "local_distinctions_generalized_by_preregistered_program_prior": True,
        "all_later_planning_completed_in_repaired_abstract_model": True,
        "all_root_action_values_and_selected_actions_match_cold_target_ground": True,
        "target_execution_observations_not_reused_for_model_repair": True,
        "sample_tax_result": "POSITIVE_REGISTERED_LOCAL_PROGRAM_REPAIR_QUERY_RESULT",
        "conditional_on_frozen_candidate_grammar_and_exact_target_queries": True,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(
            max(episode["final_state"]["board_ranks"]) >= GOAL_RANK for episode in episodes
        ),
        "broad_world_model_synthesis_completed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "local_repair_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048LocalRepairCampaignV18:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("local-repair campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("local-repair campaign bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "local_repair_campaign_id"
        }
        if (
            document.get("local_repair_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("local-repair campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("local-repair campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_local_repair_campaign_v18() -> Standard2048LocalRepairCampaignV18:
    document = _run_campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    import hashlib

    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["local_repair_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen local-repair campaign outcome changed")
    return Standard2048LocalRepairCampaignV18(
        _ISSUER, canonical_bytes, document["local_repair_campaign_id"]
    )


def verify_standard_2048_local_repair_campaign_v18(
    value: Standard2048LocalRepairCampaignV18,
) -> Standard2048LocalRepairCampaignV18:
    if type(value) is not Standard2048LocalRepairCampaignV18:
        _fail("local-repair campaign verifier rejects foreign values")
    value.__post_init__()
    expected = run_standard_2048_local_repair_campaign_v18()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("local-repair campaign differs from exact semantic replay")
    document = value.to_document()
    if (
        document["base_certificate_failed_before_any_ground_query"] is not True
        or document["all_ground_queries_restricted_to_failed_frontier"] is not True
        or document["all_root_action_values_and_selected_actions_match_cold_target_ground"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _fail("local-repair campaign semantics or locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048LocalRepairCampaignV18Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048LocalRepairCampaignV18",
    "run_standard_2048_local_repair_campaign_v18",
    "verify_standard_2048_local_repair_campaign_v18",
)
