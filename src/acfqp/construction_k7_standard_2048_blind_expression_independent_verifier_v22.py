"""Producer-free replay of the V22 commit-reveal expression campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "22.0.0"
PREREGISTRATION_ID = "ac5bc17b69aad50e7b87461891f5bfe39125d2bb33b56cd39d5cc33bba674831"
TARGET_KERNEL_ID = "9c40dc9f4a33d2f8bdb008aad5af3fc43be228c7fb964cf137c53af03e962eb5"
SWIPE_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
EXPECTED_CAMPAIGN_ID = "85a0f59d0751dfcad87517ed8167d66943d4be0ab9159f78aeaaef7f85923c3e"
EXPECTED_VERIFICATION_ID = "6b60d2e7d4585716784a6b9a93c7511f96de2f4742ada0d61d6e1ec78aa2e7b2"
BASE_RATE = Fraction(1, 10)
OVERRIDE_RATE = Fraction(3, 20)
OVERRIDE_THRESHOLD = 2
HORIZON = 3
RAW_CONTEXT_POOL = (
    ((4, 3, 4, 3, 7, 5, 1, 5, 6, 2, 0, 7, 4, 1, 5, 5), "RIGHT"),
    ((0, 3, 5, 1, 3, 0, 7, 5, 6, 4, 2, 1, 7, 1, 6, 5), "RIGHT"),
    ((1, 0, 3, 5, 6, 6, 0, 7, 2, 1, 0, 1, 1, 1, 1, 6), "LEFT"),
    ((3, 0, 4, 0, 1, 4, 0, 0, 4, 4, 0, 4, 0, 0, 7, 5), "UP"),
    ((1, 0, 2, 1, 3, 6, 5, 5, 7, 7, 4, 5, 1, 5, 7, 7), "RIGHT"),
    ((0, 2, 4, 3, 4, 0, 4, 3, 0, 5, 0, 7, 4, 5, 0, 0), "UP"),
    ((2, 2, 0, 0, 7, 0, 0, 5, 0, 2, 5, 0, 3, 5, 2, 2), "LEFT"),
    ((4, 0, 5, 0, 3, 0, 0, 7, 7, 3, 0, 0, 5, 0, 0, 7), "RIGHT"),
)
TARGET_BOARDS = (
    (6, 1, 5, 1, 3, 6, 5, 6, 4, 2, 0, 2, 3, 1, 0, 4),
    (6, 0, 0, 3, 0, 2, 7, 4, 7, 2, 7, 0, 1, 2, 4, 7),
    (0, 4, 0, 3, 6, 2, 0, 5, 5, 0, 4, 0, 3, 2, 6, 0),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v181-blind-expression-target-{index:02d}-20260813"
    for index in range(3)
)
Candidate = tuple[str, dict[str, Any], int, Fraction, tuple[Fraction, ...]]


class ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error(ValueError):
    """The V22 bytes differ from independent synthesis, proof, or planning."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error(message)


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state document changed")
    state = Swipe2048State(tuple(document["board_ranks"]), Swipe2048Status(document["status"]))
    if state_from_board_v1(state.board) != state:
        _fail("state status changed")
    return state


def _swipe(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return swipe_v14.apply_independently_replayed_swipe_program_v14(board, action)


def _target_probability(post_board: tuple[int, ...]) -> Fraction:
    return OVERRIDE_RATE if post_board.count(1) <= OVERRIDE_THRESHOLD else BASE_RATE


def _target_outcomes(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    post, merge = _swipe(state.board, action.value)
    if post == state.board:
        _fail("independent target row received an illegal swipe")
    empty = tuple(index for index, rank in enumerate(post) if rank == 0)
    p2 = _target_probability(post)
    rows = []
    for cell in empty:
        for rank, mass in ((1, 1 - p2), (2, p2)):
            board = list(post)
            board[cell] = rank
            rows.append(
                Swipe2048Outcome(
                    mass / len(empty), state_from_board_v1(tuple(board)), merge, cell, rank
                )
            )
    return tuple(rows)


def _adjacent_equal_nonzero(board: tuple[int, ...]) -> int:
    return sum(
        1
        for row in range(4)
        for column in range(4)
        for dr, dc in ((0, 1), (1, 0))
        if row + dr < 4
        and column + dc < 4
        and board[row * 4 + column]
        and board[row * 4 + column] == board[(row + dr) * 4 + column + dc]
    )


def _expressions(
    pre_board: tuple[int, ...], action: str, post_board: tuple[int, ...],
    merge_score: int, constants: tuple[int, ...],
) -> list[dict[str, Any]]:
    result = []
    for source, board in (
        ("PRE_BOARD_RANKS", pre_board),
        ("POST_SWIPE_BOARD_RANKS", post_board),
    ):
        for constant in constants:
            result.append(
                {
                    "expression_key": f"COUNT_EQ({source},{constant})",
                    "expression_ast": {
                        "operator": "COUNT_EQ", "vector_source": source, "constant": constant
                    },
                    "value": board.count(constant),
                }
            )
        for operator, value in (
            ("MAX", max(board)),
            ("SUM", sum(board)),
            ("DISTINCT_NONZERO_COUNT", len(set(board) - {0})),
            ("ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT", _adjacent_equal_nonzero(board)),
        ):
            result.append(
                {
                    "expression_key": f"{operator}({source})",
                    "expression_ast": {"operator": operator, "vector_source": source},
                    "value": value,
                }
            )
    result.extend(
        (
            {
                "expression_key": "MERGE_SCORE",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "MERGE_SCORE"},
                "value": merge_score,
            },
            {
                "expression_key": "ACTION_ORDINAL",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "ACTION_ORDINAL"},
                "value": tuple(item.value for item in ACTION_ORDER).index(action),
            },
        )
    )
    return result


def _pool_expected() -> dict[str, Any]:
    raw = []
    constants = set()
    for ordinal, (board, action) in enumerate(RAW_CONTEXT_POOL):
        post, merge = _swipe(board, action)
        raw.append((ordinal, board, action, post, merge))
        constants.update(board)
        constants.update(post)
    frozen = tuple(sorted(constants))
    rows = []
    for ordinal, board, action, post, merge in raw:
        payload = {
            "pool_ordinal": ordinal,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post),
            "merge_score": merge,
            "expression_values": _expressions(board, action, post, merge, frozen),
        }
        rows.append(
            {
                **payload,
                "structural_context_sha256": hashlib.sha256(
                    canonical_json_bytes(payload)
                ).hexdigest(),
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_blind_structural_pool.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "target_kernel_commitment_id": TARGET_KERNEL_ID,
        "swipe_world_model_id": SWIPE_WORLD_MODEL_ID,
        "observed_raw_rank_constants": list(frozen),
        "rows": rows,
        "context_count": 8,
        "expression_count_per_context": len(rows[0]["expression_values"]),
        "all_structural_values_frozen_before_first_probability_query": True,
        "target_semantics_source_or_reveal_present": False,
        "named_target_specific_feature_present": False,
    }
    return {
        **payload,
        "blind_structural_pool_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN, payload
        ),
    }


def _expression_maps(pool: dict[str, Any]) -> tuple[tuple[str, dict[str, Any], tuple[int, ...]], ...]:
    first = pool["rows"][0]["expression_values"]
    return tuple(
        (
            expression["expression_key"],
            expression["expression_ast"],
            tuple(row["expression_values"][index]["value"] for row in pool["rows"]),
        )
        for index, expression in enumerate(first)
    )


def _candidates_expected(
    pool: dict[str, Any], override: Fraction
) -> tuple[list[dict[str, Any]], tuple[Candidate, ...]]:
    artifacts = []
    native = []
    ordinal = 0
    for key, ast, values in _expression_maps(pool):
        for threshold in sorted(set(values)):
            predictions = tuple(override if value <= threshold else BASE_RATE for value in values)
            if len(set(predictions)) == 1:
                continue
            payload = {
                "schema": "acfqp.standard_2048_blind_expression_candidate.v22",
                "schema_version": SCHEMA_VERSION,
                "blind_expression_preregistration_id": PREREGISTRATION_ID,
                "blind_structural_pool_id": pool["blind_structural_pool_id"],
                "candidate_ordinal": ordinal,
                "expression_key": key,
                "expression_ast": ast,
                "threshold": threshold,
                "program_schema": "IF_EXPRESSION_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
                "base_rank_two_probability": BASE_RATE,
                "override_rank_two_probability": override,
                "expression_values_over_frozen_pool": list(values),
                "predictions_over_frozen_pool": list(predictions),
                "constant_prediction_candidate": False,
                "expression_and_threshold_generated_from_structural_pool": True,
                "target_formula_used_to_generate_candidate": False,
            }
            artifacts.append(
                {
                    **payload,
                    "blind_expression_candidate_id": content_id(
                        CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN,
                        payload,
                    ),
                }
            )
            native.append((key, ast, threshold, override, predictions))
            ordinal += 1
    return artifacts, tuple(native)


def _acquisition_expected(
    pool: dict[str, Any], ordinal: int, query: int,
    before: int | None, after: int, generated: bool,
) -> dict[str, Any]:
    row = pool["rows"][ordinal]
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_acquisition.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "target_kernel_commitment_id": TARGET_KERNEL_ID,
        "query_ordinal": query,
        "pool_ordinal": ordinal,
        "structural_context_sha256": row["structural_context_sha256"],
        "observed_rank_two_probability": _target_probability(tuple(row["post_swipe_board_ranks"])),
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidates_generated_after_this_query": generated,
        "context_and_all_expression_values_frozen_before_query": True,
        "query_interface_received_raw_post_swipe_board": True,
        "target_formula_used_by_acquisition_rule": False,
        "target_query_returns_scalar_label_only": True,
        "full_state_action_outcome_row_materialized": False,
    }
    return {
        **payload,
        "blind_expression_acquisition_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN, payload
        ),
    }


def _acquire_expected(
    pool: dict[str, Any], candidates: tuple[Candidate, ...]
) -> tuple[list[dict[str, Any]], Candidate]:
    first = _target_probability(tuple(pool["rows"][0]["post_swipe_board_ranks"]))
    remaining = tuple(candidate for candidate in candidates if candidate[4][0] == first)
    queried = [0]
    rows = [_acquisition_expected(pool, 0, 0, None, len(remaining), True)]
    while len(remaining) > 1:
        choices = []
        for ordinal in range(8):
            if ordinal in queried:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                value = candidate[4][ordinal]
                buckets[value] = buckets.get(value, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), ordinal))
        if not choices:
            _fail("independent minimax acquisition cannot separate candidates")
        _, ordinal = min(choices)
        queried.append(ordinal)
        before = remaining
        observed = _target_probability(tuple(pool["rows"][ordinal]["post_swipe_board_ranks"]))
        remaining = tuple(candidate for candidate in remaining if candidate[4][ordinal] == observed)
        rows.append(
            _acquisition_expected(pool, ordinal, len(rows), len(before), len(remaining), False)
        )
    if len(rows) != 4 or len(remaining) != 1:
        _fail("independent V22 acquisition outcome changed")
    return rows, remaining[0]


def _proposal_expected(
    pool: dict[str, Any], artifacts: list[dict[str, Any]],
    acquisitions: list[dict[str, Any]], selected: Candidate,
) -> dict[str, Any]:
    artifact = next(
        row for row in artifacts
        if row["expression_key"] == selected[0]
        and row["expression_ast"] == selected[1]
        and row["threshold"] == selected[2]
    )
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_proposal.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "target_kernel_commitment_id": TARGET_KERNEL_ID,
        "candidate_artifacts": artifacts,
        "candidate_count": len(artifacts),
        "acquisition_ids": [row["blind_expression_acquisition_id"] for row in acquisitions],
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_candidate_id": artifact["blind_expression_candidate_id"],
        "selected_expression_key": selected[0],
        "selected_expression_ast": selected[1],
        "selected_threshold": selected[2],
        "selected_base_rank_two_probability": BASE_RATE,
        "selected_override_rank_two_probability": selected[3],
        "unique_program_consistent_with_queried_contexts": True,
        "transferred_v21_grammar_and_query_rule_unchanged": True,
        "target_formula_used_to_select_program": False,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "blind_expression_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN, payload
        ),
    }


def _kernel_expected() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_commit_reveal_target_kernel.v22",
        "schema_version": SCHEMA_VERSION,
        "board_shape": [4, 4],
        "deterministic_swipe_semantics": "STANDARD_2048_WHOLE_BOARD_SWIPE_V1",
        "spawn_cell_law": "UNIFORM_OVER_POST_SWIPE_EMPTY_CELLS",
        "rank_two_law": {
            "base_probability": BASE_RATE,
            "override_expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 1,
            },
            "override_predicate": "EXPRESSION_VALUE_LE_THRESHOLD",
            "override_threshold": OVERRIDE_THRESHOLD,
            "override_probability": OVERRIDE_RATE,
        },
        "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        "exact_rational_arithmetic": True,
        "commit_reveal_protocol": (
            "TARGET_SEMANTICS_ABSENT_FROM_PREREGISTRATION_COMMIT_AND_REVEALED_ONLY_IN_SUCCESSOR_COMMIT"
        ),
    }
    return {
        **payload,
        "target_kernel_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN, payload
        ),
    }


def _proof_expected(proposal: dict[str, Any]) -> dict[str, Any]:
    revealed = _kernel_expected()
    rows = []
    for value in range(17):
        probability = OVERRIDE_RATE if value <= OVERRIDE_THRESHOLD else BASE_RATE
        rows.append(
            {
                "expression_value": value,
                "predicted_rank_two_probability": probability,
                "revealed_target_rank_two_probability": probability,
                "exact_match": True,
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_proof.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "blind_expression_proposal_id": proposal["blind_expression_proposal_id"],
        "target_kernel_commitment_id": TARGET_KERNEL_ID,
        "revealed_target_kernel": revealed,
        "proposal_frozen_before_postproposal_formula_comparison": True,
        "commitment_exactly_validated_before_proof": True,
        "proof_rows": rows,
        "proof_row_count": 17,
        "proof_mismatch_count": 0,
        "exact_expression_program_equivalence_proved": True,
        "proof_rows_not_counted_as_target_probability_queries": True,
    }
    return {
        **payload,
        "blind_expression_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN, payload
        ),
    }


def _world_expected(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_world_model.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "blind_expression_proposal_id": proposal["blind_expression_proposal_id"],
        "blind_expression_proof_id": proof["blind_expression_proof_id"],
        "target_kernel_id": TARGET_KERNEL_ID,
        "swipe_world_model_id": SWIPE_WORLD_MODEL_ID,
        "expression_ast": proposal["selected_expression_ast"],
        "threshold": proposal["selected_threshold"],
        "base_probability": BASE_RATE,
        "override_probability": OVERRIDE_RATE,
        "exact_over_committed_and_revealed_target": True,
        "reusable_across_fresh_states_actions_and_episodes": True,
        "serialized_full_state_action_table_present": False,
        "open_ended_expression_language_claimed": False,
    }
    return {
        **payload,
        "blind_expression_world_model_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN, payload
        ),
    }


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
def _actions(board: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(
        action.value for action in ACTION_ORDER if _swipe(board, action.value)[0] != board
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
    order = tuple(action.value for action in ACTION_ORDER)
    if candidate.action is None or current.action is None:
        _fail("terminal value entered action comparison")
    return (candidate.score, -candidate.loss, -order.index(candidate.action)) > (
        current.score, -current.loss, -order.index(current.action)
    )


class _Planner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        self.rows += 1
        post, merge = _swipe(board, action)
        empty = tuple(index for index, rank in enumerate(post) if rank == 0)
        p2 = _target_probability(post)
        self.outcomes += 2 * len(empty)
        score = loss = Fraction()
        for cell in empty:
            for rank, mass in ((1, 1 - p2), (2, p2)):
                child = list(post)
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
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        if remaining == 0 or status == Swipe2048Status.WON.value:
            result = _Value(Fraction(), Fraction(), None)
        elif status == Swipe2048Status.LOST.value:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self.action_value(board, action, remaining)
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def roots(self, state: Swipe2048State) -> tuple[_Value, ...]:
        return tuple(self.action_value(state.board, action, HORIZON) for action in _actions(state.board))


def _root_replay(state: Swipe2048State) -> dict[str, Any]:
    planner = _Planner()
    values = planner.roots(state)
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no independent action")
    return {
        "root_action_exact_values": [
            {
                "action": value.action,
                "expected_merge_score": value.score,
                "loss_probability_within_horizon": value.loss,
            }
            for value in values
        ],
        "selected_action": best.action,
        "selected_expected_merge_score": best.score,
        "selected_loss_probability_within_horizon": best.loss,
        "action_rows": planner.rows,
        "outcomes": planner.outcomes,
        "hits": planner.hits,
        "misses": planner.misses,
    }


def _verify_episodes(observed: Any, world_id: str) -> tuple[int, int]:
    if type(observed) is not list or len(observed) != 3:
        _fail("blind episode inventory changed")
    decision_count = 0
    for episode_index, episode in enumerate(observed):
        _verify_id(
            episode,
            "blind_expression_episode_id",
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN,
            "episode",
        )
        state = state_from_board_v1(TARGET_BOARDS[episode_index])
        if (
            episode.get("episode_index") != episode_index
            or episode.get("execution_seed") != TARGET_SEEDS[episode_index]
            or _state(episode.get("initial_state")) != state
            or episode.get("blind_expression_world_model_id") != world_id
        ):
            _fail("blind episode identity changed")
        decisions = episode.get("decisions")
        if type(decisions) is not list or len(decisions) != 4:
            _fail("blind episode decision inventory changed")
        for decision_index, decision in enumerate(decisions):
            replay = _root_replay(state)
            certificate = _verify_id(
                decision.get("certificate"),
                "blind_expression_certificate_id",
                CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN,
                "certificate",
            )
            if (
                decision.get("decision_index") != decision_index
                or _state(decision.get("predecision_state")) != state
                or certificate.get("root_state") != decision.get("predecision_state")
                or certificate.get("root_action_exact_values") != replay["root_action_exact_values"]
                or certificate.get("selected_action") != replay["selected_action"]
                or certificate.get("selected_expected_merge_score")
                != replay["selected_expected_merge_score"]
                or certificate.get("selected_loss_probability_within_horizon")
                != replay["selected_loss_probability_within_horizon"]
                or certificate.get("factored_action_row_evaluation_count") != replay["action_rows"]
                or certificate.get("factored_support_outcome_evaluation_count") != replay["outcomes"]
                or certificate.get("subproof_cache_hit_count") != replay["hits"]
                or certificate.get("subproof_cache_miss_count") != replay["misses"]
                or certificate.get("operational_target_probability_query_count") != 0
                or certificate.get("operational_ground_state_action_row_count") != 0
                or certificate.get("status")
                != "CERTIFIED_COMMIT_REVEAL_EXPRESSION_WORLD_MODEL_H3"
            ):
                _fail("blind certificate differs from independent H3 replay")
            control = decision.get("matched_cold_target_ground")
            expected_control = {
                "root_action_exact_values": replay["root_action_exact_values"],
                "selected_action": replay["selected_action"],
                "selected_expected_merge_score": replay["selected_expected_merge_score"],
                "selected_loss_probability_within_horizon": replay[
                    "selected_loss_probability_within_horizon"
                ],
                "ground_state_action_row_count": replay["action_rows"],
                "ground_outcome_count": replay["outcomes"],
                "subproof_cache_hit_count": replay["hits"],
                "subproof_cache_miss_count": replay["misses"],
                "lane": "STANDALONE_EVALUATION_ONLY",
                "route_or_certificate_authority": False,
            }
            if (
                control != expected_control
                or decision.get("route") != "EXACT_COMMIT_REVEAL_EXPRESSION_MODEL_CERTIFIED"
                or decision.get("all_root_action_values_exactly_equal") is not True
                or decision.get("selected_action_exact_value_and_loss_equivalent") is not True
                or decision.get("certificate_frozen_before_cold_evaluation_and_target_transition")
                is not True
            ):
                _fail("blind cold-target comparison changed")
            outcome, tape = select_seeded_outcome_v1(
                _target_outcomes(state, Swipe2048Action(replay["selected_action"])),
                seed=TARGET_SEEDS[episode_index],
                decision_index=decision_index,
            )
            if (
                decision.get("executed_action") != replay["selected_action"]
                or decision.get("execution_tape_sha256") != tape
                or _state(decision.get("executed_next_state")) != outcome.next_state
                or decision.get("online_target_transition_observation_count") != 1
                or decision.get("execution_transition_used_to_modify_world_model") is not False
            ):
                _fail("blind target transition differs from independent replay")
            state = outcome.next_state
            decision_count += 1
        if (
            _state(episode.get("final_state")) != state
            or episode.get("decision_count") != 4
            or episode.get("model_certificate_count") != 4
            or episode.get("local_ground_recovery_count") != 0
            or episode.get("all_root_action_values_exactly_equal") is not True
            or episode.get("all_selected_actions_exact_value_and_loss_equivalent") is not True
        ):
            _fail("blind episode closure changed")
    return len(observed), decision_count


def _verify_preregistration(document: Any) -> None:
    row = _verify_id(
        document,
        "blind_expression_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN,
        "preregistration",
    )
    raw = [
        {"pool_ordinal": index, "pre_state_board_ranks": list(board), "action": action}
        for index, (board, action) in enumerate(RAW_CONTEXT_POOL)
    ]
    if (
        row["blind_expression_preregistration_id"] != PREREGISTRATION_ID
        or row.get("raw_context_pool") != raw
        or row.get("target_commitment", {}).get("target_kernel_commitment_id")
        != TARGET_KERNEL_ID
        or row.get("target_commitment", {}).get("target_semantics_document_present") is not False
        or row.get("target_commitment", {}).get("target_kernel_source_present") is not False
        or row.get("active_acquisition", {}).get("maximum_target_probability_queries") != 4
        or row.get("postproposal_reveal_and_proof", {}).get(
            "target_reveal_source_access_before_proposal_freeze"
        )
        is not False
        or row.get("outcome_fields_present") is not False
        or row.get("target_revealed") is not False
        or row.get("target_probability_query_count") != 0
        or row.get("expression_program_selected") is not False
        or row.get("open_ended_expression_invention_claimed") is not False
    ):
        _fail("blind preregistration or commitment locks changed")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048BlindExpressionIndependentVerificationV22:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("blind independent verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("blind independent verification bytes changed")
        payload = {
            key: value for key, value in document.items()
            if key != "blind_expression_verification_id"
        }
        if (
            document.get("blind_expression_verification_id") != self.verification_id
            or document.get("blind_expression_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("blind independent verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("blind independent verification is not an object")
        return document


def verify_standard_2048_blind_expression_bytes_independently_v22(
    canonical_bytes: bytes,
) -> Standard2048BlindExpressionIndependentVerificationV22:
    try:
        observed = loads_canonical_json(canonical_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error(
            "blind campaign bytes are not canonical"
        ) from error
    if canonical_json_bytes(observed) != canonical_bytes:
        _fail("blind campaign bytes are noncanonical")
    root = _verify_id(
        observed,
        "blind_expression_campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN,
        "campaign",
    )
    if root["blind_expression_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("blind campaign identity changed")
    _verify_preregistration(root.get("blind_expression_preregistration"))
    revealed = _kernel_expected()
    if revealed["target_kernel_id"] != TARGET_KERNEL_ID or root.get("revealed_target_kernel") != revealed:
        _fail("revealed target differs from committed independent semantics")
    pool = _pool_expected()
    if root.get("structural_pool") != pool:
        _fail("blind structural pool differs from independent generation")
    first = _target_probability(tuple(pool["rows"][0]["post_swipe_board_ranks"]))
    artifacts, candidates = _candidates_expected(pool, first)
    acquisitions, selected = _acquire_expected(pool, candidates)
    if root.get("acquisitions") != acquisitions:
        _fail("blind active acquisitions differ from independent replay")
    proposal = _proposal_expected(pool, artifacts, acquisitions, selected)
    if root.get("proposal") != proposal:
        _fail("blind expression proposal differs from independent synthesis")
    proof = _proof_expected(proposal)
    if root.get("proof") != proof:
        _fail("blind post-reveal proof differs from independent proof")
    world = _world_expected(proposal, proof)
    if root.get("world_model") != world:
        _fail("blind world model differs from independent reconstruction")
    episodes, decisions = _verify_episodes(
        root.get("episodes"), world["blind_expression_world_model_id"]
    )
    if (
        episodes != 3
        or decisions != 12
        or root.get("generated_primitive_expression_count") != 28
        or root.get("generated_expression_program_candidate_count") != 80
        or root.get("target_probability_query_count") != 4
        or root.get("queried_pool_ordinals") != [0, 2, 4, 1]
        or root.get("version_space_counts_after_queries") != [35, 19, 8, 1]
        or root.get("selected_expression_key") != "COUNT_EQ(POST_SWIPE_BOARD_RANKS,1)"
        or root.get("selected_threshold") != 2
        or root.get("postproposal_exact_proof_row_count") != 17
        or root.get("query_reduction_against_no_prior") != 4
        or root.get("query_fraction_of_no_prior") != Fraction(1, 2)
        or root.get("git_ordered_commit_reveal_protocol_satisfied") is not True
        or root.get("experimenter_cognitive_blinding_claimed") is not False
        or root.get("runtime_target_source_access_isolation_enforced") is not False
        or root.get("open_ended_expression_or_coordinate_invention_completed") is not False
        or root.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or root.get("official_execution_allowed") is not False
    ):
        _fail("blind campaign aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_blind_expression_independent_verification.v22",
        "schema_version": SCHEMA_VERSION,
        "blind_expression_preregistration_id": PREREGISTRATION_ID,
        "target_kernel_commitment_id": TARGET_KERNEL_ID,
        "blind_expression_campaign_id": EXPECTED_CAMPAIGN_ID,
        "blind_structural_pool_id": pool["blind_structural_pool_id"],
        "blind_expression_proposal_id": proposal["blind_expression_proposal_id"],
        "blind_expression_proof_id": proof["blind_expression_proof_id"],
        "blind_expression_world_model_id": world["blind_expression_world_model_id"],
        "commitment_and_reveal_semantics_independently_recomputed": True,
        "twenty_eight_primitive_expressions_independently_generated": True,
        "eighty_program_candidates_independently_generated": True,
        "four_minimax_queries_independently_replayed": True,
        "unique_count_eq_post_one_expression_independently_selected": True,
        "all_17_formula_rows_independently_proved": True,
        "all_12_h3_root_values_actions_and_transitions_independently_replayed": True,
        "four_query_difference_against_strict_no_prior_verified": True,
        "experimenter_cognitive_blinding_verified": False,
        "runtime_target_source_access_isolation_verified": False,
        "open_ended_expression_invention_verified": False,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_broad_world_model_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN, payload
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen blind independent verification identity changed")
    return Standard2048BlindExpressionIndependentVerificationV22(
        _ISSUER,
        canonical_json_bytes({**payload, "blind_expression_verification_id": verification_id}),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048BlindExpressionIndependentVerifierV22Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048BlindExpressionIndependentVerificationV22",
    "verify_standard_2048_blind_expression_bytes_independently_v22",
)
