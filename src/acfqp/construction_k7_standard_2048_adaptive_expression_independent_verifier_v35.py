"""Producer-free semantic replay of the V35 adaptive 2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

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
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "35.0.0"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_campaign_v35"
PREREGISTRATION_ID = "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
PREREGISTRATION_BYTE_COUNT = 8329
PREREGISTRATION_SHA256 = "3e68f1b7d47e91783a9a00dea50ca9ea1fcbaef7d613a99f78b853d17363388e"
TARGET_KERNEL_ID = "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"
V34_ACCOUNTED_CAMPAIGN_ID = "0" * 64
V34_ACCOUNTING_VERIFICATION_ID = "0" * 64
EXPECTED_CAMPAIGN_ID = "0" * 64
EXPECTED_CAMPAIGN_BYTE_COUNT = 0
EXPECTED_CAMPAIGN_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64
HORIZON = 3
MAXIMUM_DECISIONS = 128
COLD_CHECKPOINTS = (0, 63, 127)
BASE_RATE = Fraction(1, 10)
OVERRIDE_RATE = Fraction(1, 4)
OVERRIDE_THRESHOLD = 1
TARGET_EXPRESSION_AST = {
    "operator": "COUNT_EQ",
    "vector_source": "POST_SWIPE_BOARD_RANKS",
    "constant": 2,
}
INITIAL_BOARDS = (
    (2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
EPISODE_SEEDS = tuple(
    f"standard-2048-v193-adaptive-expression-repair-{index:02d}-20260814"
    for index in range(4)
)
PROPOSED_CONTRACT_VERSION = "2.0.193"
V35_REGISTERED_V34_PREREGISTRATION_ID = (
    "9a02a999b32b3753c4cbfc9dde0baf7b783f661e696875d5bbf97d986bbc3fc5"
)
EXECUTED_V34R1_PREREGISTRATION_ID = (
    "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_preregistration_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_runtime_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/domains/standard_2048.py",
)
_VECTOR_SOURCES = ("PRE_BOARD_RANKS", "POST_SWIPE_BOARD_RANKS")
_UNARY_REDUCERS = (
    "MAX",
    "SUM",
    "DISTINCT_NONZERO_COUNT",
    "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT",
)
_DIRECTIONS = ("LE_OVERRIDE", "GT_OVERRIDE")


class ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error(
    ValueError
):
    """The campaign differs from independent acquisition, proof, or planning."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error(
        message
    )


def _verify_id(
    document: Any, id_key: str, domain: str, label: str
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state document changed")
    try:
        state = Swipe2048State(
            tuple(document["board_ranks"]), Swipe2048Status(document["status"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error(
            "state value changed"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("state status differs from board")
    return state


def _swipe(board: tuple[int, ...], action: str) -> tuple[tuple[int, ...], int]:
    return swipe_v14.apply_independently_replayed_swipe_program_v14(board, action)


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
        action.value
        for action in ACTION_ORDER
        if _swipe(board, action.value)[0] != board
    )


@lru_cache(maxsize=None)
def _status(board: tuple[int, ...]) -> str:
    if max(board) >= GOAL_RANK:
        return Swipe2048Status.WON.value
    return Swipe2048Status.ACTIVE.value if _actions(board) else Swipe2048Status.LOST.value


def _target_probability(post_board: tuple[int, ...]) -> Fraction:
    return OVERRIDE_RATE if post_board.count(2) <= OVERRIDE_THRESHOLD else BASE_RATE


def _target_outcomes(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    post, merge = _swipe(state.board, action.value)
    if post == state.board:
        _fail("target outcome replay received an illegal swipe")
    empty = tuple(index for index, rank in enumerate(post) if rank == 0)
    p2 = _target_probability(post)
    rows = []
    for cell in empty:
        for rank, mass in ((1, 1 - p2), (2, p2)):
            board = list(post)
            board[cell] = rank
            rows.append(
                Swipe2048Outcome(
                    mass / len(empty),
                    state_from_board_v1(tuple(board)),
                    merge,
                    cell,
                    rank,
                )
            )
    return tuple(rows)


def _target_document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_target.v35",
        "schema_version": SCHEMA_VERSION,
        "spawn_rank_support": [1, 2],
        "base_rank_two_probability": BASE_RATE,
        "override_expression_ast": TARGET_EXPRESSION_AST,
        "override_relation": "LESS_THAN_OR_EQUAL",
        "override_threshold": OVERRIDE_THRESHOLD,
        "override_rank_two_probability": OVERRIDE_RATE,
        "rank_one_probability_is_exact_complement": True,
    }
    return {
        **payload,
        "target_kernel_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
            payload,
        ),
    }


def _context(board: tuple[int, ...], action: str) -> dict[str, Any]:
    post, merge = _swipe(board, action)
    if post == board:
        _fail("raw frontier contains an illegal swipe")
    payload = {
        "pre_state_board_ranks": list(board),
        "action": action,
        "post_swipe_board_ranks": list(post),
        "merge_score": merge,
    }
    return {
        **payload,
        "structural_context_sha256": hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _frontier(state: Swipe2048State) -> tuple[dict[str, Any], ...]:
    contexts: dict[str, dict[str, Any]] = {}
    expanded: set[tuple[tuple[int, ...], str, int]] = set()

    def visit(current: Swipe2048State, remaining: int, *, root: bool) -> None:
        if remaining == 0 or current.status is not Swipe2048Status.ACTIVE:
            return
        working = current if root else state_from_board_v1(_canonical(current.board))
        key = (working.board, working.status.value, remaining)
        if key in expanded:
            return
        expanded.add(key)
        for action in _actions(working.board):
            context = _context(working.board, action)
            context_id = context["structural_context_sha256"]
            contexts.setdefault(context_id, context)
            post = tuple(context["post_swipe_board_ranks"])
            for cell, rank in (
                (cell, rank)
                for cell, value in enumerate(post)
                if value == 0
                for rank in (1, 2)
            ):
                child = list(post)
                child[cell] = rank
                visit(state_from_board_v1(tuple(child)), remaining - 1, root=False)

    visit(state, HORIZON, root=True)
    return tuple(contexts[key] for key in sorted(contexts))


def _adjacent_equal_nonzero(board: tuple[int, ...]) -> int:
    return sum(
        1
        for row in range(4)
        for column in range(4)
        for dr, dc in ((0, 1), (1, 0))
        if row + dr < 4
        and column + dc < 4
        and board[row * 4 + column]
        and board[row * 4 + column]
        == board[(row + dr) * 4 + column + dc]
    )


def _expression_specs(
    contexts: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    constants = sorted(
        {
            rank
            for context in contexts
            for field in ("pre_state_board_ranks", "post_swipe_board_ranks")
            for rank in context[field]
        }
    )
    result = []
    for source in _VECTOR_SOURCES:
        result.extend(
            {
                "operator": "COUNT_EQ",
                "vector_source": source,
                "constant": constant,
            }
            for constant in constants
        )
        result.extend(
            {"operator": operator, "vector_source": source}
            for operator in _UNARY_REDUCERS
        )
    result.extend(
        {"operator": "RAW_SCALAR", "source": source}
        for source in ("MERGE_SCORE", "ACTION_ORDINAL")
    )
    return tuple(sorted(result, key=canonical_json_bytes))


def _expression(ast: Mapping[str, Any], context: Mapping[str, Any]) -> int:
    source_name = ast.get("vector_source")
    board = (
        tuple(context["pre_state_board_ranks"])
        if source_name == "PRE_BOARD_RANKS"
        else tuple(context["post_swipe_board_ranks"])
        if source_name == "POST_SWIPE_BOARD_RANKS"
        else None
    )
    operator = ast.get("operator")
    if operator == "COUNT_EQ" and board is not None and set(ast) == {
        "operator",
        "vector_source",
        "constant",
    }:
        return board.count(ast["constant"])
    if board is not None and set(ast) == {"operator", "vector_source"}:
        if operator == "MAX":
            return max(board)
        if operator == "SUM":
            return sum(board)
        if operator == "DISTINCT_NONZERO_COUNT":
            return len(set(board) - {0})
        if operator == "ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT":
            return _adjacent_equal_nonzero(board)
    if operator == "RAW_SCALAR" and set(ast) == {"operator", "source"}:
        if ast["source"] == "MERGE_SCORE":
            return context["merge_score"]
        if ast["source"] == "ACTION_ORDINAL":
            return tuple(item.value for item in ACTION_ORDER).index(context["action"])
    _fail("expression is outside the registered depth-one grammar")


Candidate = tuple[str, dict[str, Any], int, Fraction, str]


def _candidate_document(candidate: Candidate) -> dict[str, Any]:
    identity, ast, threshold, override, direction = candidate
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_candidate.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "expression_ast": ast,
        "threshold": threshold,
        "direction": direction,
        "base_rank_two_probability": BASE_RATE,
        "override_rank_two_probability": override,
        "expression_and_threshold_generated_from_frozen_raw_contexts": True,
        "override_probability_generated_from_acquired_label": True,
        "target_formula_used_to_generate_candidate": False,
    }
    if identity != content_id(
        CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN,
        payload,
    ):
        _fail("independent candidate identity changed")
    return {**payload, "expression_candidate_id": identity}


def _candidate(
    ast: dict[str, Any], threshold: int, override: Fraction, direction: str
) -> Candidate:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_candidate.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "expression_ast": ast,
        "threshold": threshold,
        "direction": direction,
        "base_rank_two_probability": BASE_RATE,
        "override_rank_two_probability": override,
        "expression_and_threshold_generated_from_frozen_raw_contexts": True,
        "override_probability_generated_from_acquired_label": True,
        "target_formula_used_to_generate_candidate": False,
    }
    return (
        content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN,
            payload,
        ),
        ast,
        threshold,
        override,
        direction,
    )


def _predict(candidate: Candidate, context: Mapping[str, Any]) -> Fraction:
    _, ast, threshold, override, direction = candidate
    value = _expression(ast, context)
    use_override = value <= threshold if direction == "LE_OVERRIDE" else value > threshold
    return override if use_override else BASE_RATE


def _generate(
    contexts: tuple[dict[str, Any], ...], labels: Mapping[str, Fraction]
) -> tuple[tuple[Candidate, ...], dict[str, int]]:
    by_id = {row["structural_context_sha256"]: row for row in contexts}
    overrides = tuple(sorted(set(labels.values()) - {BASE_RATE}))
    checks = values_evaluated = 0
    candidates: dict[str, Candidate] = {}
    for ast in _expression_specs(contexts):
        values = tuple(_expression(ast, context) for context in contexts)
        values_evaluated += len(contexts)
        for threshold in sorted(set(values)):
            for override in overrides:
                for direction in _DIRECTIONS:
                    candidate = _candidate(ast, threshold, override, direction)
                    predictions = tuple(_predict(candidate, row) for row in contexts)
                    values_evaluated += len(contexts)
                    if len(set(predictions)) == 1:
                        continue
                    consistent = True
                    for context_id, observed in labels.items():
                        checks += 1
                        if _predict(candidate, by_id[context_id]) != observed:
                            consistent = False
                            break
                    if consistent:
                        candidates[candidate[0]] = candidate
    ordered = tuple(candidates[key] for key in sorted(candidates))
    return ordered, {
        "model.structural_context_rows_frozen": len(contexts),
        "model.structural_expression_value_evaluations": values_evaluated,
        "model.expression_candidates_materialized": len(ordered),
        "model.candidate_label_consistency_checks": checks,
    }


def _filter(
    candidates: tuple[Candidate, ...],
    context: Mapping[str, Any],
    observed: Fraction,
) -> tuple[tuple[Candidate, ...], int]:
    retained = []
    checks = 0
    for candidate in candidates:
        checks += 1
        if _predict(candidate, context) == observed:
            retained.append(candidate)
    return tuple(retained), checks


def _local_decision(
    contexts: tuple[dict[str, Any], ...],
    candidates: tuple[Candidate, ...],
    labels: Mapping[str, Fraction],
) -> tuple[str, str | None, str | None, int]:
    if not any(value != BASE_RATE for value in labels.values()):
        choices = tuple(
            row["structural_context_sha256"]
            for row in contexts
            if row["structural_context_sha256"] not in labels
        )
        return "QUERY_REQUIRED_NO_NONBASE_LABEL", None, min(choices), 0
    if not candidates:
        return "COLD_GROUND_FALLBACK_EMPTY_VERSION_SPACE", None, None, 0
    predictions = tuple(
        tuple(_predict(candidate, context) for candidate in candidates)
        for context in contexts
    )
    evaluations = len(contexts) * len(candidates)
    differing = tuple(
        (context, row)
        for context, row in zip(contexts, predictions, strict=True)
        if len(set(row)) > 1
    )
    if not differing:
        selected = min(candidates, key=lambda item: item[0])
        return "LOCALLY_CERTIFIED_ALL_SURVIVORS_AGREE", selected[0], None, evaluations
    choices = []
    for context, row in differing:
        context_id = context["structural_context_sha256"]
        if context_id in labels:
            continue
        buckets: dict[Fraction, int] = {}
        for value in row:
            buckets[value] = buckets.get(value, 0) + 1
        choices.append((max(buckets.values()), -len(buckets), context_id))
    if not choices:
        _fail("independent version space has unresolved labelled disagreement")
    return "QUERY_REQUIRED_LOCAL_DISAGREEMENT", None, min(choices)[2], evaluations


@dataclass(frozen=True, slots=True)
class _AcquiredExpected:
    failure: dict[str, Any]
    acquisitions: tuple[dict[str, Any], ...]
    proposal: dict[str, Any]
    proof: dict[str, Any]
    overlay: dict[str, Any]
    control: dict[str, Any]
    selected: Candidate
    counters: dict[str, int]


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _failure_expected(
    frontier: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_failure.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "episode_index": 0,
        "decision_index": 0,
        "root_state": _state_document(state_from_board_v1(INITIAL_BOARDS[0])),
        "planning_horizon": HORIZON,
        "frontier_contexts": list(frontier),
        "frontier_context_count": len(frontier),
        "frontier_frozen_before_target_probability_query": True,
        "target_probability_query_count_before_failure_freeze": 0,
        "provisional_model_certificate_issued": False,
        "failure_reason": "TARGET_PROBABILITY_UNCOVERED_ON_FROZEN_H3_FRONTIER",
        "next_route": "LOCAL_GROUND_DISTINCTION_ACQUISITION",
    }
    return {
        **payload,
        "adaptive_expression_failure_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN,
            payload,
        ),
    }


def _acquisition_expected(
    *,
    failure_id: str,
    query_ordinal: int,
    context: dict[str, Any],
    observed: Fraction,
    before: int,
    after: int,
    universe_generated: bool,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_acquisition.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure_id,
        "query_ordinal": query_ordinal,
        "raw_context": context,
        "observed_rank_two_probability": observed,
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidate_universe_generated_after_this_label": universe_generated,
        "context_belongs_to_previously_frozen_failed_frontier": True,
        "full_state_action_outcome_row_materialized": False,
        "label_used_only_for_candidate_consistency": True,
    }
    return {
        **payload,
        "adaptive_expression_acquisition_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN,
            payload,
        ),
    }


def _proposal_expected(
    failure: dict[str, Any],
    acquisitions: list[dict[str, Any]],
    universe: tuple[Candidate, ...],
    selected: Candidate,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_proposal.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure["adaptive_expression_failure_id"],
        "acquisition_ids": [
            row["adaptive_expression_acquisition_id"] for row in acquisitions
        ],
        "candidate_universe": [
            _candidate_document(candidate) for candidate in universe
        ],
        "candidate_universe_count": len(universe),
        "selected_candidate": _candidate_document(selected),
        "selected_candidate_id": selected[0],
        "remaining_candidate_count": 1,
        "candidate_universe_frozen_from_first_failed_frontier": True,
        "candidate_universe_expanded_after_first_failure": False,
        "selected_before_target_semantics_document_access": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "adaptive_expression_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
            payload,
        ),
    }


def _proof_expected(
    proposal: dict[str, Any], selected: Candidate
) -> dict[str, Any]:
    revealed = _target_document()
    if revealed["target_kernel_id"] != TARGET_KERNEL_ID:
        _fail("independent target commitment changed")
    _, ast, threshold, override, direction = selected
    rows = [
        {"field": "expression_ast", "exact_match": ast == TARGET_EXPRESSION_AST},
        {
            "field": "threshold_and_relation",
            "exact_match": threshold == OVERRIDE_THRESHOLD
            and direction == "LE_OVERRIDE",
        },
        {"field": "base_probability", "exact_match": True},
        {"field": "override_probability", "exact_match": override == OVERRIDE_RATE},
    ]
    if any(row["exact_match"] is not True for row in rows):
        _fail("independently selected expression differs from target")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_proof.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_proposal_id": proposal[
            "adaptive_expression_proposal_id"
        ],
        "target_kernel_id": TARGET_KERNEL_ID,
        "selected_candidate_id": selected[0],
        "revealed_target_semantics": revealed,
        "field_equality_rows": rows,
        "proposal_frozen_before_target_semantics_document_access": True,
        "target_commitment_recomputed_before_comparison": True,
        "exact_program_equivalence_proved": True,
        "proof_probability_label_query_count": 0,
    }
    return {
        **payload,
        "adaptive_expression_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
            payload,
        ),
    }


def _overlay_expected(
    proposal: dict[str, Any], proof: dict[str, Any], selected: Candidate
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_overlay.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_proposal_id": proposal[
            "adaptive_expression_proposal_id"
        ],
        "adaptive_expression_proof_id": proof["adaptive_expression_proof_id"],
        "target_kernel_id": TARGET_KERNEL_ID,
        "selected_candidate": _candidate_document(selected),
        "source_facts": _source_facts(),
        "exact_over_committed_target": True,
        "reusable_across_later_states_actions_and_episodes": True,
        "serialized_state_action_probability_table_present": False,
        "operational_target_probability_query_count_after_overlay_freeze": 0,
    }
    return {
        **payload,
        "adaptive_expression_overlay_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN,
            payload,
        ),
    }


def _control_expected(
    failure: dict[str, Any], frontier: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_ground_control.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_failure_id": failure["adaptive_expression_failure_id"],
        "control_scope": "FIRST_OPERATIONAL_CERTIFICATE_FAILURE_FRONTIER",
        "context_probability_rows": [
            {
                "structural_context_sha256": row["structural_context_sha256"],
                "rank_two_probability": _target_probability(
                    tuple(row["post_swipe_board_ranks"])
                ),
            }
            for row in frontier
        ],
        "distinct_context_probability_label_count": len(frontier),
        "every_distinct_frozen_frontier_context_queried": True,
        "labels_used_to_modify_operational_overlay": False,
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }
    return {
        **payload,
        "adaptive_expression_ground_control_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN,
            payload,
        ),
    }


def _acquired_expected() -> _AcquiredExpected:
    frontier = _frontier(state_from_board_v1(INITIAL_BOARDS[0]))
    failure = _failure_expected(frontier)
    by_id = {row["structural_context_sha256"]: row for row in frontier}
    labels: dict[str, Fraction] = {}
    candidates: tuple[Candidate, ...] = ()
    universe: tuple[Candidate, ...] = ()
    acquisitions = []
    counters = {
        "model.structural_context_rows_frozen": 0,
        "model.structural_expression_value_evaluations": 0,
        "model.expression_candidates_materialized": 0,
        "model.candidate_label_consistency_checks": 0,
        "model.active_query_partition_evaluations": 0,
        "model.target_probability_labels_acquired": 0,
        "model.exact_program_proof_rows_evaluated": 0,
        "model.world_model_freezes": 0,
    }
    while True:
        status, selected_id, context_id, evaluations = _local_decision(
            frontier, candidates, labels
        )
        counters["model.active_query_partition_evaluations"] += evaluations
        if status == "LOCALLY_CERTIFIED_ALL_SURVIVORS_AGREE":
            if selected_id is None:
                raise AssertionError("independent local certificate lost candidate")
            selected = next(row for row in candidates if row[0] == selected_id)
            break
        if context_id is None or context_id not in by_id or len(acquisitions) >= 12:
            _fail("independent adaptive acquisition cannot continue")
        context = by_id[context_id]
        observed = _target_probability(tuple(context["post_swipe_board_ranks"]))
        labels[context_id] = observed
        before = len(candidates)
        generated = False
        if not universe and any(value != BASE_RATE for value in labels.values()):
            candidates, generated_counts = _generate(frontier, labels)
            universe = candidates
            for path, value in generated_counts.items():
                counters[path] += value
            generated = True
        elif universe:
            candidates, checks = _filter(candidates, context, observed)
            counters["model.candidate_label_consistency_checks"] += checks
        counters["model.target_probability_labels_acquired"] += 1
        acquisitions.append(
            _acquisition_expected(
                failure_id=failure["adaptive_expression_failure_id"],
                query_ordinal=len(acquisitions),
                context=context,
                observed=observed,
                before=before,
                after=len(candidates),
                universe_generated=generated,
            )
        )
    if not universe or len(candidates) != 1:
        _fail("independent first frontier did not select one program")
    proposal = _proposal_expected(failure, acquisitions, universe, selected)
    proof = _proof_expected(proposal, selected)
    counters["model.exact_program_proof_rows_evaluated"] = 4
    overlay = _overlay_expected(proposal, proof, selected)
    counters["model.world_model_freezes"] = 1
    control = _control_expected(failure, frontier)
    return _AcquiredExpected(
        failure,
        tuple(acquisitions),
        proposal,
        proof,
        overlay,
        control,
        selected,
        counters,
    )


@dataclass(frozen=True, slots=True)
class _Value:
    score: Fraction
    loss: Fraction
    action: str | None


def _better(candidate: _Value, current: _Value | None) -> bool:
    if current is None:
        return True
    if candidate.action is None or current.action is None:
        _fail("terminal value entered independent action comparison")
    order = tuple(action.value for action in ACTION_ORDER)
    return (candidate.score, -candidate.loss, -order.index(candidate.action)) > (
        current.score,
        -current.loss,
        -order.index(current.action),
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
            "action": value.action,
            "expected_merge_score": value.score,
            "loss_probability_within_horizon": value.loss,
        }
        for value in values
    ]


class _PersistentPlanner:
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0
        self.reusable_keys: frozenset[tuple[tuple[int, ...], str, int]] = frozenset()
        self.cross_hits = 0

    def action_value(
        self, board: tuple[int, ...], action: str, remaining: int
    ) -> _Value:
        self.rows += 1
        context = _context(board, action)
        p2 = _predict(self.candidate, context)
        post = tuple(context["post_swipe_board_ranks"])
        merge = context["merge_score"]
        empty = tuple(index for index, rank in enumerate(post) if rank == 0)
        self.outcomes += 2 * len(empty)
        score = loss = Fraction()
        for cell in empty:
            for rank, mass in ((1, 1 - p2), (2, p2)):
                child = list(post)
                child[cell] = rank
                child_board = tuple(child)
                value = self.state_value(
                    child_board, _status(child_board), remaining - 1
                )
                probability = mass / len(empty)
                score += probability * (merge + value.score)
                loss += probability * value.loss
        return _Value(score, loss, action)

    def state_value(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        if key in self.cache:
            self.hits += 1
            if key in self.reusable_keys:
                self.cross_hits += 1
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

    def plan_root(self, state: Swipe2048State) -> dict[str, Any]:
        before = (
            self.rows,
            self.outcomes,
            self.hits,
            self.misses,
            self.cross_hits,
        )
        self.reusable_keys = frozenset(self.cache)
        values = tuple(
            self.action_value(state.board, action, HORIZON)
            for action in _actions(state.board)
        )
        selected = _best(values)
        return {
            "root_action_exact_values": _value_rows(values),
            "selected_action": selected.action,
            "selected_expected_merge_score": selected.score,
            "selected_loss_probability_within_horizon": selected.loss,
            "factored_action_row_evaluation_count": self.rows - before[0],
            "factored_support_outcome_evaluation_count": self.outcomes - before[1],
            "subproof_cache_hit_count": self.hits - before[2],
            "subproof_cache_miss_count": self.misses - before[3],
            "cross_decision_subproof_cache_hit_count": self.cross_hits - before[4],
            "persistent_subproof_cache_entry_count": len(self.cache),
        }


class _GroundPlanner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}
        self.hits = self.misses = self.rows = self.outcomes = 0

    def action_value(
        self, state: Swipe2048State, action: Swipe2048Action, remaining: int
    ) -> _Value:
        self.rows += 1
        outcomes = _target_outcomes(state, action)
        self.outcomes += len(outcomes)
        score = loss = Fraction()
        for outcome in outcomes:
            value = self.state_value(
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (outcome.merge_score + value.score)
            loss += outcome.probability * value.loss
        return _Value(score, loss, action.value)

    def state_value(
        self, board: tuple[int, ...], status: str, remaining: int
    ) -> _Value:
        board = _canonical(board)
        key = (board, status, remaining)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or status == Swipe2048Status.WON.value:
            result = _Value(Fraction(), Fraction(), None)
        elif status == Swipe2048Status.LOST.value:
            result = _Value(Fraction(), Fraction(1), None)
        else:
            best = None
            for action in _actions(board):
                candidate = self.action_value(
                    state, Swipe2048Action(action), remaining
                )
                if _better(candidate, best):
                    best = candidate
            result = best or _Value(Fraction(), Fraction(1), None)
        self.cache[key] = result
        return result

    def root(self, state: Swipe2048State) -> dict[str, Any]:
        values = tuple(
            self.action_value(state, Swipe2048Action(action), HORIZON)
            for action in _actions(state.board)
        )
        selected = _best(values)
        return {
            "root_action_exact_values": _value_rows(values),
            "selected_action": selected.action,
            "selected_expected_merge_score": selected.score,
            "selected_loss_probability_within_horizon": selected.loss,
            "ground_state_action_row_count": self.rows,
            "ground_outcome_count": self.outcomes,
            "subproof_cache_hit_count": self.hits,
            "subproof_cache_miss_count": self.misses,
            "lane": "STANDALONE_EVALUATION_ONLY",
            "route_or_certificate_authority": False,
        }


def _episode_expected(
    episode_index: int, overlay: dict[str, Any], candidate: Candidate
) -> dict[str, Any]:
    state = state_from_board_v1(INITIAL_BOARDS[episode_index])
    initial = _state_document(state)
    planning = _PersistentPlanner(candidate)
    decisions = []
    for decision_index in range(MAXIMUM_DECISIONS):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        model = planning.plan_root(state)
        certificate_payload = {
            "schema": "acfqp.standard_2048_adaptive_expression_certificate.v35",
            "schema_version": SCHEMA_VERSION,
            "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
            "adaptive_expression_overlay_id": overlay[
                "adaptive_expression_overlay_id"
            ],
            "adaptive_expression_proof_id": overlay[
                "adaptive_expression_proof_id"
            ],
            "episode_index": episode_index,
            "decision_index": decision_index,
            "root_state": _state_document(state),
            "planning_horizon": HORIZON,
            "root_action_exact_values": model["root_action_exact_values"],
            "selected_action": model["selected_action"],
            "selected_expected_merge_score": model[
                "selected_expected_merge_score"
            ],
            "selected_loss_probability_within_horizon": model[
                "selected_loss_probability_within_horizon"
            ],
            "factored_action_row_evaluation_count": model[
                "factored_action_row_evaluation_count"
            ],
            "factored_support_outcome_evaluation_count": model[
                "factored_support_outcome_evaluation_count"
            ],
            "subproof_cache_hit_count": model["subproof_cache_hit_count"],
            "subproof_cache_miss_count": model["subproof_cache_miss_count"],
            "cross_decision_subproof_cache_hit_count": model[
                "cross_decision_subproof_cache_hit_count"
            ],
            "persistent_subproof_cache_entry_count": model[
                "persistent_subproof_cache_entry_count"
            ],
            "operational_target_probability_query_count_after_overlay_freeze": 0,
            "operational_ground_state_action_row_count": 0,
            "target_transition_accessed_before_certificate_freeze": False,
            "status": "CERTIFIED_PROVED_ADAPTIVE_EXPRESSION_MODEL_H3",
        }
        certificate = {
            **certificate_payload,
            "adaptive_expression_certificate_id": content_id(
                CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN,
                certificate_payload,
            ),
        }
        cold = _GroundPlanner().root(state) if decision_index in COLD_CHECKPOINTS else None
        if cold is not None and (
            cold["root_action_exact_values"] != model["root_action_exact_values"]
            or cold["selected_action"] != model["selected_action"]
        ):
            _fail("independent expression and ground checkpoint differ")
        outcome, tape = select_seeded_outcome_v1(
            _target_outcomes(
                state, Swipe2048Action(model["selected_action"])
            ),
            seed=EPISODE_SEEDS[episode_index],
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "certificate": certificate,
                "route": "PROVED_ADAPTIVE_EXPRESSION_WORLD_MODEL",
                "cold_target_checkpoint": cold,
                "checkpoint_root_values_and_action_exactly_equal": cold is None
                or (
                    cold["root_action_exact_values"]
                    == model["root_action_exact_values"]
                    and cold["selected_action"] == model["selected_action"]
                ),
                "certificate_frozen_before_cold_checkpoint_and_target_transition": True,
                "executed_action": model["selected_action"],
                "execution_tape_sha256": tape,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
                "execution_transition_used_to_modify_world_model": False,
            }
        )
        state = outcome.next_state
    checkpoint_rows = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_episode.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_overlay_id": overlay[
            "adaptive_expression_overlay_id"
        ],
        "episode_index": episode_index,
        "execution_seed": EPISODE_SEEDS[episode_index],
        "initial_state": initial,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": MAXIMUM_DECISIONS,
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "model_certificate_count": len(decisions),
        "cold_evaluation_checkpoint_count": len(checkpoint_rows),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoint_rows
        ),
        "factored_action_row_evaluation_count": sum(
            row["certificate"]["factored_action_row_evaluation_count"]
            for row in decisions
        ),
        "factored_support_outcome_evaluation_count": sum(
            row["certificate"]["factored_support_outcome_evaluation_count"]
            for row in decisions
        ),
        "subproof_cache_hit_count": sum(
            row["certificate"]["subproof_cache_hit_count"] for row in decisions
        ),
        "subproof_cache_miss_count": sum(
            row["certificate"]["subproof_cache_miss_count"] for row in decisions
        ),
        "cross_decision_subproof_cache_hit_count": sum(
            row["certificate"]["cross_decision_subproof_cache_hit_count"]
            for row in decisions
        ),
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= GOAL_RANK,
    }
    return {
        **payload,
        "adaptive_expression_episode_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN,
            payload,
        ),
    }


def _preregistration_document(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("preregistration bytes changed")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error(
            "preregistration is not canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
        or len(raw) != PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != PREREGISTRATION_SHA256
    ):
        _fail("frozen preregistration bytes changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "adaptive_expression_preregistration_id"
    }
    if (
        document.get("adaptive_expression_preregistration_id")
        != PREREGISTRATION_ID
        or content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN,
            payload,
        )
        != PREREGISTRATION_ID
    ):
        _fail("preregistration identity changed")
    segment = document.get("fresh_long_segment")
    recovery = document.get("certificate_triggered_recovery")
    prior = document.get("observation_derived_structural_prior")
    sample = document.get("sample_tax_contract")
    predecessors = document.get("frozen_predecessors")
    target = document.get("target_commitment")
    if (
        document.get("schema")
        != "acfqp.standard_2048_adaptive_expression_preregistration.v35"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or type(segment) is not dict
        or tuple(tuple(row) for row in segment.get("initial_boards", ()))
        != INITIAL_BOARDS
        or tuple(segment.get("episode_seeds", ())) != EPISODE_SEEDS
        or segment.get("planning_horizon") != HORIZON
        or segment.get("maximum_decisions_per_episode") != MAXIMUM_DECISIONS
        or type(recovery) is not dict
        or recovery.get("maximum_target_probability_labels") != 12
        or recovery.get("failure_artifact_required_before_acquisition") is not True
        or recovery.get("global_target_table_read_allowed") is not False
        or type(prior) is not dict
        or prior.get("target_specific_program_candidate_supplied") is not False
        or prior.get("named_target_feature_supplied") is not False
        or type(sample) is not dict
        or sample.get("adaptive_target_probability_label_cap") != 12
        or sample.get("broad_iid_or_cross_domain_sample_efficiency_claimed")
        is not False
        or type(predecessors) is not dict
        or predecessors.get("v34_accounting_preregistration_id")
        != V35_REGISTERED_V34_PREREGISTRATION_ID
        or predecessors.get("v34_full_accounting_must_verify_before_target_execution")
        is not True
        or type(target) is not dict
        or target.get("target_kernel_commitment_id") != TARGET_KERNEL_ID
        or target.get("target_semantics_document_present") is not False
        or document.get("target_revealed") is not False
        or document.get("target_execution_performed") is not False
        or document.get("outcome_fields_present") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("counter_completeness_gate_status") != "NOT_RUN"
        or document.get("workload_economics_gate_status") != "NOT_RUN"
    ):
        _fail("preregistration semantics or claim locks changed")
    return document


def _campaign_expected(preregistration: dict[str, Any]) -> dict[str, Any]:
    if (
        V34_ACCOUNTED_CAMPAIGN_ID == "0" * 64
        or V34_ACCOUNTING_VERIFICATION_ID == "0" * 64
    ):
        _fail("V34 accounting predecessor has not been frozen")
    acquired = _acquired_expected()
    episodes = [
        _episode_expected(index, acquired.overlay, acquired.selected)
        for index in range(len(INITIAL_BOARDS))
    ]
    decisions = [row for episode in episodes for row in episode["decisions"]]
    checkpoints = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    adaptive_labels = len(acquired.acquisitions)
    control_labels = acquired.control["distinct_context_probability_label_count"]
    if not 0 < adaptive_labels < control_labels:
        _fail("independent acquisition did not reduce the registered label count")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_campaign.v35",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "adaptive_expression_preregistration": preregistration,
        "additive_role_domains": {
            "proposal": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
            "proof": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
            "roles_are_not_reused_as_overlay_or_plan_certificate": True,
        },
        "preexecution_v34_accounting_binding": {
            "v35_registered_v34_preregistration_id": (
                V35_REGISTERED_V34_PREREGISTRATION_ID
            ),
            "executed_v34r1_preregistration_id": (
                EXECUTED_V34R1_PREREGISTRATION_ID
            ),
            "v34_accounted_campaign_id": V34_ACCOUNTED_CAMPAIGN_ID,
            "v34_accounting_verification_id": V34_ACCOUNTING_VERIFICATION_ID,
            "failed_v34_predecessor_preserved": True,
            "resource_cap_successor_preserves_scientific_workload": True,
            "partial_failed_predecessor_bundles_reused": False,
            "verified_before_first_target_probability_query": True,
        },
        "certificate_failure": acquired.failure,
        "expression_acquisitions": list(acquired.acquisitions),
        "expression_proposal": acquired.proposal,
        "expression_proof": acquired.proof,
        "expression_overlay": acquired.overlay,
        "matched_no_prior_first_frontier_control": acquired.control,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "model_certificate_count": len(decisions),
        "certificate_failure_count": 1,
        "ground_distinction_query_count": adaptive_labels,
        "first_frontier_no_prior_label_count": control_labels,
        "ground_distinction_label_reduction": control_labels - adaptive_labels,
        "adaptive_label_fraction_of_no_prior": Fraction(
            adaptive_labels, control_labels
        ),
        "certified_decisions_per_ground_distinction_label": Fraction(
            len(decisions), adaptive_labels
        ),
        "candidate_universe_count": acquired.proposal["candidate_universe_count"],
        "final_candidate_count": acquired.proposal["remaining_candidate_count"],
        "overlay_freeze_count": 1,
        "operational_target_probability_query_count_after_overlay_freeze": 0,
        "online_target_transition_observation_count": len(decisions),
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "model_operational_counter_values": acquired.counters,
        "planning_factored_action_row_evaluation_count": sum(
            episode["factored_action_row_evaluation_count"] for episode in episodes
        ),
        "planning_factored_support_outcome_evaluation_count": sum(
            episode["factored_support_outcome_evaluation_count"]
            for episode in episodes
        ),
        "planning_subproof_cache_hit_count": sum(
            episode["subproof_cache_hit_count"] for episode in episodes
        ),
        "planning_subproof_cache_miss_count": sum(
            episode["subproof_cache_miss_count"] for episode in episodes
        ),
        "planning_cross_decision_subproof_cache_hit_count": sum(
            episode["cross_decision_subproof_cache_hit_count"]
            for episode in episodes
        ),
        "evaluation_no_prior_probability_label_count": control_labels,
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["cold_target_checkpoint"]["ground_state_action_row_count"]
            for row in checkpoints
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["cold_target_checkpoint"]["ground_outcome_count"]
            for row in checkpoints
        ),
        "sample_tax_reduced_on_registered_first_failure_label_axis": True,
        "all_plans_after_repair_use_proved_reusable_expression_model": True,
        "target_queries_restricted_to_previously_failed_frontier": True,
        "matched_control_labels_excluded_from_operational_overlay": True,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "formal_native_accounting_successor_required": True,
        "full_standard_2048_game_claimed": False,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "adaptive_expression_campaign_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveExpressionIndependentVerificationV35:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    verification_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive-expression verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("adaptive_expression_campaign_id") != self.campaign_id
            or document.get("adaptive_expression_verification_id")
            != self.verification_id
        ):
            _fail("adaptive-expression verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_expression_verification_id"
        }
        if content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
            payload,
        ) != self.verification_id:
            _fail("adaptive-expression verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-expression verification is not an object")
        return document


def verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
    campaign_bytes: bytes,
    preregistration_bytes: bytes,
) -> Standard2048AdaptiveExpressionIndependentVerificationV35:
    if type(campaign_bytes) is not bytes:
        _fail("campaign bytes changed")
    try:
        observed = loads_canonical_json(campaign_bytes)
    except Exception as error:
        raise ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error(
            "campaign is not canonical JSON"
        ) from error
    if type(observed) is not dict or canonical_json_bytes(observed) != campaign_bytes:
        _fail("campaign is not a canonical object")
    observed_payload = {
        key: value
        for key, value in observed.items()
        if key != "adaptive_expression_campaign_id"
    }
    observed_id = observed.get("adaptive_expression_campaign_id")
    if observed_id != content_id(
        CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN,
        observed_payload,
    ):
        _fail("campaign content identity changed")
    if (
        (EXPECTED_CAMPAIGN_ID != "0" * 64 and observed_id != EXPECTED_CAMPAIGN_ID)
        or (
            EXPECTED_CAMPAIGN_BYTE_COUNT
            and len(campaign_bytes) != EXPECTED_CAMPAIGN_BYTE_COUNT
        )
        or (
            EXPECTED_CAMPAIGN_SHA256 != "0" * 64
            and hashlib.sha256(campaign_bytes).hexdigest()
            != EXPECTED_CAMPAIGN_SHA256
        )
    ):
        _fail("frozen campaign identity or bytes changed")
    preregistration = _preregistration_document(preregistration_bytes)
    expected = _campaign_expected(preregistration)
    expected_bytes = canonical_json_bytes(expected)
    campaign_id = expected["adaptive_expression_campaign_id"]
    if campaign_bytes != expected_bytes:
        _fail("campaign differs from producer-free semantic replay")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_independent_verification.v35",
        "schema_version": SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": PREREGISTRATION_ID,
        "adaptive_expression_campaign_id": campaign_id,
        "v34_accounted_campaign_id": V34_ACCOUNTED_CAMPAIGN_ID,
        "v34_accounting_verification_id": V34_ACCOUNTING_VERIFICATION_ID,
        "certificate_failure_id": expected["certificate_failure"][
            "adaptive_expression_failure_id"
        ],
        "adaptive_expression_proposal_id": expected["expression_proposal"][
            "adaptive_expression_proposal_id"
        ],
        "adaptive_expression_proof_id": expected["expression_proof"][
            "adaptive_expression_proof_id"
        ],
        "adaptive_expression_overlay_id": expected["expression_overlay"][
            "adaptive_expression_overlay_id"
        ],
        "episode_count": expected["episode_count"],
        "decision_count": expected["decision_count"],
        "ground_distinction_query_count": expected[
            "ground_distinction_query_count"
        ],
        "first_frontier_no_prior_label_count": expected[
            "first_frontier_no_prior_label_count"
        ],
        "adaptive_label_fraction_of_no_prior": expected[
            "adaptive_label_fraction_of_no_prior"
        ],
        "cold_evaluation_checkpoint_count": expected[
            "cold_evaluation_checkpoint_count"
        ],
        "failure_frontier_acquisition_and_candidate_elimination_replayed": True,
        "selected_expression_exact_proof_replayed": True,
        "every_h3_plan_certificate_replayed": True,
        "every_seeded_execution_transition_replayed": True,
        "persistent_cross_decision_cache_counters_replayed": True,
        "matched_first_frontier_no_prior_control_replayed": True,
        "cold_ground_checkpoints_replayed": True,
        "campaign_replay_result": "PASS",
        "counter_records_issued": False,
        "formal_native_accounting_successor_required": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN,
        payload,
    )
    raw = canonical_json_bytes(
        {**payload, "adaptive_expression_verification_id": verification_id}
    )
    if (
        (EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID)
        or (
            EXPECTED_VERIFICATION_BYTE_COUNT
            and len(raw) != EXPECTED_VERIFICATION_BYTE_COUNT
        )
        or (
            EXPECTED_VERIFICATION_SHA256 != "0" * 64
            and hashlib.sha256(raw).hexdigest() != EXPECTED_VERIFICATION_SHA256
        )
    ):
        _fail("frozen verification identity or bytes changed")
    return Standard2048AdaptiveExpressionIndependentVerificationV35(
        _ISSUER, raw, campaign_id, verification_id
    )


__all__ = (
    "ConstructionK7Standard2048AdaptiveExpressionIndependentVerifierV35Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048AdaptiveExpressionIndependentVerificationV35",
    "verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35",
)
