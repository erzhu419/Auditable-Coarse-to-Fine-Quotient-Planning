"""Producer-free replay of the multiseed partial standard-2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.domains.g2048 import inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_action_v1,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    support_outcomes_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.155"
PROFILE_KEY = "construction_k7_standard_2048_multiseed_partial_world_model_v1"
OBSERVATION_PROFILE_KEY = "construction_k7_standard_2048_spawn_observation_v1"
PLANNING_HORIZON = 3
EPISODE_DECISION_COUNT = 3
SOURCE_OBSERVATION_SEED = "standard-2048-source-spawn-rank-archive-20260812-v1"
SOURCE_STREAM_DOMAIN = b"acfqp:standard-2048-source-spawn-observation:v1\x00"
SOURCE_SAMPLE_COUNT = 4096
HELDOUT_EPISODE_SEEDS = (
    "standard-2048-heldout-episode-000",
    "standard-2048-heldout-episode-003",
    "standard-2048-heldout-episode-081",
)
REGISTERED_ROOT_BOARD = (
    1, 2, 3, 4,
    2, 3, 4, 5,
    3, 4, 5, 6,
    1, 1, 2, 2,
)
HOEFFDING_RADIUS = Fraction(1, 32)
CONDITIONAL_CONFIDENCE_LOWER = Fraction(999, 1000)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_INDEPENDENT_VERIFICATION_V1_DOMAIN
)


class ConstructionK7Standard2048MultiseedIndependentVerifierV1Error(ValueError):
    """Canonical campaign bytes do not independently replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MultiseedIndependentVerifierV1Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048MultiseedIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _fraction(value: Any, label: str) -> Fraction:
    if type(value) is Fraction:
        return value
    row = _exact(value, {"numerator", "denominator"}, label)
    if (
        type(row["numerator"]) is not int
        or type(row["denominator"]) is not int
        or row["denominator"] <= 0
    ):
        _fail(f"{label} is not an exact rational")
    result = Fraction(row["numerator"], row["denominator"])
    if result.numerator != row["numerator"] or result.denominator != row["denominator"]:
        _fail(f"{label} is not reduced")
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _canonical_equal(actual: Any, expected: Any, label: str) -> None:
    if canonical_json_bytes(actual) != canonical_json_bytes(expected):
        _fail(f"{label} changed")


def _domain_id(document: dict[str, Any], identity: str, domain: str) -> str:
    identifier = _cid(document.get(identity), identity)
    payload = {key: value for key, value in document.items() if key != identity}
    if content_id(domain, payload) != identifier:
        _fail(f"{identity} changed")
    return identifier


def _state(document: Any, label: str) -> Swipe2048State:
    row = _exact(document, {"board_ranks", "status"}, label)
    try:
        state = Swipe2048State(tuple(row["board_ranks"]), Swipe2048Status(row["status"]))
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048MultiseedIndependentVerifierV1Error(
            f"{label} is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail(f"{label} status changed")
    return state


def _sdoc(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _row_key(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[tuple[int, ...], str, str]:
    representative, transported_action, _ = canonicalize_state_action_v1(state, action)
    return representative.board, representative.status.value, transported_action.value


def _key_document(key: tuple[tuple[int, ...], str, str]) -> dict[str, Any]:
    board, status, action = key
    return {"state": {"board_ranks": list(board), "status": status}, "action": action}


def _replay_source_evidence(document: Any) -> tuple[str, str, Fraction, Fraction]:
    evidence = _exact(document, {"archive", "interval"}, "source evidence")
    rows: list[int] = []
    for index in range(SOURCE_SAMPLE_COUNT):
        digest = hashlib.sha256(
            SOURCE_STREAM_DOMAIN
            + SOURCE_OBSERVATION_SEED.encode("utf-8")
            + b"\x00"
            + str(index).encode("ascii")
        ).digest()
        rows.append(int(int.from_bytes(digest, "big") * 10 < (1 << 256)))
    packed = bytearray()
    for start in range(0, SOURCE_SAMPLE_COUNT, 8):
        value = 0
        for offset, bit in enumerate(rows[start : start + 8]):
            value |= bit << (7 - offset)
        packed.append(value)
    count = sum(rows)
    archive_payload = {
        "schema": "acfqp.standard_2048_spawn_observation_archive.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": OBSERVATION_PROFILE_KEY,
        "source_stream_domain_hex": SOURCE_STREAM_DOMAIN.hex(),
        "source_observation_seed": SOURCE_OBSERVATION_SEED,
        "source_sample_count": SOURCE_SAMPLE_COUNT,
        "packed_rank_two_bits_hex": bytes(packed).hex(),
        "unpacked_observation_bytes_sha256": hashlib.sha256(bytes(rows)).hexdigest(),
        "rank_one_count": SOURCE_SAMPLE_COUNT - count,
        "rank_two_count": count,
        "source_archive_frozen_before_target_preregistration": True,
        "target_episode_identity_present": False,
        "deterministic_fixture_replay_not_iid_evidence": True,
    }
    archive_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN,
        archive_payload,
    )
    archive_expected = {**archive_payload, "spawn_observation_archive_id": archive_id}
    _canonical_equal(evidence["archive"], archive_expected, "raw source archive")

    empirical = Fraction(count, SOURCE_SAMPLE_COUNT)
    lower = max(Fraction(), empirical - HOEFFDING_RADIUS)
    upper = min(Fraction(1), empirical + HOEFFDING_RADIUS)
    taylor = sum(
        (Fraction(8) ** term) / math.factorial(term) for term in range(14)
    )
    if not taylor > 2000 or not lower <= Fraction(1, 10) <= upper:
        _fail("registered observation interval proof changed")
    interval_payload = {
        "schema": "acfqp.standard_2048_spawn_probability_interval.v1",
        "schema_version": SCHEMA_VERSION,
        "spawn_observation_archive_id": archive_id,
        "estimated_parameter": "P_SPAWN_RANK_TWO",
        "estimator": "RAW_EMPIRICAL_FREQUENCY_V1",
        "empirical_rank_two_probability": _fdoc(empirical),
        "hoeffding_radius": _fdoc(HOEFFDING_RADIUS),
        "rank_two_probability_lower": _fdoc(lower),
        "rank_two_probability_upper": _fdoc(upper),
        "conditional_confidence_lower": _fdoc(CONDITIONAL_CONFIDENCE_LOWER),
        "two_sided_hoeffding_exponent": 8,
        "exp_eight_taylor_last_term": 13,
        "exp_eight_rational_lower_bound": _fdoc(taylor),
        "proof_obligation": "2*EXP(-8)<1/1000_BECAUSE_EXP(8)>2000",
        "confidence_is_conditional_on_idealized_iid_source": True,
        "deterministic_replay_does_not_establish_iid": True,
        "known_position_support_not_estimated": True,
    }
    interval_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN, interval_payload
    )
    interval_expected = {
        **interval_payload,
        "spawn_probability_interval_id": interval_id,
    }
    _canonical_equal(evidence["interval"], interval_expected, "spawn interval")
    return archive_id, interval_id, lower, upper


@dataclass(frozen=True, slots=True)
class _Outcome:
    spawn_rank: int
    probability: Fraction
    next_state: Swipe2048State
    merge_score: int
    count: int


@dataclass(frozen=True, slots=True)
class _Row:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[_Outcome, ...]
    support_count: int
    interval_id: str
    row_id: str

    @property
    def key(self) -> tuple[tuple[int, ...], str, str]:
        return self.state.board, self.state.status.value, self.action.value


def _row_document(row: _Row) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_partial_spawn_row.v1",
        "schema_version": SCHEMA_VERSION,
        "state": _sdoc(row.state),
        "action": row.action.value,
        "spawn_probability_interval_id": row.interval_id,
        "outcomes": [
            {
                "spawn_rank": outcome.spawn_rank,
                "conditional_cell_probability": _fdoc(outcome.probability),
                "next_state": _sdoc(outcome.next_state),
                "merge_score": outcome.merge_score,
                "represented_support_outcome_count": outcome.count,
            }
            for outcome in row.outcomes
        ],
        "support_outcome_count": row.support_count,
        "support_and_position_geometry_known_structural": True,
        "spawn_rank_probability_point_value_absent": True,
        "materialized_only_after_failed_proof": True,
    }
    return {**payload, "partial_row_id": content_id(
        CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN, payload
    )}


def _replay_row(document: Any, interval_id: str) -> _Row:
    row = _exact(
        document,
        {
            "schema", "schema_version", "state", "action",
            "spawn_probability_interval_id", "outcomes", "support_outcome_count",
            "support_and_position_geometry_known_structural",
            "spawn_rank_probability_point_value_absent",
            "materialized_only_after_failed_proof", "partial_row_id",
        },
        "partial row",
    )
    state = _state(row["state"], "partial row state")
    try:
        action = Swipe2048Action(row["action"])
    except ValueError as error:
        raise ConstructionK7Standard2048MultiseedIndependentVerifierV1Error(
            "partial row action changed"
        ) from error
    if (
        canonicalize_state_v1(state)[0] != state
        or action not in legal_actions_v1(state.board)
        or row["spawn_probability_interval_id"] != interval_id
    ):
        _fail("partial row identity or legality changed")
    support = support_outcomes_v1(state, action)
    empty_count = len(support) // 2
    grouped: dict[tuple[int, tuple[int, ...], str, int], int] = {}
    for outcome in support:
        representative, _ = canonicalize_state_v1(outcome.next_state)
        key = (
            outcome.spawned_rank,
            representative.board,
            representative.status.value,
            outcome.merge_score,
        )
        grouped[key] = grouped.get(key, 0) + 1
    outcomes = tuple(
        _Outcome(
            rank,
            Fraction(count, empty_count),
            Swipe2048State(next_board, Swipe2048Status(next_status)),
            merge_score,
            count,
        )
        for (rank, next_board, next_status, merge_score), count in sorted(grouped.items())
    )
    result = _Row(
        state,
        action,
        outcomes,
        len(support),
        interval_id,
        _cid(row["partial_row_id"], "partial row ID"),
    )
    expected = _row_document(result)
    if expected["partial_row_id"] != result.row_id:
        _fail("partial row content ID changed")
    _canonical_equal(row, expected, "partial support row")
    return result


def _model_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    archive_id: str,
    interval_id: str,
) -> dict[str, Any]:
    documents = [_row_document(rows[key]) for key in sorted(rows)]
    payload = {
        "schema": "acfqp.standard_2048_partial_d4_world_model.v1",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_PARTIAL_SPAWN_V1",
        "abstraction": "D4_STATE_ACTION_QUOTIENT_WITH_RANK_INTERVAL_V1",
        "query_neutral": True,
        "spawn_observation_archive_id": archive_id,
        "spawn_probability_interval_id": interval_id,
        "support_and_position_geometry_known_structural": True,
        "rank_probability_observation_derived_interval": True,
        "rectangular_rowwise_interval_relaxation": True,
        "rows": documents,
        "row_count": len(documents),
        "support_outcome_count": sum(row.support_count for row in rows.values()),
    }
    return {**payload, "partial_world_model_id": content_id(
        CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN, payload
    )}


def _replay_final_model(
    document: Any, archive_id: str, interval_id: str
) -> tuple[dict[tuple[tuple[int, ...], str, str], _Row], str]:
    model = _exact(
        document,
        {
            "schema", "schema_version", "semantics", "abstraction", "query_neutral",
            "spawn_observation_archive_id", "spawn_probability_interval_id",
            "support_and_position_geometry_known_structural",
            "rank_probability_observation_derived_interval",
            "rectangular_rowwise_interval_relaxation", "rows", "row_count",
            "support_outcome_count", "partial_world_model_id",
        },
        "final partial model",
    )
    if type(model["rows"]) is not list:
        _fail("final partial rows changed")
    rows: dict[tuple[tuple[int, ...], str, str], _Row] = {}
    seen_ids: set[str] = set()
    for raw in model["rows"]:
        row = _replay_row(raw, interval_id)
        if row.key in rows or row.row_id in seen_ids:
            _fail("final model has duplicate partial rows")
        rows[row.key] = row
        seen_ids.add(row.row_id)
    expected = _model_document(rows, archive_id, interval_id)
    _canonical_equal(model, expected, "final partial model")
    return rows, expected["partial_world_model_id"]


@dataclass(frozen=True, slots=True)
class _RobustValue:
    lower: Fraction
    upper: Fraction
    loss: Fraction
    action: Swipe2048Action | None


@dataclass(frozen=True, slots=True)
class _ExactValue:
    score: Fraction
    loss: Fraction
    action: Swipe2048Action | None


def _missing_frontier(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    root: Swipe2048State,
    horizon: int,
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        representative, _ = canonicalize_state_v1(state)
        visit = (representative.board, representative.status.value, remaining)
        if (
            remaining == 0
            or representative.status is not Swipe2048Status.ACTIVE
            or visit in visited
        ):
            return
        visited.add(visit)
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                missing.add(key)
            else:
                for outcome in row.outcomes:
                    walk(outcome.next_state, remaining - 1)

    walk(root, horizon)
    return tuple(sorted(missing))


def _solve_robust(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    root: Swipe2048State,
    horizon: int,
    probability_lower: Fraction,
    probability_upper: Fraction,
) -> tuple[_RobustValue, tuple[str, ...]]:
    dependencies: set[str] = set()

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _RobustValue:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        representative, _ = canonicalize_state_v1(state)
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            return _RobustValue(Fraction(), Fraction(), Fraction(), None)
        if representative.status is Swipe2048Status.LOST:
            return _RobustValue(Fraction(), Fraction(), Fraction(1), None)
        best: _RobustValue | None = None
        for action in legal_actions_v1(representative.board):
            row = rows.get(_row_key(representative, action))
            if row is None:
                _fail("robust replay reached a missing row")
            dependencies.add(row.row_id)
            by_rank: dict[int, tuple[Fraction, Fraction, Fraction]] = {}
            for rank in (1, 2):
                lower = upper = loss = Fraction()
                for outcome in row.outcomes:
                    if outcome.spawn_rank != rank:
                        continue
                    child = solve(
                        outcome.next_state.board,
                        outcome.next_state.status.value,
                        remaining - 1,
                    )
                    lower += outcome.probability * (outcome.merge_score + child.lower)
                    upper += outcome.probability * (outcome.merge_score + child.upper)
                    loss += outcome.probability * child.loss
                by_rank[rank] = lower, upper, loss
            lower_values = tuple(
                (1 - p) * by_rank[1][0] + p * by_rank[2][0]
                for p in (probability_lower, probability_upper)
            )
            upper_values = tuple(
                (1 - p) * by_rank[1][1] + p * by_rank[2][1]
                for p in (probability_lower, probability_upper)
            )
            loss_values = tuple(
                (1 - p) * by_rank[1][2] + p * by_rank[2][2]
                for p in (probability_lower, probability_upper)
            )
            candidate = _RobustValue(
                min(lower_values), max(upper_values), max(loss_values), action
            )
            if best is None or (
                candidate.lower,
                -candidate.loss,
                candidate.upper,
                -ACTION_ORDER.index(candidate.action),
            ) > (
                best.lower,
                -best.loss,
                best.upper,
                -ACTION_ORDER.index(best.action),
            ):
                best = candidate
        if best is None:
            return _RobustValue(Fraction(), Fraction(), Fraction(1), None)
        return best

    representative, transform = canonicalize_state_v1(root)
    value = solve(representative.board, representative.status.value, horizon)
    if value.action is None:
        return value, tuple(sorted(dependencies))
    return (
        _RobustValue(
            value.lower,
            value.upper,
            value.loss,
            transform_action_v1(value.action, inverse_d4(transform)),
        ),
        tuple(sorted(dependencies)),
    )


def _audit_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    root: Swipe2048State,
    archive_id: str,
    interval_id: str,
    probability_lower: Fraction,
    probability_upper: Fraction,
) -> dict[str, Any]:
    model = _model_document(rows, archive_id, interval_id)
    missing = _missing_frontier(rows, root, PLANNING_HORIZON)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_statistical_partial_model_audit.v1",
        "schema_version": SCHEMA_VERSION,
        "partial_world_model_id": model["partial_world_model_id"],
        "spawn_probability_interval_id": interval_id,
        "root_state": _sdoc(root),
        "horizon": PLANNING_HORIZON,
        "objective": "MAX_ROBUST_SCORE_LOWER_THEN_MIN_ROBUST_LOSS_UPPER_V1",
        "status": "FAILED_PROOF_FRONTIER" if missing else "CERTIFIED_INTERVAL_ROBUST",
        "missing_frontier": [_key_document(key) for key in missing],
        "missing_frontier_count": len(missing),
    }
    if missing:
        payload.update(
            {
                "selected_action": None,
                "robust_score_lower": None,
                "robust_score_upper": None,
                "robust_loss_probability_upper": None,
                "ordered_dependency_row_ids": [],
                "robust_plan_id": None,
            }
        )
    else:
        value, dependencies = _solve_robust(
            rows,
            root,
            PLANNING_HORIZON,
            probability_lower,
            probability_upper,
        )
        if value.action is None:
            _fail("active audit root produced no action")
        plan_payload = {
            "schema": "acfqp.standard_2048_interval_robust_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_world_model_id": model["partial_world_model_id"],
            "spawn_probability_interval_id": interval_id,
            "root_state": _sdoc(root),
            "horizon": PLANNING_HORIZON,
            "objective": "MAX_ROBUST_SCORE_LOWER_THEN_MIN_ROBUST_LOSS_UPPER_V1",
            "selected_action": value.action.value,
            "robust_score_lower": _fdoc(value.lower),
            "robust_score_upper": _fdoc(value.upper),
            "robust_loss_probability_upper": _fdoc(value.loss),
            "ordered_dependency_row_ids": list(dependencies),
        }
        payload.update(
            {
                "selected_action": value.action.value,
                "robust_score_lower": _fdoc(value.lower),
                "robust_score_upper": _fdoc(value.upper),
                "robust_loss_probability_upper": _fdoc(value.loss),
                "ordered_dependency_row_ids": list(dependencies),
                "robust_plan_id": content_id(
                    CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN,
                    plan_payload,
                ),
            }
        )
    return {**payload, "audit_id": content_id(
        CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN, payload
    )}


def _direct_document(root: Swipe2048State) -> tuple[dict[str, Any], _ExactValue]:
    touched: set[tuple[tuple[int, ...], str, str]] = set()
    outcome_count = 0

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ExactValue:
        nonlocal outcome_count
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _ExactValue(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _ExactValue(Fraction(), Fraction(1), None)
        best: _ExactValue | None = None
        for action in legal_actions_v1(state.board):
            row_key = (state.board, state.status.value, action.value)
            outcomes = step_v1(state, action)
            if row_key not in touched:
                touched.add(row_key)
                outcome_count += len(outcomes)
            score = loss = Fraction()
            for outcome in outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (outcome.merge_score + child.score)
                loss += outcome.probability * child.loss
            candidate = _ExactValue(score, loss, action)
            if best is None or (
                candidate.score,
                -candidate.loss,
                -ACTION_ORDER.index(candidate.action),
            ) > (best.score, -best.loss, -ACTION_ORDER.index(best.action)):
                best = candidate
        if best is None:
            return _ExactValue(Fraction(), Fraction(1), None)
        return best

    value = solve(root.board, root.status.value, PLANNING_HORIZON)
    if value.action is None:
        _fail("direct replay produced no action")
    payload = {
        "schema": "acfqp.standard_2048_statistical_matched_direct.v1",
        "schema_version": SCHEMA_VERSION,
        "root_state": _sdoc(root),
        "horizon": PLANNING_HORIZON,
        "objective": "MAX_EXACT_EXPECTED_SCORE_THEN_MIN_LOSS_V1",
        "selected_action": value.action.value,
        "expected_merge_score": _fdoc(value.score),
        "loss_probability_within_horizon": _fdoc(value.loss),
        "ground_state_action_row_count": len(touched),
        "ground_outcome_count": outcome_count,
        "cold_model_per_decision": True,
        "evaluation_lane_only": True,
        "partial_model_or_source_observations_used": False,
    }
    return (
        {**payload, "matched_direct_plan_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN,
            payload,
        )},
        value,
    )


def _replay_preregistration(
    document: Any, archive_id: str, interval_id: str
) -> str:
    root = state_from_board_v1(REGISTERED_ROOT_BOARD)
    payload = {
        "schema": "acfqp.standard_2048_multiseed_statistical_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "environment_semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1",
        "registered_root_state": _sdoc(root),
        "planning_horizon": PLANNING_HORIZON,
        "episode_decision_count": EPISODE_DECISION_COUNT,
        "heldout_episode_seeds": list(HELDOUT_EPISODE_SEEDS),
        "source_observation_seed": SOURCE_OBSERVATION_SEED,
        "source_sample_count": SOURCE_SAMPLE_COUNT,
        "spawn_observation_archive_id": archive_id,
        "spawn_probability_interval_id": interval_id,
        "goal_rank": GOAL_RANK,
        "source_archive_frozen_before_target_preregistration": True,
        "source_and_target_identities_disjoint": True,
        "episode_seeds_and_matched_controls_frozen_before_model_construction": True,
        "known_structural_mechanics": [
            "WHOLE_BOARD_SWIPE",
            "SPAWN_CELL_SUPPORT",
            "UNIFORM_CELL_GIVEN_RANK",
            "D4_TRANSPORT",
        ],
        "observation_derived_parameter": "P_SPAWN_RANK_TWO_INTERVAL",
    }
    expected = {
        **payload,
        "statistical_preregistration_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN,
            payload,
        ),
    }
    _canonical_equal(document, expected, "statistical preregistration")
    return expected["statistical_preregistration_id"]


@dataclass(frozen=True, slots=True)
class Standard2048MultiseedIndependentVerificationV1:
    campaign_id: str
    preregistration_id: str
    source_archive_id: str
    spawn_interval_id: str
    final_world_model_id: str
    final_world_model_row_count: int
    total_receding_decision_count: int

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "preregistration_id": self.preregistration_id,
                "source_archive_id": self.source_archive_id,
                "spawn_interval_id": self.spawn_interval_id,
                "final_world_model_id": self.final_world_model_id,
                "final_world_model_row_count": self.final_world_model_row_count,
                "total_receding_decision_count": self.total_receding_decision_count,
                "raw_source_observations_replayed": True,
                "partial_support_rows_replayed": True,
                "robust_receding_plans_replayed": True,
                "matched_direct_controls_replayed": True,
                "process_or_iid_authority_independently_verified": False,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_multiseed_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "preregistration_id": self.preregistration_id,
            "source_archive_id": self.source_archive_id,
            "spawn_interval_id": self.spawn_interval_id,
            "final_world_model_id": self.final_world_model_id,
            "final_world_model_row_count": self.final_world_model_row_count,
            "total_receding_decision_count": self.total_receding_decision_count,
            "raw_source_observations_replayed": True,
            "partial_support_rows_replayed": True,
            "robust_receding_plans_replayed": True,
            "matched_direct_controls_replayed": True,
            "process_or_iid_authority_independently_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_multiseed_campaign_bytes_independently_v1(
    raw: bytes,
) -> Standard2048MultiseedIndependentVerificationV1:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    root = loads_canonical_json(raw)
    if type(root) is not dict or canonical_json_bytes(root) != raw:
        _fail("campaign is not canonical JSON")
    root = _exact(
        root,
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "source_observation_evidence", "statistical_preregistration", "episodes",
            "episode_count", "total_receding_decision_count", "final_partial_world_model",
            "partial_model_ground_support_row_count", "partial_model_support_outcome_count",
            "matched_direct_total_ground_row_count",
            "matched_direct_total_ground_outcome_count", "sample_tax_telemetry",
            "standard_4x4_swipe_spawn_semantics_executed",
            "multiple_heldout_seeds_executed", "longer_receding_rollout_executed",
            "persistent_world_model_reused_across_episodes",
            "spawn_rank_law_observation_derived_partial",
            "spawn_position_law_known_structural", "source_target_identity_separated",
            "certificate_failure_triggered_ground_recovery",
            "ground_support_rows_materialized_only_after_failed_proof",
            "all_selected_actions_match_cold_direct",
            "exact_target_values_inside_robust_envelopes",
            "multi_step_planning_completed_in_partial_abstract_model",
            "formal_exact_iid_claimed", "unknown_support_learning_claimed",
            "observation_derived_coordinate_invention_claimed",
            "full_standard_2048_game_completed", "real_game_ui_adapter_present",
            "broad_sample_efficiency_claimed", "official_execution_allowed",
            "official_scalar_cost", "official_N_break_even",
            "counter_completeness_gate_status", "workload_economics_gate_status",
            "campaign_id",
        },
        "campaign",
    )
    campaign_id = _domain_id(
        root,
        "campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN,
    )
    if (
        root["schema"]
        != "acfqp.standard_2048_multiseed_partial_world_model_campaign.v1"
        or root["schema_version"] != SCHEMA_VERSION
        or root["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or root["profile_key"] != PROFILE_KEY
    ):
        _fail("campaign header changed")

    positive_locks = {
        "standard_4x4_swipe_spawn_semantics_executed",
        "multiple_heldout_seeds_executed",
        "longer_receding_rollout_executed",
        "persistent_world_model_reused_across_episodes",
        "spawn_rank_law_observation_derived_partial",
        "spawn_position_law_known_structural",
        "source_target_identity_separated",
        "certificate_failure_triggered_ground_recovery",
        "ground_support_rows_materialized_only_after_failed_proof",
        "all_selected_actions_match_cold_direct",
        "exact_target_values_inside_robust_envelopes",
        "multi_step_planning_completed_in_partial_abstract_model",
    }
    negative_locks = {
        "formal_exact_iid_claimed",
        "unknown_support_learning_claimed",
        "observation_derived_coordinate_invention_claimed",
        "full_standard_2048_game_completed",
        "real_game_ui_adapter_present",
        "broad_sample_efficiency_claimed",
        "official_execution_allowed",
    }
    if any(root[key] is not True for key in positive_locks) or any(
        root[key] is not False for key in negative_locks
    ):
        _fail("campaign claim locks changed")
    if (
        root["official_scalar_cost"] is not None
        or root["official_N_break_even"] is not None
        or root["counter_completeness_gate_status"] != "NOT_RUN"
        or root["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("official economics locks changed")

    archive_id, interval_id, probability_lower, probability_upper = (
        _replay_source_evidence(root["source_observation_evidence"])
    )
    preregistration_id = _replay_preregistration(
        root["statistical_preregistration"], archive_id, interval_id
    )
    final_rows, final_model_id = _replay_final_model(
        root["final_partial_world_model"], archive_id, interval_id
    )
    final_rows_by_id = {row.row_id: row for row in final_rows.values()}
    current: dict[tuple[tuple[int, ...], str, str], _Row] = {}
    expected_initial_model_id = _model_document(current, archive_id, interval_id)[
        "partial_world_model_id"
    ]

    if type(root["episodes"]) is not list or len(root["episodes"]) != len(
        HELDOUT_EPISODE_SEEDS
    ):
        _fail("heldout episode inventory changed")
    total_rows = total_support = total_direct_rows = total_direct_outcomes = 0
    total_decisions = 0
    for episode_index, (raw_episode, seed) in enumerate(
        zip(root["episodes"], HELDOUT_EPISODE_SEEDS, strict=True)
    ):
        episode = _exact(
            raw_episode,
            {
                "schema", "schema_version", "statistical_preregistration_id",
                "episode_index", "heldout_episode_seed", "initial_state",
                "initial_partial_world_model_id", "decisions", "decision_count",
                "terminal_state_after_registered_prefix", "final_partial_world_model_id",
                "incremental_partial_row_count", "incremental_support_outcome_count",
                "matched_direct_ground_row_count", "matched_direct_ground_outcome_count",
                "episode_id",
            },
            "episode",
        )
        _domain_id(
            episode,
            "episode_id",
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN,
        )
        state = state_from_board_v1(REGISTERED_ROOT_BOARD)
        episode_initial_model_id = _model_document(current, archive_id, interval_id)[
            "partial_world_model_id"
        ]
        if (
            episode["schema"]
            != "acfqp.standard_2048_statistical_receding_episode.v1"
            or episode["schema_version"] != SCHEMA_VERSION
            or episode["statistical_preregistration_id"] != preregistration_id
            or episode["episode_index"] != episode_index
            or episode["heldout_episode_seed"] != seed
            or episode["initial_state"] != _sdoc(state)
            or episode["initial_partial_world_model_id"] != episode_initial_model_id
            or type(episode["decisions"]) is not list
            or len(episode["decisions"]) != EPISODE_DECISION_COUNT
            or episode["decision_count"] != EPISODE_DECISION_COUNT
        ):
            _fail("episode preregistration or initial state changed")
        episode_rows = episode_support = episode_direct_rows = episode_direct_outcomes = 0
        for decision_index, raw_decision in enumerate(episode["decisions"]):
            decision = _exact(
                raw_decision,
                {
                    "episode_index", "decision_index", "state_before_decision",
                    "base_audit", "recovery_transactions", "certified_robust_plan",
                    "matched_direct_control", "selected_action_agrees_with_matched_direct",
                    "exact_direct_value_inside_robust_envelope",
                    "incremental_partial_row_count", "incremental_support_outcome_count",
                    "executed_target_transition",
                },
                "decision",
            )
            if (
                decision["episode_index"] != episode_index
                or decision["decision_index"] != decision_index
                or decision["state_before_decision"] != _sdoc(state)
                or decision["selected_action_agrees_with_matched_direct"] is not True
                or decision["exact_direct_value_inside_robust_envelope"] is not True
            ):
                _fail("decision identity or claim changed")
            base_expected = _audit_document(
                current,
                state,
                archive_id,
                interval_id,
                probability_lower,
                probability_upper,
            )
            _canonical_equal(decision["base_audit"], base_expected, "base audit")
            if type(decision["recovery_transactions"]) is not list:
                _fail("recovery transaction inventory changed")
            decision_rows = decision_support = 0
            for transaction_index, raw_transaction in enumerate(
                decision["recovery_transactions"], start=1
            ):
                transaction = _exact(
                    raw_transaction,
                    {
                        "transaction_index", "failed_audit_id", "failed_status",
                        "predecessor_partial_world_model_id", "recovered_frontier_count",
                        "recovered_partial_row_ids", "recovered_support_outcome_count",
                        "successor_partial_world_model_id",
                        "ground_support_access_before_failed_audit",
                        "exact_spawn_probability_accessed_by_recovery",
                    },
                    "recovery transaction",
                )
                failed = _audit_document(
                    current,
                    state,
                    archive_id,
                    interval_id,
                    probability_lower,
                    probability_upper,
                )
                if failed["status"] != "FAILED_PROOF_FRONTIER":
                    _fail("recovery continued after certification")
                frontier = tuple(
                    _row_key(
                        _state(item["state"], "failed frontier state"),
                        Swipe2048Action(item["action"]),
                    )
                    for item in failed["missing_frontier"]
                )
                expected_ids: list[str] = []
                recovered_rows: list[_Row] = []
                for key in frontier:
                    row = final_rows.get(key)
                    if row is None or key in current:
                        _fail("failed frontier row is absent or already present")
                    expected_ids.append(row.row_id)
                    recovered_rows.append(row)
                predecessor_id = _model_document(current, archive_id, interval_id)[
                    "partial_world_model_id"
                ]
                if (
                    transaction["transaction_index"] != transaction_index
                    or transaction["failed_audit_id"] != failed["audit_id"]
                    or transaction["failed_status"] != "FAILED_PROOF_FRONTIER"
                    or transaction["predecessor_partial_world_model_id"] != predecessor_id
                    or transaction["recovered_frontier_count"] != len(recovered_rows)
                    or transaction["recovered_partial_row_ids"] != expected_ids
                    or transaction["ground_support_access_before_failed_audit"] is not False
                    or transaction["exact_spawn_probability_accessed_by_recovery"] is not False
                ):
                    _fail("recovery transaction sequencing changed")
                for row in recovered_rows:
                    current[row.key] = row
                recovered_support = sum(row.support_count for row in recovered_rows)
                successor_id = _model_document(current, archive_id, interval_id)[
                    "partial_world_model_id"
                ]
                if (
                    transaction["recovered_support_outcome_count"] != recovered_support
                    or transaction["successor_partial_world_model_id"] != successor_id
                ):
                    _fail("recovery transaction work or successor changed")
                decision_rows += len(recovered_rows)
                decision_support += recovered_support
            certified = _audit_document(
                current,
                state,
                archive_id,
                interval_id,
                probability_lower,
                probability_upper,
            )
            if certified["status"] != "CERTIFIED_INTERVAL_ROBUST":
                _fail("decision remained uncertified after registered recovery")
            _canonical_equal(
                decision["certified_robust_plan"], certified, "certified robust plan"
            )
            direct, exact_value = _direct_document(state)
            _canonical_equal(
                decision["matched_direct_control"], direct, "matched direct control"
            )
            if (
                certified["selected_action"] != direct["selected_action"]
                or not _fraction(certified["robust_score_lower"], "robust lower")
                <= exact_value.score
                <= _fraction(certified["robust_score_upper"], "robust upper")
                or exact_value.loss
                > _fraction(certified["robust_loss_probability_upper"], "robust loss")
                or decision["incremental_partial_row_count"] != decision_rows
                or decision["incremental_support_outcome_count"] != decision_support
            ):
                _fail("robust/direct agreement or decision work changed")
            transition = _exact(
                decision["executed_target_transition"],
                {
                    "target_seed", "target_decision_index", "spawn_tape_digest",
                    "selected_action", "selected_outcome_probability_evaluation_only",
                    "spawned_cell", "spawned_rank", "merge_score", "successor_state",
                    "target_observation_not_used_before_plan_freeze",
                },
                "target transition",
            )
            action = Swipe2048Action(certified["selected_action"])
            selected, digest = select_seeded_outcome_v1(
                step_v1(state, action), seed=seed, decision_index=decision_index
            )
            if (
                transition["target_seed"] != seed
                or transition["target_decision_index"] != decision_index
                or transition["spawn_tape_digest"] != digest
                or transition["selected_action"] != action.value
                or transition["selected_outcome_probability_evaluation_only"]
                != selected.probability
                or transition["spawned_cell"] != selected.spawned_cell
                or transition["spawned_rank"] != selected.spawned_rank
                or transition["merge_score"] != selected.merge_score
                or transition["successor_state"] != _sdoc(selected.next_state)
                or transition["target_observation_not_used_before_plan_freeze"] is not True
            ):
                _fail("heldout target transition changed")
            state = selected.next_state
            episode_rows += decision_rows
            episode_support += decision_support
            episode_direct_rows += direct["ground_state_action_row_count"]
            episode_direct_outcomes += direct["ground_outcome_count"]
            total_decisions += 1
        episode_final_model_id = _model_document(current, archive_id, interval_id)[
            "partial_world_model_id"
        ]
        if (
            episode["terminal_state_after_registered_prefix"] != _sdoc(state)
            or episode["final_partial_world_model_id"] != episode_final_model_id
            or episode["incremental_partial_row_count"] != episode_rows
            or episode["incremental_support_outcome_count"] != episode_support
            or episode["matched_direct_ground_row_count"] != episode_direct_rows
            or episode["matched_direct_ground_outcome_count"] != episode_direct_outcomes
        ):
            _fail("episode terminal state or work totals changed")
        total_rows += episode_rows
        total_support += episode_support
        total_direct_rows += episode_direct_rows
        total_direct_outcomes += episode_direct_outcomes
        if episode_index == 0 and episode_initial_model_id != expected_initial_model_id:
            _fail("first episode did not begin from the empty model")

    if current != final_rows or _model_document(current, archive_id, interval_id)[
        "partial_world_model_id"
    ] != final_model_id:
        _fail("episode chain did not reconstruct the final model")
    telemetry = _exact(
        root["sample_tax_telemetry"],
        {
            "offline_source_rank_observation_count",
            "online_target_transition_observation_count",
            "partial_model_support_row_count", "partial_model_support_outcome_count",
            "matched_direct_ground_row_count", "matched_direct_ground_outcome_count",
            "scalar_crossing_claimed",
        },
        "sample-tax telemetry",
    )
    if (
        root["episode_count"] != len(HELDOUT_EPISODE_SEEDS)
        or root["total_receding_decision_count"] != total_decisions
        or root["partial_model_ground_support_row_count"] != total_rows
        or root["partial_model_support_outcome_count"] != total_support
        or root["matched_direct_total_ground_row_count"] != total_direct_rows
        or root["matched_direct_total_ground_outcome_count"] != total_direct_outcomes
        or telemetry
        != {
            "offline_source_rank_observation_count": SOURCE_SAMPLE_COUNT,
            "online_target_transition_observation_count": total_decisions,
            "partial_model_support_row_count": total_rows,
            "partial_model_support_outcome_count": total_support,
            "matched_direct_ground_row_count": total_direct_rows,
            "matched_direct_ground_outcome_count": total_direct_outcomes,
            "scalar_crossing_claimed": False,
        }
    ):
        _fail("campaign or sample-tax totals changed")

    return Standard2048MultiseedIndependentVerificationV1(
        campaign_id,
        preregistration_id,
        archive_id,
        interval_id,
        final_model_id,
        len(final_rows),
        total_decisions,
    )


__all__ = (
    "ConstructionK7Standard2048MultiseedIndependentVerifierV1Error",
    "Standard2048MultiseedIndependentVerificationV1",
    "verify_standard_2048_multiseed_campaign_bytes_independently_v1",
)
