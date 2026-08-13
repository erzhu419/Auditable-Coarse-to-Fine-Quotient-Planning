"""Propose a context program from raw observations, prove it, then plan."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_context_program_preregistration_v20 as pre
from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
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
PROFILE_KEY = "construction_k7_standard_2048_context_program_campaign_v20"
MAXIMUM_PROCESSES = 3
EXPECTED_CAMPAIGN_ID = "4dc1d46cfac38aca4bf6e881dfaafea8550f84d535b51cc1f5ef273800b24df5"
EXPECTED_CANONICAL_BYTE_COUNT = 69645
EXPECTED_CANONICAL_SHA256 = "65eb82659a62b2340f246926510f5c8baf97155c02e283f256e63f3d74561d5b"
SELECTED_SWIPE_PROGRAM = "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP"
BASE_RANK_TWO_PROBABILITY = Fraction(1, 10)
Program = tuple[str, int, Fraction]


class ConstructionK7Standard2048ContextProgramCampaignV20Error(ValueError):
    """The context observations, generated program, proof, or plans changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ContextProgramCampaignV20Error(message)


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
        board, action, candidate_key=SELECTED_SWIPE_PROGRAM
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


def _features(
    pre_board: tuple[int, ...], action: str, post_board: tuple[int, ...], merge_score: int
) -> dict[str, int]:
    values = {
        "POST_SWIPE_EMPTY_COUNT": post_board.count(0),
        "PRE_STATE_EMPTY_COUNT": pre_board.count(0),
        "POST_SWIPE_MAX_RANK": max(post_board),
        "PRE_STATE_MAX_RANK": max(pre_board),
        "MERGE_OCCURRED": int(merge_score > 0),
        "ACTION_AXIS_HORIZONTAL": int(action in {"LEFT", "RIGHT"}),
    }
    if tuple(values) != pre.FEATURE_BASIS:
        _fail("context feature basis order changed")
    return values


def _observation_archive() -> dict[str, Any]:
    rows = []
    for index, (board, action, expected_empty_count) in enumerate(pre.SOURCE_WITNESSES):
        post_board, merge_score = _swipe(board, action)
        features = _features(board, action, post_board, merge_score)
        if features["POST_SWIPE_EMPTY_COUNT"] != expected_empty_count:
            _fail("preregistered structural context changed")
        frozen_context = {
            "source_observation_index": index,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post_board),
            "merge_score": merge_score,
            "feature_values": features,
        }
        context_sha256 = hashlib.sha256(canonical_json_bytes(frozen_context)).hexdigest()
        observed_probability = kernel.query_rank_two_probability_v18(expected_empty_count)
        rows.append(
            {
                **frozen_context,
                "structural_context_sha256_before_probability_query": context_sha256,
                "probability_query_ordinal": index,
                "observed_rank_two_probability": _fdoc(observed_probability),
                "probability_queried_after_context_freeze": True,
                "full_state_action_outcome_row_materialized": False,
                "target_kernel_rule_or_source_disclosed_to_proposer": False,
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_context_observation_archive.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": pre.PREREGISTRATION_ID,
        "target_kernel_id": kernel.TARGET_KERNEL_ID,
        "archive_role": "SOURCE_CONTEXT_PROGRAM_PROPOSAL",
        "rows": rows,
        "observation_count": len(rows),
        "unique_probability_query_count": len(rows),
        "context_and_features_frozen_before_each_probability_query": True,
        "target_kernel_source_or_formula_available_to_proposer": False,
        "process_isolation_authority_present": False,
    }
    return {
        **payload,
        "context_observation_archive_id": content_id(pre.FUTURE_DOMAINS["archive"], payload),
    }


def _fraction(document: dict[str, Any]) -> Fraction:
    if set(document) != {"numerator", "denominator"}:
        _fail("rational document changed")
    return Fraction(document["numerator"], document["denominator"])


def _program_probability(program: Program, feature_values: dict[str, int]) -> Fraction:
    feature_name, threshold, override = program
    return override if feature_values[feature_name] <= threshold else BASE_RANK_TWO_PROBABILITY


def _candidate_artifacts(archive: dict[str, Any]) -> list[dict[str, Any]]:
    rows = archive["rows"]
    observed_values = sorted(
        {_fraction(row["observed_rank_two_probability"]) for row in rows}
        - {BASE_RANK_TWO_PROBABILITY}
    )
    if not observed_values:
        _fail("source archive contains no nonbase program output")
    candidates = []
    ordinal = 0
    for feature_name in pre.FEATURE_BASIS:
        thresholds = sorted({row["feature_values"][feature_name] for row in rows})
        for threshold in thresholds:
            for override in observed_values:
                program = (feature_name, threshold, override)
                predictions = [
                    _program_probability(program, row["feature_values"]) for row in rows
                ]
                observed = [
                    _fraction(row["observed_rank_two_probability"]) for row in rows
                ]
                mismatch_indices = [
                    index
                    for index, (predicted, target) in enumerate(
                        zip(predictions, observed, strict=True)
                    )
                    if predicted != target
                ]
                payload = {
                    "schema": "acfqp.standard_2048_context_program_candidate.v20",
                    "schema_version": SCHEMA_VERSION,
                    "context_program_preregistration_id": pre.PREREGISTRATION_ID,
                    "context_observation_archive_id": archive["context_observation_archive_id"],
                    "candidate_ordinal": ordinal,
                    "program_schema": "IF_FEATURE_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
                    "feature_name": feature_name,
                    "threshold": threshold,
                    "base_rank_two_probability": _fdoc(BASE_RANK_TWO_PROBABILITY),
                    "override_rank_two_probability": _fdoc(override),
                    "threshold_generated_from_observed_feature_value": True,
                    "override_generated_from_observed_nonbase_value": True,
                    "source_predictions": [_fdoc(value) for value in predictions],
                    "source_mismatch_indices": mismatch_indices,
                    "source_mismatch_count": len(mismatch_indices),
                    "target_kernel_rule_or_source_accessed": False,
                }
                candidates.append(
                    {
                        **payload,
                        "context_program_candidate_id": content_id(
                            pre.FUTURE_DOMAINS["candidate"], payload
                        ),
                    }
                )
                ordinal += 1
    return candidates


def _proposal(archive: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    best_mismatch = min(row["source_mismatch_count"] for row in candidates)
    best = [row for row in candidates if row["source_mismatch_count"] == best_mismatch]
    if best_mismatch != 0 or len(best) != 1:
        _fail("observed contexts did not uniquely select one zero-mismatch program")
    selected = best[0]
    payload = {
        "schema": "acfqp.standard_2048_context_program_proposal.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": pre.PREREGISTRATION_ID,
        "context_observation_archive_id": archive["context_observation_archive_id"],
        "candidate_artifacts": candidates,
        "candidate_count": len(candidates),
        "candidates_generated_after_source_archive_freeze": True,
        "preenumerated_feature_threshold_candidate_list_used": False,
        "selection_rule": "UNIQUE_MINIMUM_EXACT_RATIONAL_MISMATCH_COUNT",
        "selected_candidate_id": selected["context_program_candidate_id"],
        "selected_feature_name": selected["feature_name"],
        "selected_threshold": selected["threshold"],
        "selected_base_rank_two_probability": selected["base_rank_two_probability"],
        "selected_override_rank_two_probability": selected[
            "override_rank_two_probability"
        ],
        "selected_source_mismatch_count": selected["source_mismatch_count"],
        "unique_zero_mismatch_program": True,
        "proposal_frozen_before_target_formula_proof": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "context_program_proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload),
    }


def _selected_program(proposal: dict[str, Any]) -> Program:
    return (
        proposal["selected_feature_name"],
        proposal["selected_threshold"],
        _fraction(proposal["selected_override_rank_two_probability"]),
    )


def _proof(proposal: dict[str, Any]) -> dict[str, Any]:
    program = _selected_program(proposal)
    rows = []
    for empty_count in range(1, 17):
        feature_values = {name: 0 for name in pre.FEATURE_BASIS}
        feature_values["POST_SWIPE_EMPTY_COUNT"] = empty_count
        predicted = _program_probability(program, feature_values)
        target = kernel.query_rank_two_probability_v18(empty_count)
        rows.append(
            {
                "post_swipe_empty_count": empty_count,
                "predicted_rank_two_probability": _fdoc(predicted),
                "target_rank_two_probability": _fdoc(target),
                "exact_match": predicted == target,
            }
        )
    mismatch_count = sum(row["exact_match"] is not True for row in rows)
    if mismatch_count:
        _fail("selected context program failed exact postproposal proof")
    payload = {
        "schema": "acfqp.standard_2048_context_program_proof.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": pre.PREREGISTRATION_ID,
        "context_program_proposal_id": proposal["context_program_proposal_id"],
        "proposal_frozen_before_target_kernel_semantics_access": True,
        "proof_rows": rows,
        "proof_row_count": len(rows),
        "proof_mismatch_count": mismatch_count,
        "registered_empty_count_domain_complete": True,
        "exact_rational_formula_equivalence_proved": True,
        "proof_rows_not_counted_as_transition_observations": True,
    }
    return {
        **payload,
        "context_program_proof_id": content_id(pre.FUTURE_DOMAINS["proof"], payload),
    }


def _world_model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    if proof["proof_mismatch_count"] != 0:
        _fail("unproved context program cannot issue a world model")
    payload = {
        "schema": "acfqp.standard_2048_context_world_model.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": pre.PREREGISTRATION_ID,
        "context_program_proposal_id": proposal["context_program_proposal_id"],
        "context_program_proof_id": proof["context_program_proof_id"],
        "swipe_world_model_id": swipe_v14.FACTORED_WORLD_MODEL_ID,
        "swipe_program_key": SELECTED_SWIPE_PROGRAM,
        "spawn_cell_law": "UNIFORM_OVER_POST_SWIPE_EMPTY_CELLS",
        "rank_two_program": {
            "program_schema": "IF_FEATURE_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
            "feature_name": proposal["selected_feature_name"],
            "threshold": proposal["selected_threshold"],
            "base_probability": proposal["selected_base_rank_two_probability"],
            "override_probability": proposal["selected_override_rank_two_probability"],
        },
        "exact_over_registered_target_kernel": True,
        "reusable_across_fresh_states_actions_and_episodes": True,
        "serialized_full_state_action_table_present": False,
        "open_ended_coordinate_invention_claimed": False,
    }
    return {
        **payload,
        "context_world_model_id": content_id(pre.FUTURE_DOMAINS["world_model"], payload),
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
        current.score,
        -current.loss,
        -order.index(current.action),
    )


class _ModelPlanner:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def _action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge_score = _swipe(board, action)
        features = _features(board, action, moved, merge_score)
        empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
        if not empty:
            _fail("legal swipe has no spawn location")
        p2 = _program_probability(self.program, features)
        self.outcomes += 2 * len(empty)
        score = Fraction()
        loss = Fraction()
        for cell in empty:
            for rank, mass in ((1, 1 - p2), (2, p2)):
                child = list(moved)
                child[cell] = rank
                child_board = tuple(child)
                value = self._state_value(child_board, _status(child_board), remaining - 1)
                probability = mass / len(empty)
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
        self.hits = self.misses = self.rows = self.outcomes = 0

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
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (outcome.merge_score + child.score)
            loss += outcome.probability * child.loss
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
            value = _Value(Fraction(), Fraction(), None)
        elif state.status is Swipe2048Status.LOST:
            value = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in legal_actions_v1(state.board):
                candidate = self._action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = value
        return value

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


def plan_proved_context_program_root_v20(
    state: Swipe2048State,
    *,
    feature_name: str,
    threshold: int,
    override_probability: Fraction,
) -> dict[str, Any]:
    """Plan one root in the proved factored model without target access."""

    if type(state) is not Swipe2048State:
        _fail("public context-model planner requires an exact state")
    if feature_name not in pre.FEATURE_BASIS or type(threshold) is not int:
        _fail("public context-model program changed")
    program = (feature_name, threshold, Fraction(override_probability))
    planner = _ModelPlanner(program)
    values = planner.roots(state)
    selected = _best(values)
    return {
        "root_action_exact_values": _value_rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": _fdoc(selected.score),
        "selected_loss_probability_within_horizon": _fdoc(selected.loss),
        "factored_action_row_evaluation_count": planner.rows,
        "factored_support_outcome_evaluation_count": planner.outcomes,
        "subproof_cache_hit_count": planner.hits,
        "subproof_cache_miss_count": planner.misses,
        "target_transition_accessed": False,
    }


def evaluate_target_root_v20(state: Swipe2048State) -> dict[str, Any]:
    """Evaluate one cold target root for the standalone comparison lane."""

    if type(state) is not Swipe2048State:
        _fail("public target evaluator requires an exact state")
    planner = _DirectPlanner()
    values = planner.roots(state)
    selected = _best(values)
    return {
        "root_action_exact_values": _value_rows(values),
        "selected_action": selected.action,
        "selected_expected_merge_score": _fdoc(selected.score),
        "selected_loss_probability_within_horizon": _fdoc(selected.loss),
        "ground_state_action_row_count": planner.rows,
        "ground_outcome_count": planner.outcomes,
        "subproof_cache_hit_count": planner.hits,
        "subproof_cache_miss_count": planner.misses,
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }


def _episode(
    task: tuple[int, tuple[int, ...], str, Program, str]
) -> dict[str, Any]:
    episode_index, initial_board, seed, program, world_model_id = task
    state = state_from_board_v1(initial_board)
    initial_state = _state_document(state)
    model = _ModelPlanner(program)
    direct = _DirectPlanner()
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model_before = (model.rows, model.outcomes, model.hits, model.misses)
        model_values = model.roots(state)
        selected = _best(model_values)
        certificate_payload = {
            "schema": "acfqp.standard_2048_context_plan_certificate.v20",
            "schema_version": SCHEMA_VERSION,
            "context_program_preregistration_id": pre.PREREGISTRATION_ID,
            "context_world_model_id": world_model_id,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": pre.PLANNING_HORIZON,
            "root_action_exact_values": _value_rows(model_values),
            "selected_action": selected.action,
            "selected_expected_merge_score": _fdoc(selected.score),
            "selected_loss_probability_within_horizon": _fdoc(selected.loss),
            "selection_rule": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_THEN_ACTION_ORDER",
            "factored_action_row_evaluation_count": model.rows - model_before[0],
            "factored_support_outcome_evaluation_count": model.outcomes - model_before[1],
            "persistent_subproof_cache_hit_count": model.hits - model_before[2],
            "persistent_subproof_cache_miss_count": model.misses - model_before[3],
            "operational_ground_distinction_query_count": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_OBSERVATION_PROPOSED_CONTEXT_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "context_plan_certificate_id": content_id(
                pre.FUTURE_DOMAINS["certificate"], certificate_payload
            ),
        }
        direct_before = (direct.rows, direct.outcomes, direct.hits, direct.misses)
        direct_values = direct.roots(state)
        direct_best = _best(direct_values)
        model_by_action = {value.action: value for value in model_values}
        direct_by_action = {value.action: value for value in direct_values}
        exact = set(model_by_action) == set(direct_by_action) and all(
            model_by_action[action].score == direct_by_action[action].score
            and model_by_action[action].loss == direct_by_action[action].loss
            for action in model_by_action
        )
        if not exact or selected.action != direct_best.action:
            _fail("context world model differs from cold target-ground planner")
        outcome, tape = select_seeded_outcome_v1(
            kernel.target_outcomes_v18(state, Swipe2048Action(selected.action)),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "EXACT_CONTEXT_PROGRAM_WORLD_MODEL_CERTIFIED",
                "matched_cold_target_ground": {
                    "root_action_exact_values": _value_rows(direct_values),
                    "selected_action": direct_best.action,
                    "ground_state_action_row_count": direct.rows - direct_before[0],
                    "ground_outcome_count": direct.outcomes - direct_before[1],
                    "persistent_subproof_cache_hit_count": direct.hits - direct_before[2],
                    "persistent_subproof_cache_miss_count": direct.misses - direct_before[3],
                    "lane": "STANDALONE_EVALUATION_ONLY",
                    "route_or_certificate_authority": False,
                },
                "all_root_action_values_exactly_equal": True,
                "selected_action_exact_value_and_loss_equivalent": True,
                "certificate_frozen_before_target_transition": True,
                "executed_action": selected.action,
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_context_program_episode.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": pre.PREREGISTRATION_ID,
        "context_world_model_id": world_model_id,
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "planning_horizon": pre.PLANNING_HORIZON,
        "decisions": decisions,
        "decision_count": len(decisions),
        "context_model_certificate_count": len(decisions),
        "local_ground_recovery_count": 0,
        "final_state": _state_document(state),
        "all_root_action_values_exactly_equal": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"] for row in decisions
        ),
    }
    return {
        **payload,
        "context_program_episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_context_program_preregistration_v20()
    archive = _observation_archive()
    candidates = _candidate_artifacts(archive)
    proposal = _proposal(archive, candidates)
    proof = _proof(proposal)
    world_model = _world_model(proposal, proof)
    program = _selected_program(proposal)
    tasks = tuple(
        (index, board, pre.TARGET_SEEDS[index], program, world_model["context_world_model_id"])
        for index, board in enumerate(pre.TARGET_INITIAL_BOARDS)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        episodes = list(executor.map(_episode, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    if len(decisions) != len(pre.TARGET_INITIAL_BOARDS) * pre.MAXIMUM_DECISIONS_PER_EPISODE:
        _fail("fresh heldout workload did not retain all registered decisions")
    source_query_count = archive["unique_probability_query_count"]
    payload = {
        "schema": "acfqp.standard_2048_context_program_campaign.v20",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "context_program_preregistration": preregistration.to_document(),
        "context_observation_archive": archive,
        "context_program_proposal": proposal,
        "context_program_proof": proof,
        "context_world_model": world_model,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "source_context_probability_observation_count": source_query_count,
        "generated_context_program_candidate_count": len(candidates),
        "postproposal_exact_formula_proof_row_count": proof["proof_row_count"],
        "v19_matched_program_query_count": 4,
        "v19_strict_no_prior_query_count": 10,
        "retained_query_reduction_against_no_prior": 10 - source_query_count,
        "context_program_query_fraction_of_no_prior": Fraction(source_query_count, 10),
        "context_feature_and_program_proposed_from_raw_observations": True,
        "preenumerated_context_program_candidate_list_used": False,
        "selected_feature_name": proposal["selected_feature_name"],
        "selected_threshold": proposal["selected_threshold"],
        "selected_override_rank_two_probability": proposal[
            "selected_override_rank_two_probability"
        ],
        "all_12_plans_in_observation_proposed_world_model": True,
        "all_12_root_action_values_exactly_match_cold_target_ground": all(
            row["all_root_action_values_exactly_equal"] for row in decisions
        ),
        "all_12_selected_actions_exactly_match_cold_target_ground": all(
            row["selected_action_exact_value_and_loss_equivalent"] for row in decisions
        ),
        "operational_ground_distinction_query_count_during_planning": 0,
        "operational_ground_state_action_row_count_during_planning": 0,
        "online_target_transition_observation_count": len(decisions),
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["matched_cold_target_ground"]["ground_state_action_row_count"]
            for row in decisions
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["matched_cold_target_ground"]["ground_outcome_count"]
            for row in decisions
        ),
        "sample_tax_result": (
            "POSITIVE_CONDITIONAL_CONTEXT_PROGRAM_PROPOSAL_RETAINS_V19_QUERY_REDUCTION"
        ),
        "conditional_on_finite_human_primitive_feature_basis": True,
        "conditional_on_normalized_one_change_program_schema": True,
        "open_ended_coordinate_invention_completed": False,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": any(
            max(episode["final_state"]["board_ranks"]) >= GOAL_RANK for episode in episodes
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "context_program_campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ContextProgramCampaignV20:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("context-program campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("context-program campaign bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "context_program_campaign_id"
        }
        if (
            document.get("context_program_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("context-program campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("context-program campaign is not an object")
        return document


@lru_cache(maxsize=1)
def run_standard_2048_context_program_campaign_v20(
) -> Standard2048ContextProgramCampaignV20:
    document = _campaign_document()
    canonical_bytes = canonical_json_bytes(document)
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        document["context_program_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen context-program campaign outcome changed")
    return Standard2048ContextProgramCampaignV20(
        _ISSUER, canonical_bytes, document["context_program_campaign_id"]
    )


def verify_standard_2048_context_program_campaign_v20(
    value: Standard2048ContextProgramCampaignV20,
) -> Standard2048ContextProgramCampaignV20:
    if type(value) is not Standard2048ContextProgramCampaignV20:
        _fail("context-program campaign verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != run_standard_2048_context_program_campaign_v20().canonical_bytes:
        _fail("context-program campaign differs from semantic replay")
    document = value.to_document()
    if (
        document["selected_feature_name"] != "POST_SWIPE_EMPTY_COUNT"
        or document["selected_threshold"] != 4
        or document["all_12_root_action_values_exactly_match_cold_target_ground"] is not True
        or document["official_execution_allowed"] is not False
    ):
        _fail("context-program campaign result or claim locks changed")
    return value


__all__ = (
    "ConstructionK7Standard2048ContextProgramCampaignV20Error",
    "EXPECTED_CAMPAIGN_ID",
    "Standard2048ContextProgramCampaignV20",
    "evaluate_target_root_v20",
    "plan_proved_context_program_root_v20",
    "run_standard_2048_context_program_campaign_v20",
    "verify_standard_2048_context_program_campaign_v20",
)
