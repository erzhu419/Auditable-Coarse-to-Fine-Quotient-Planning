"""Producer-free replay of the observation-proposed 2048 context program."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_repair_independent_verifier_v18 as target_v18
from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "20.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.179"
PROFILE_KEY = "construction_k7_standard_2048_context_program_campaign_v20"
PREREGISTRATION_ID = "52cc4ca629df1080843293eaf57cdefa351197dd66e11d4049dbbaeecff13fc6"
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
EXPECTED_CAMPAIGN_ID = "4dc1d46cfac38aca4bf6e881dfaafea8550f84d535b51cc1f5ef273800b24df5"
EXPECTED_VERIFICATION_ID = "da1328e43ad293296df5e2021a24d244e77818b7bf888780e1bce974db299f3e"
SWIPE_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
HORIZON = 3
MAXIMUM_DECISIONS = 4
MAXIMUM_PROCESSES = 3
BASE_RATE = Fraction(1, 10)
FEATURE_BASIS = (
    "POST_SWIPE_EMPTY_COUNT",
    "PRE_STATE_EMPTY_COUNT",
    "POST_SWIPE_MAX_RANK",
    "PRE_STATE_MAX_RANK",
    "MERGE_OCCURRED",
    "ACTION_AXIS_HORIZONTAL",
)
SOURCE_WITNESSES = (
    ((0, 0, 1, 2, 4, 5, 4, 1, 2, 3, 2, 4, 1, 2, 3, 6), "UP", 2),
    ((0, 0, 2, 2, 5, 1, 3, 3, 2, 5, 2, 6, 1, 3, 3, 1), "LEFT", 5),
    ((0, 1, 2, 4, 1, 1, 3, 5, 3, 2, 4, 2, 6, 4, 1, 2), "DOWN", 3),
    ((0, 0, 2, 1, 5, 5, 3, 2, 2, 3, 2, 3, 1, 1, 3, 6), "LEFT", 4),
)
TARGET_BOARDS = (
    (2, 6, 5, 0, 6, 1, 0, 0, 0, 2, 3, 1, 6, 5, 5, 4),
    (2, 0, 0, 1, 5, 1, 4, 3, 5, 3, 4, 4, 3, 0, 3, 2),
    (1, 0, 2, 5, 0, 2, 6, 0, 6, 0, 2, 2, 0, 1, 4, 1),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v179-context-program-target-{index:02d}-20260813"
    for index in range(3)
)
Program = tuple[str, int, Fraction]


class ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error(ValueError):
    """Campaign bytes differ from independent proposal, proof, or plan replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error(message)


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _fdoc(value: Fraction) -> Fraction:
    """Return the canonical decoder's exact rational representation."""

    return Fraction(value)


def _fraction(document: Any) -> Fraction:
    if type(document) is Fraction:
        return document
    if type(document) is not dict or set(document) != {"numerator", "denominator"}:
        _fail("rational document changed")
    return Fraction(document["numerator"], document["denominator"])


def _state(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state schema changed")
    state = Swipe2048State(tuple(document["board_ranks"]), Swipe2048Status(document["status"]))
    if state_from_board_v1(state.board) != state:
        _fail("state status changed")
    return state


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
    return tuple(action.value for action in ACTION_ORDER if _swipe(board, action.value)[0] != board)


@lru_cache(maxsize=None)
def _status(board: tuple[int, ...]) -> str:
    if max(board) >= 11:
        return "WON"
    return "ACTIVE" if _actions(board) else "LOST"


def _features(
    pre_board: tuple[int, ...], action: str, post_board: tuple[int, ...], merge_score: int
) -> dict[str, int]:
    result = {
        "POST_SWIPE_EMPTY_COUNT": post_board.count(0),
        "PRE_STATE_EMPTY_COUNT": pre_board.count(0),
        "POST_SWIPE_MAX_RANK": max(post_board),
        "PRE_STATE_MAX_RANK": max(pre_board),
        "MERGE_OCCURRED": int(merge_score > 0),
        "ACTION_AXIS_HORIZONTAL": int(action in {"LEFT", "RIGHT"}),
    }
    if tuple(result) != FEATURE_BASIS:
        _fail("feature basis changed")
    return result


def _archive_expected() -> dict[str, Any]:
    rows = []
    for index, (board, action, empty_count) in enumerate(SOURCE_WITNESSES):
        post_board, merge_score = _swipe(board, action)
        features = _features(board, action, post_board, merge_score)
        if features["POST_SWIPE_EMPTY_COUNT"] != empty_count:
            _fail("independent structural witness changed")
        frozen = {
            "source_observation_index": index,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post_board),
            "merge_score": merge_score,
            "feature_values": features,
        }
        rows.append(
            {
                **frozen,
                "structural_context_sha256_before_probability_query": hashlib.sha256(
                    canonical_json_bytes(frozen)
                ).hexdigest(),
                "probability_query_ordinal": index,
                "observed_rank_two_probability": _fdoc(
                    target_v18.independently_replay_rank_two_probability_v18(empty_count)
                ),
                "probability_queried_after_context_freeze": True,
                "full_state_action_outcome_row_materialized": False,
                "target_kernel_rule_or_source_disclosed_to_proposer": False,
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_context_observation_archive.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": PREREGISTRATION_ID,
        "target_kernel_id": TARGET_KERNEL_ID,
        "archive_role": "SOURCE_CONTEXT_PROGRAM_PROPOSAL",
        "rows": rows,
        "observation_count": 4,
        "unique_probability_query_count": 4,
        "context_and_features_frozen_before_each_probability_query": True,
        "target_kernel_source_or_formula_available_to_proposer": False,
        "process_isolation_authority_present": False,
    }
    return {
        **payload,
        "context_observation_archive_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN, payload
        ),
    }


def _program_probability(program: Program, features: dict[str, int]) -> Fraction:
    name, threshold, override = program
    return override if features[name] <= threshold else BASE_RATE


def _candidates_expected(archive: dict[str, Any]) -> list[dict[str, Any]]:
    rows = archive["rows"]
    observed_values = sorted(
        {_fraction(row["observed_rank_two_probability"]) for row in rows} - {BASE_RATE}
    )
    candidates = []
    ordinal = 0
    for feature_name in FEATURE_BASIS:
        thresholds = sorted({row["feature_values"][feature_name] for row in rows})
        for threshold in thresholds:
            for override in observed_values:
                program = (feature_name, threshold, override)
                predictions = [_program_probability(program, row["feature_values"]) for row in rows]
                observed = [_fraction(row["observed_rank_two_probability"]) for row in rows]
                mismatches = [
                    index
                    for index, (prediction, target) in enumerate(
                        zip(predictions, observed, strict=True)
                    )
                    if prediction != target
                ]
                payload = {
                    "schema": "acfqp.standard_2048_context_program_candidate.v20",
                    "schema_version": SCHEMA_VERSION,
                    "context_program_preregistration_id": PREREGISTRATION_ID,
                    "context_observation_archive_id": archive["context_observation_archive_id"],
                    "candidate_ordinal": ordinal,
                    "program_schema": "IF_FEATURE_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
                    "feature_name": feature_name,
                    "threshold": threshold,
                    "base_rank_two_probability": _fdoc(BASE_RATE),
                    "override_rank_two_probability": _fdoc(override),
                    "threshold_generated_from_observed_feature_value": True,
                    "override_generated_from_observed_nonbase_value": True,
                    "source_predictions": [_fdoc(value) for value in predictions],
                    "source_mismatch_indices": mismatches,
                    "source_mismatch_count": len(mismatches),
                    "target_kernel_rule_or_source_accessed": False,
                }
                candidates.append(
                    {
                        **payload,
                        "context_program_candidate_id": content_id(
                            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN,
                            payload,
                        ),
                    }
                )
                ordinal += 1
    return candidates


def _proposal_expected(archive: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    best_count = min(row["source_mismatch_count"] for row in candidates)
    best = [row for row in candidates if row["source_mismatch_count"] == best_count]
    if best_count != 0 or len(best) != 1:
        _fail("independent observations did not select one program")
    selected = best[0]
    payload = {
        "schema": "acfqp.standard_2048_context_program_proposal.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": PREREGISTRATION_ID,
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
        "selected_override_rank_two_probability": selected["override_rank_two_probability"],
        "selected_source_mismatch_count": selected["source_mismatch_count"],
        "unique_zero_mismatch_program": True,
        "proposal_frozen_before_target_formula_proof": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "context_program_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN, payload
        ),
    }


def _selected_program(proposal: dict[str, Any]) -> Program:
    return (
        proposal["selected_feature_name"],
        proposal["selected_threshold"],
        _fraction(proposal["selected_override_rank_two_probability"]),
    )


def _proof_expected(proposal: dict[str, Any]) -> dict[str, Any]:
    program = _selected_program(proposal)
    rows = []
    for empty_count in range(1, 17):
        features = {name: 0 for name in FEATURE_BASIS}
        features["POST_SWIPE_EMPTY_COUNT"] = empty_count
        predicted = _program_probability(program, features)
        target = target_v18.independently_replay_rank_two_probability_v18(empty_count)
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
        _fail("independent formula proof failed")
    payload = {
        "schema": "acfqp.standard_2048_context_program_proof.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": PREREGISTRATION_ID,
        "context_program_proposal_id": proposal["context_program_proposal_id"],
        "proposal_frozen_before_target_kernel_semantics_access": True,
        "proof_rows": rows,
        "proof_row_count": 16,
        "proof_mismatch_count": 0,
        "registered_empty_count_domain_complete": True,
        "exact_rational_formula_equivalence_proved": True,
        "proof_rows_not_counted_as_transition_observations": True,
    }
    return {
        **payload,
        "context_program_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN, payload
        ),
    }


def _world_expected(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_context_world_model.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": PREREGISTRATION_ID,
        "context_program_proposal_id": proposal["context_program_proposal_id"],
        "context_program_proof_id": proof["context_program_proof_id"],
        "swipe_world_model_id": SWIPE_WORLD_MODEL_ID,
        "swipe_program_key": "COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
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
        "context_world_model_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN, payload
        ),
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
        _fail("terminal value entered comparison")
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

    def action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        moved, merge = _swipe(board, action)
        features = _features(board, action, moved, merge)
        empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
        p2 = _program_probability(self.program, features)
        self.outcomes += 2 * len(empty)
        score = loss = Fraction()
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
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        if remaining == 0 or status == "WON":
            value = _Value(Fraction(), Fraction(), None)
        elif status == "LOST":
            value = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self.action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = value
        return value

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(self.action_value(state.board, action, HORIZON) for action in _actions(state.board))


class _DirectPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def action_value(self, state: Swipe2048State, action: Swipe2048Action, remaining: int) -> _Value:
        self.rows += 1
        outcomes = target_v18.apply_independently_replayed_target_outcomes_v18(state, action)
        self.outcomes += len(outcomes)
        score = loss = Fraction()
        for outcome in outcomes:
            value = self.state_value(
                outcome.next_state.board, outcome.next_state.status.value, remaining - 1
            )
            score += outcome.probability * (outcome.merge_score + value.score)
            loss += outcome.probability * value.loss
        return _Value(score, loss, action.value)

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or status == "WON":
            value = _Value(Fraction(), Fraction(), None)
        elif status == "LOST":
            value = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in legal_actions_v1(state.board):
                candidate = self.action_value(state, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = value
        return value

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(self.action_value(state, action, HORIZON) for action in legal_actions_v1(state.board))


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
        {
            "action": value.action,
            "expected_merge_score": _fdoc(value.score),
            "loss_probability_within_horizon": _fdoc(value.loss),
        }
        for value in values
    ]


def _verify_episode(
    task: tuple[int, dict[str, Any], Program, str]
) -> tuple[dict[str, Any], int, int]:
    episode_index, observed, program, world_model_id = task
    _verify_id(
        observed,
        "context_program_episode_id",
        CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN,
        "episode",
    )
    state = state_from_board_v1(TARGET_BOARDS[episode_index])
    initial_state = _state_document(state)
    model = _ModelPlanner(program)
    direct = _DirectPlanner()
    expected_decisions = []
    for decision_index in range(MAXIMUM_DECISIONS):
        model_before = (model.rows, model.outcomes, model.hits, model.misses)
        model_values = model.roots(state)
        selected = _best(model_values)
        certificate_payload = {
            "schema": "acfqp.standard_2048_context_plan_certificate.v20",
            "schema_version": SCHEMA_VERSION,
            "context_program_preregistration_id": PREREGISTRATION_ID,
            "context_world_model_id": world_model_id,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": HORIZON,
            "root_action_exact_values": _rows(model_values),
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
                CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN,
                certificate_payload,
            ),
        }
        direct_before = (direct.rows, direct.outcomes, direct.hits, direct.misses)
        direct_values = direct.roots(state)
        direct_best = _best(direct_values)
        if _rows(model_values) != _rows(direct_values) or selected.action != direct_best.action:
            _fail("independent model and target plans differ")
        outcome, tape = select_seeded_outcome_v1(
            target_v18.apply_independently_replayed_target_outcomes_v18(
                state, Swipe2048Action(selected.action)
            ),
            seed=TARGET_SEEDS[episode_index],
            decision_index=decision_index,
        )
        expected_decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "EXACT_CONTEXT_PROGRAM_WORLD_MODEL_CERTIFIED",
                "matched_cold_target_ground": {
                    "root_action_exact_values": _rows(direct_values),
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
        "context_program_preregistration_id": PREREGISTRATION_ID,
        "context_world_model_id": world_model_id,
        "episode_index": episode_index,
        "execution_seed": TARGET_SEEDS[episode_index],
        "initial_state": initial_state,
        "planning_horizon": HORIZON,
        "decisions": expected_decisions,
        "decision_count": 4,
        "context_model_certificate_count": 4,
        "local_ground_recovery_count": 0,
        "final_state": _state_document(state),
        "all_root_action_values_exactly_equal": True,
        "all_selected_actions_exact_value_and_loss_equivalent": True,
    }
    expected = {
        **payload,
        "context_program_episode_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN, payload
        ),
    }
    if observed != expected:
        _fail("episode differs from independent planning and target replay")
    return expected, direct.rows, direct.outcomes


def _verify_preregistration(document: Any) -> dict[str, Any]:
    row = _verify_id(
        document,
        "context_program_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN,
        "preregistration",
    )
    workload = row.get("heldout_planning_workload")
    if (
        row["context_program_preregistration_id"] != PREREGISTRATION_ID
        or row.get("outcome_fields_present") is not False
        or row.get("feature_or_program_selected") is not False
        or row.get("heldout_planning_executed") is not False
        or row.get("feature_basis") != list(FEATURE_BASIS)
        or type(workload) is not dict
        or workload.get("initial_boards") != [list(board) for board in TARGET_BOARDS]
        or workload.get("episode_seeds") != list(TARGET_SEEDS)
        or workload.get("planning_horizon") != HORIZON
    ):
        _fail("preregistration semantics changed")
    return row


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ContextProgramIndependentVerificationV20:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("context-program verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("context-program verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "context_program_verification_id"
        }
        if (
            document.get("context_program_verification_id") != self.verification_id
            or document.get("context_program_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("context-program verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("context-program verification is not an object")
        return document


def verify_standard_2048_context_program_bytes_independently_v20(
    canonical_bytes: bytes,
) -> Standard2048ContextProgramIndependentVerificationV20:
    try:
        observed = loads_canonical_json(canonical_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error(
            "context-program campaign bytes are not canonical"
        ) from error
    if type(observed) is not dict or canonical_json_bytes(observed) != canonical_bytes:
        _fail("context-program campaign bytes changed")
    root = _verify_id(
        observed,
        "context_program_campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN,
        "campaign",
    )
    if root["context_program_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("context-program campaign identity changed")
    preregistration = _verify_preregistration(root.get("context_program_preregistration"))
    archive = _archive_expected()
    if root.get("context_observation_archive") != archive:
        _fail("source context archive differs from independent replay")
    candidates = _candidates_expected(archive)
    proposal = _proposal_expected(archive, candidates)
    if root.get("context_program_proposal") != proposal:
        _fail("context program proposal differs from independent generation")
    proof = _proof_expected(proposal)
    if root.get("context_program_proof") != proof:
        _fail("postproposal exact proof differs from independent replay")
    world_model = _world_expected(proposal, proof)
    if root.get("context_world_model") != world_model:
        _fail("context world model differs from independently proved model")
    observed_episodes = root.get("episodes")
    if type(observed_episodes) is not list or len(observed_episodes) != 3:
        _fail("heldout episode inventory changed")
    program = _selected_program(proposal)
    tasks = tuple(
        (index, observed_episodes[index], program, world_model["context_world_model_id"])
        for index in range(3)
    )
    with ProcessPoolExecutor(max_workers=MAXIMUM_PROCESSES) as executor:
        replayed = list(executor.map(_verify_episode, tasks, chunksize=1))
    episodes = [row[0] for row in replayed]
    direct_rows = sum(row[1] for row in replayed)
    direct_outcomes = sum(row[2] for row in replayed)
    decisions = [row for episode in episodes for row in episode["decisions"]]
    payload = {
        "schema": "acfqp.standard_2048_context_program_campaign.v20",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "context_program_preregistration": preregistration,
        "context_observation_archive": archive,
        "context_program_proposal": proposal,
        "context_program_proof": proof,
        "context_world_model": world_model,
        "episodes": episodes,
        "episode_count": 3,
        "decision_count": 12,
        "source_context_probability_observation_count": 4,
        "generated_context_program_candidate_count": 12,
        "postproposal_exact_formula_proof_row_count": 16,
        "v19_matched_program_query_count": 4,
        "v19_strict_no_prior_query_count": 10,
        "retained_query_reduction_against_no_prior": 6,
        "context_program_query_fraction_of_no_prior": Fraction(2, 5),
        "context_feature_and_program_proposed_from_raw_observations": True,
        "preenumerated_context_program_candidate_list_used": False,
        "selected_feature_name": "POST_SWIPE_EMPTY_COUNT",
        "selected_threshold": 4,
        "selected_override_rank_two_probability": _fdoc(Fraction(1, 5)),
        "all_12_plans_in_observation_proposed_world_model": True,
        "all_12_root_action_values_exactly_match_cold_target_ground": True,
        "all_12_selected_actions_exactly_match_cold_target_ground": True,
        "operational_ground_distinction_query_count_during_planning": 0,
        "operational_ground_state_action_row_count_during_planning": 0,
        "online_target_transition_observation_count": 12,
        "evaluation_cold_target_ground_state_action_row_count": direct_rows,
        "evaluation_cold_target_ground_outcome_count": direct_outcomes,
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
            max(episode["final_state"]["board_ranks"]) >= 11 for episode in episodes
        ),
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    expected_root = {
        **payload,
        "context_program_campaign_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN, payload
        ),
    }
    if root != expected_root or expected_root["context_program_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("campaign differs from complete independent semantic reconstruction")
    verification_payload = {
        "schema": "acfqp.standard_2048_context_program_independent_verification.v20",
        "schema_version": SCHEMA_VERSION,
        "context_program_preregistration_id": PREREGISTRATION_ID,
        "context_program_campaign_id": EXPECTED_CAMPAIGN_ID,
        "context_observation_archive_id": archive["context_observation_archive_id"],
        "context_program_proposal_id": proposal["context_program_proposal_id"],
        "context_program_proof_id": proof["context_program_proof_id"],
        "context_world_model_id": world_model["context_world_model_id"],
        "four_raw_context_observations_independently_replayed": True,
        "twelve_postobservation_candidates_independently_generated": True,
        "unique_feature_threshold_program_independently_selected": True,
        "all_16_formula_rows_independently_proved": True,
        "all_12_h3_plans_independently_replanned": True,
        "all_12_target_transitions_independently_replayed": True,
        "all_root_values_and_actions_match_independent_target_ground": True,
        "retained_six_query_difference_against_v19_no_prior_verified": True,
        "open_ended_coordinate_invention_verified": False,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_broad_world_model_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN,
        verification_payload,
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen context-program verification identity changed")
    return Standard2048ContextProgramIndependentVerificationV20(
        _ISSUER,
        canonical_json_bytes(
            {**verification_payload, "context_program_verification_id": verification_id}
        ),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048ContextProgramIndependentVerifierV20Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ContextProgramIndependentVerificationV20",
    "verify_standard_2048_context_program_bytes_independently_v20",
)
