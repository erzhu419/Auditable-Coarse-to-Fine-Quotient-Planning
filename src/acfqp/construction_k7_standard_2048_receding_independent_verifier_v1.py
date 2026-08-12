"""Producer-free replay for the standard-2048 H=3 construction campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.domains.g2048 import D4Transform, inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    SPAWN_DISTRIBUTION,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_action_v1,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    transform_action_v1,
    transform_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_standard_2048_h3_receding_world_model_v1"
PLANNING_HORIZON = 3
RECEDING_DECISION_COUNT = 2
HELDOUT_TRANSFORM = D4Transform.ROTATE_90
HELDOUT_SPAWN_SEED = "standard-2048-heldout-seed-20260812-v1"
VERIFICATION_DOMAIN = CONSTRUCTION_K7_STANDARD_2048_INDEPENDENT_VERIFICATION_V1_DOMAIN


class ConstructionK7Standard2048IndependentVerifierV1Error(ValueError):
    """Canonical campaign bytes do not replay under the public semantics."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048IndependentVerifierV1Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048IndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fraction(document: Any, label: str) -> Fraction:
    if type(document) is Fraction:
        return document
    row = _exact(document, {"numerator", "denominator"}, label)
    if (
        type(row["numerator"]) is not int
        or type(row["denominator"]) is not int
        or row["denominator"] <= 0
    ):
        _fail(f"{label} is not an exact rational")
    value = Fraction(row["numerator"], row["denominator"])
    if value.numerator != row["numerator"] or value.denominator != row["denominator"]:
        _fail(f"{label} is not reduced")
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state(document: Any, label: str) -> Swipe2048State:
    row = _exact(document, {"board_ranks", "status"}, label)
    try:
        state = Swipe2048State(tuple(row["board_ranks"]), Swipe2048Status(row["status"]))
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048IndependentVerifierV1Error(
            f"{label} state is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail(f"{label} status is not derived from the board")
    return state


def _sdoc(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _domain_id(document: dict[str, Any], identity: str, domain: str) -> str:
    identifier = _cid(document.get(identity), identity)
    payload = {key: value for key, value in document.items() if key != identity}
    if content_id(domain, payload) != identifier:
        _fail(f"{identity} changed")
    return identifier


@dataclass(frozen=True, slots=True)
class _Outcome:
    probability: Fraction
    next_state: Swipe2048State
    merge_score: int
    count: int


@dataclass(frozen=True, slots=True)
class _Row:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[_Outcome, ...]
    ground_count: int
    row_id: str

    @property
    def key(self) -> tuple[tuple[int, ...], str, str]:
        return self.state.board, self.state.status.value, self.action.value


def _replay_row(document: Any) -> _Row:
    row = _exact(
        document,
        {
            "schema", "schema_version", "state", "action", "outcomes",
            "ground_outcome_count", "ground_row_materialized_after_failed_proof",
            "spawn_law_known_exact_not_learned", "quotient_row_id",
        },
        "quotient row",
    )
    identifier = _domain_id(
        row, "quotient_row_id", CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN
    )
    state = _state(row["state"], "row state")
    try:
        action = Swipe2048Action(row["action"])
    except ValueError as error:
        raise ConstructionK7Standard2048IndependentVerifierV1Error(
            "row action changed"
        ) from error
    if (
        row["schema"] != "acfqp.standard_2048_quotient_row.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["ground_row_materialized_after_failed_proof"] is not True
        or row["spawn_law_known_exact_not_learned"] is not True
        or canonicalize_state_v1(state)[0] != state
        or action not in legal_actions_v1(state.board)
        or type(row["outcomes"]) is not list
        or not row["outcomes"]
        or type(row["ground_outcome_count"]) is not int
        or row["ground_outcome_count"] <= 0
    ):
        _fail("quotient row semantics changed")
    outcomes: list[_Outcome] = []
    for raw in row["outcomes"]:
        item = _exact(
            raw,
            {"probability", "next_state", "merge_score", "represented_ground_outcome_count"},
            "quotient outcome",
        )
        probability = _fraction(item["probability"], "outcome probability")
        next_state = _state(item["next_state"], "outcome next state")
        if (
            type(item["merge_score"]) is not int
            or item["merge_score"] < 0
            or type(item["represented_ground_outcome_count"]) is not int
            or item["represented_ground_outcome_count"] <= 0
        ):
            _fail("quotient outcome semantics changed")
        outcomes.append(
            _Outcome(
                probability,
                next_state,
                item["merge_score"],
                item["represented_ground_outcome_count"],
            )
        )
    parsed = _Row(state, action, tuple(outcomes), row["ground_outcome_count"], identifier)
    raw_ground = step_v1(state, action)
    grouped: dict[tuple[tuple[int, ...], str, int], list[Any]] = {}
    for ground in raw_ground:
        representative, _ = canonicalize_state_v1(ground.next_state)
        key = (representative.board, representative.status.value, ground.merge_score)
        grouped.setdefault(key, [Fraction(), 0])
        grouped[key][0] += ground.probability
        grouped[key][1] += 1
    expected = tuple(
        _Outcome(
            probability,
            Swipe2048State(board, Swipe2048Status(status)),
            score,
            count,
        )
        for (board, status, score), (probability, count) in sorted(grouped.items())
    )
    if (
        parsed.outcomes != expected
        or parsed.ground_count != len(raw_ground)
        or sum((item.probability for item in parsed.outcomes), Fraction()) != 1
        or sum(item.count for item in parsed.outcomes) != parsed.ground_count
    ):
        _fail("quotient row differs from exact 4x4 swipe/spawn replay")
    return parsed


def _replay_model(document: Any) -> tuple[str, dict[tuple[tuple[int, ...], str, str], _Row]]:
    model = _exact(
        document,
        {
            "schema", "schema_version", "semantics", "abstraction", "query_neutral",
            "known_spawn_distribution", "rows", "row_count", "ground_outcome_count",
            "world_model_id",
        },
        "world model",
    )
    identifier = _domain_id(
        model, "world_model_id", CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN
    )
    expected_spawn = [
        {"rank": rank, "probability": probability}
        for rank, probability in SPAWN_DISTRIBUTION
    ]
    if (
        model["schema"] != "acfqp.standard_2048_d4_world_model.v1"
        or model["schema_version"] != SCHEMA_VERSION
        or model["semantics"] != "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_EXACT_SPAWN_V1"
        or model["abstraction"] != "EXACT_D4_STATE_ACTION_QUOTIENT_V1"
        or model["query_neutral"] is not True
        or model["known_spawn_distribution"] != expected_spawn
        or type(model["rows"]) is not list
    ):
        _fail("world model semantics changed")
    rows = tuple(_replay_row(row) for row in model["rows"])
    by_key = {row.key: row for row in rows}
    if (
        len(by_key) != len(rows)
        or list(by_key) != sorted(by_key)
        or model["row_count"] != len(rows)
        or model["ground_outcome_count"] != sum(row.ground_count for row in rows)
    ):
        _fail("world model row inventory changed")
    return identifier, by_key


def _key(state: Swipe2048State, action: Swipe2048Action) -> tuple[tuple[int, ...], str, str]:
    representative, transformed_action, _ = canonicalize_state_action_v1(state, action)
    return representative.board, representative.status.value, transformed_action.value


@dataclass(frozen=True, slots=True)
class _Value:
    score: Fraction
    loss: Fraction
    action: Swipe2048Action | None


def _better(candidate: _Value, current: _Value | None) -> bool:
    if current is None or candidate.score != current.score:
        return current is None or candidate.score > current.score
    if candidate.loss != current.loss:
        return candidate.loss < current.loss
    if candidate.action is None:
        return False
    if current.action is None:
        return True
    return ACTION_ORDER.index(candidate.action) < ACTION_ORDER.index(current.action)


def _solve_model(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    root: Swipe2048State,
    horizon: int,
) -> tuple[_Value, tuple[str, ...]]:
    dependencies: set[str] = set()

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status: str, remaining: int) -> _Value:
        state = Swipe2048State(board, Swipe2048Status(status))
        representative, _ = canonicalize_state_v1(state)
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            return _Value(Fraction(), Fraction(), None)
        if representative.status is Swipe2048Status.LOST:
            return _Value(Fraction(), Fraction(1), None)
        best: _Value | None = None
        for action in legal_actions_v1(representative.board):
            row = rows.get(_key(representative, action))
            if row is None:
                _fail("certified audit depends on a missing quotient row")
            dependencies.add(row.row_id)
            score = Fraction()
            loss = Fraction()
            for outcome in row.outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (outcome.merge_score + child.score)
                loss += outcome.probability * child.loss
            candidate = _Value(score, loss, action)
            if _better(candidate, best):
                best = candidate
        if best is None:
            return _Value(Fraction(), Fraction(1), None)
        return best

    representative, transform = canonicalize_state_v1(root)
    value = solve(representative.board, representative.status.value, horizon)
    if value.action is None:
        return value, tuple(sorted(dependencies))
    return (
        _Value(value.score, value.loss, transform_action_v1(value.action, inverse_d4(transform))),
        tuple(sorted(dependencies)),
    )


def _missing(
    rows: Mapping[tuple[tuple[int, ...], str, str], _Row],
    root: Swipe2048State,
    horizon: int,
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    seen: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        representative, _ = canonicalize_state_v1(state)
        visit = (representative.board, representative.status.value, remaining)
        if remaining == 0 or representative.status is not Swipe2048Status.ACTIVE or visit in seen:
            return
        seen.add(visit)
        for action in legal_actions_v1(representative.board):
            row = rows.get(_key(representative, action))
            if row is None:
                missing.add(_key(representative, action))
            else:
                for outcome in row.outcomes:
                    walk(outcome.next_state, remaining - 1)

    walk(root, horizon)
    return tuple(sorted(missing))


def _replay_audit(
    document: Any,
    models: Mapping[str, Mapping[tuple[tuple[int, ...], str, str], _Row]],
    label: str,
) -> tuple[Swipe2048State, _Value | None]:
    audit = _exact(
        document,
        {
            "schema", "schema_version", "world_model_id", "root_state", "horizon",
            "objective", "status", "missing_frontier", "missing_frontier_count",
            "selected_action", "expected_merge_score", "loss_probability_within_horizon",
            "ordered_dependency_row_ids", "abstract_plan_id", "audit_id",
        },
        label,
    )
    _domain_id(audit, "audit_id", CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN)
    model_id = _cid(audit["world_model_id"], f"{label} model")
    rows = models.get(model_id)
    root = _state(audit["root_state"], f"{label} root")
    if (
        rows is None
        or audit["schema"] != "acfqp.standard_2048_partial_model_audit.v1"
        or audit["schema_version"] != SCHEMA_VERSION
        or audit["horizon"] != PLANNING_HORIZON
        or audit["objective"] != "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1"
    ):
        _fail(f"{label} header changed")
    missing = _missing(rows, root, audit["horizon"])
    missing_docs = [
        {"state": {"board_ranks": list(key[0]), "status": key[1]}, "action": key[2]}
        for key in missing
    ]
    if audit["missing_frontier"] != missing_docs or audit["missing_frontier_count"] != len(missing):
        _fail(f"{label} frontier changed")
    if missing:
        if (
            audit["status"] != "FAILED_PROOF_FRONTIER"
            or any(
                audit[key] not in (None, [])
                for key in (
                    "selected_action", "expected_merge_score", "loss_probability_within_horizon",
                    "ordered_dependency_row_ids", "abstract_plan_id",
                )
            )
        ):
            _fail(f"{label} failure classification changed")
        return root, None
    value, dependencies = _solve_model(rows, root, audit["horizon"])
    if value.action is None:
        _fail(f"{label} certified no action")
    plan_payload = {
        "schema": "acfqp.standard_2048_abstract_plan.v1",
        "schema_version": SCHEMA_VERSION,
        "world_model_id": model_id,
        "root_state": _sdoc(root),
        "horizon": audit["horizon"],
        "objective": audit["objective"],
        "selected_action": value.action.value,
        "expected_merge_score": _fdoc(value.score),
        "loss_probability_within_horizon": _fdoc(value.loss),
        "ordered_dependency_row_ids": list(dependencies),
    }
    if (
        audit["status"] != "CERTIFIED"
        or audit["selected_action"] != value.action.value
        or audit["expected_merge_score"] != value.score
        or audit["loss_probability_within_horizon"] != value.loss
        or audit["ordered_dependency_row_ids"] != list(dependencies)
        or audit["abstract_plan_id"]
        != content_id(CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN, plan_payload)
    ):
        _fail(f"{label} certified value changed")
    return root, value


def _direct(root: Swipe2048State, horizon: int) -> tuple[_Value, int, int]:
    touched: set[tuple[tuple[int, ...], str, str]] = set()
    ground_outcomes = 0

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status: str, remaining: int) -> _Value:
        nonlocal ground_outcomes
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _Value(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _Value(Fraction(), Fraction(1), None)
        best: _Value | None = None
        for action in legal_actions_v1(state.board):
            key = (state.board, state.status.value, action.value)
            outcomes = step_v1(state, action)
            if key not in touched:
                touched.add(key)
                ground_outcomes += len(outcomes)
            score = Fraction()
            loss = Fraction()
            for outcome in outcomes:
                child = solve(
                    outcome.next_state.board, outcome.next_state.status.value, remaining - 1
                )
                score += outcome.probability * (outcome.merge_score + child.score)
                loss += outcome.probability * child.loss
            candidate = _Value(score, loss, action)
            if _better(candidate, best):
                best = candidate
        if best is None:
            return _Value(Fraction(), Fraction(1), None)
        return best

    value = solve(root.board, root.status.value, horizon)
    return value, len(touched), ground_outcomes


def _replay_direct(document: Any, expected_root: Swipe2048State) -> tuple[int, int]:
    row = _exact(
        document,
        {
            "schema", "schema_version", "root_state", "horizon", "objective",
            "selected_action", "expected_merge_score", "loss_probability_within_horizon",
            "ground_state_action_row_count", "ground_outcome_count", "cold_model_per_decision",
            "quotient_or_prior_used", "matched_direct_plan_id",
        },
        "matched direct plan",
    )
    _domain_id(row, "matched_direct_plan_id", CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN)
    root = _state(row["root_state"], "matched direct root")
    value, row_count, outcome_count = _direct(root, row["horizon"])
    if (
        root != expected_root
        or row["schema"] != "acfqp.standard_2048_matched_direct_plan.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["horizon"] != PLANNING_HORIZON
        or row["objective"] != "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1"
        or value.action is None
        or row["selected_action"] != value.action.value
        or row["expected_merge_score"] != value.score
        or row["loss_probability_within_horizon"] != value.loss
        or row["ground_state_action_row_count"] != row_count
        or row["ground_outcome_count"] != outcome_count
        or row["cold_model_per_decision"] is not True
        or row["quotient_or_prior_used"] is not False
    ):
        _fail("matched direct plan changed")
    return row_count, outcome_count


@dataclass(frozen=True, slots=True)
class Standard2048IndependentVerificationV1:
    campaign_id: str
    preregistration_id: str
    world_model_id: str
    world_model_row_count: int
    direct_ground_row_count: int

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "preregistration_id": self.preregistration_id,
                "world_model_id": self.world_model_id,
                "world_model_row_count": self.world_model_row_count,
                "direct_ground_row_count": self.direct_ground_row_count,
                "standard_4x4_semantics_replayed": True,
                "h3_model_plans_replayed": True,
                "matched_direct_replayed": True,
                "heldout_d4_zero_ground_reuse_replayed": True,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "preregistration_id": self.preregistration_id,
            "world_model_id": self.world_model_id,
            "world_model_row_count": self.world_model_row_count,
            "direct_ground_row_count": self.direct_ground_row_count,
            "standard_4x4_semantics_replayed": True,
            "h3_model_plans_replayed": True,
            "matched_direct_replayed": True,
            "heldout_d4_zero_ground_reuse_replayed": True,
            "process_or_iid_authority_independently_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_receding_campaign_bytes_independently_v1(
    raw: bytes,
) -> Standard2048IndependentVerificationV1:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    root = loads_canonical_json(raw)
    if type(root) is not dict or canonical_json_bytes(root) != raw:
        _fail("campaign is not canonical JSON")
    expected_root_keys = {
        "schema", "schema_version", "proposed_contract_version", "profile_key",
        "preregistration", "initial_empty_model_audit", "first_decision_recovery_transactions",
        "first_decision_plan", "executed_first_transition", "successor_base_audit",
        "second_decision_recovery_transactions", "second_decision_plan", "heldout_d4_reuse_audit",
        "final_world_model", "matched_direct_baseline", "world_model_ground_row_count",
        "world_model_ground_outcome_count", "first_decision_ground_row_count",
        "second_decision_incremental_ground_row_count", "heldout_reuse_incremental_ground_row_count",
        "planning_horizon", "receding_horizon_decision_count",
        "standard_4x4_swipe_spawn_semantics_executed",
        "reusable_d4_quotient_world_model_synthesized",
        "ground_rows_materialized_only_after_failed_proof",
        "multi_step_planning_mainly_completed_in_abstract_model",
        "matched_cold_direct_baseline_present", "heldout_d4_model_reuse_without_ground",
        "spawn_law_learned_from_observations", "observation_derived_coordinate_invention_claimed",
        "unknown_support_learning_claimed", "formal_exact_iid_claimed",
        "full_standard_2048_game_completed", "real_game_ui_adapter_present",
        "broad_board_or_game_generalization_claimed", "official_execution_allowed",
        "official_scalar_cost", "official_N_break_even", "counter_completeness_gate_status",
        "workload_economics_gate_status", "campaign_id",
    }
    root = _exact(root, expected_root_keys, "campaign")
    campaign_id = _domain_id(
        root, "campaign_id", CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN
    )
    locks = {
        "spawn_law_learned_from_observations": False,
        "observation_derived_coordinate_invention_claimed": False,
        "unknown_support_learning_claimed": False,
        "formal_exact_iid_claimed": False,
        "full_standard_2048_game_completed": False,
        "real_game_ui_adapter_present": False,
        "broad_board_or_game_generalization_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    if (
        root["schema"] != "acfqp.standard_2048_receding_world_model_campaign.v1"
        or root["schema_version"] != SCHEMA_VERSION
        or root["proposed_contract_version"] != "2.0.154"
        or root["profile_key"] != PROFILE_KEY
        or any(root[key] != value for key, value in locks.items())
        or any(
            root[key] is not True
            for key in (
                "standard_4x4_swipe_spawn_semantics_executed",
                "reusable_d4_quotient_world_model_synthesized",
                "ground_rows_materialized_only_after_failed_proof",
                "multi_step_planning_mainly_completed_in_abstract_model",
                "matched_cold_direct_baseline_present",
                "heldout_d4_model_reuse_without_ground",
            )
        )
        or root["planning_horizon"] != PLANNING_HORIZON
        or root["receding_horizon_decision_count"] != RECEDING_DECISION_COUNT
    ):
        _fail("campaign header or claim locks changed")

    prereg = _exact(
        root["preregistration"],
        {
            "schema", "schema_version", "profile_key", "environment_semantics",
            "source_root_state", "heldout_root_state", "heldout_transform", "planning_horizon",
            "receding_decision_count", "spawn_tape_seed", "goal_rank",
            "query_and_seed_frozen_before_model_construction",
            "matched_direct_control_frozen_before_model_construction", "exact_known_spawn_law",
            "standard_2048_preregistration_id",
        },
        "preregistration",
    )
    prereg_id = _domain_id(
        prereg, "standard_2048_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN,
    )
    source = _state(prereg["source_root_state"], "source root")
    heldout = _state(prereg["heldout_root_state"], "heldout root")
    if (
        prereg["schema"] != "acfqp.standard_2048_receding_preregistration.v1"
        or prereg["schema_version"] != SCHEMA_VERSION
        or prereg["profile_key"] != PROFILE_KEY
        or prereg["environment_semantics"] != "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1"
        or prereg["heldout_transform"] != HELDOUT_TRANSFORM.value
        or prereg["planning_horizon"] != PLANNING_HORIZON
        or prereg["receding_decision_count"] != RECEDING_DECISION_COUNT
        or prereg["spawn_tape_seed"] != HELDOUT_SPAWN_SEED
        or prereg["goal_rank"] != GOAL_RANK
        or prereg["query_and_seed_frozen_before_model_construction"] is not True
        or prereg["matched_direct_control_frozen_before_model_construction"] is not True
        or prereg["exact_known_spawn_law"]
        != [{"rank": rank, "probability": p} for rank, p in SPAWN_DISTRIBUTION]
        or heldout.board != transform_board_v1(source.board, HELDOUT_TRANSFORM)
    ):
        _fail("preregistration semantics changed")

    final_model_id, final_rows = _replay_model(root["final_world_model"])
    empty_model_payload = {
        "schema": "acfqp.standard_2048_d4_world_model.v1",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_EXACT_SPAWN_V1",
        "abstraction": "EXACT_D4_STATE_ACTION_QUOTIENT_V1",
        "query_neutral": True,
        "known_spawn_distribution": [
            {"rank": rank, "probability": p} for rank, p in SPAWN_DISTRIBUTION
        ],
        "rows": [], "row_count": 0, "ground_outcome_count": 0,
    }
    empty_model_id = content_id(CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN, empty_model_payload)
    models: dict[str, Mapping[tuple[tuple[int, ...], str, str], _Row]] = {
        empty_model_id: {},
        final_model_id: final_rows,
    }
    # Every intermediate model is reconstructed from the transaction row-ID additions.
    known_rows_by_id = {row.row_id: row for row in final_rows.values()}
    current: dict[tuple[tuple[int, ...], str, str], _Row] = {}
    current_id = empty_model_id
    first_count = 0
    second_count = 0
    successor_transaction_root = _state(
        _exact(
            root["successor_base_audit"],
            {
                "schema", "schema_version", "world_model_id", "root_state", "horizon",
                "objective", "status", "missing_frontier", "missing_frontier_count",
                "selected_action", "expected_merge_score", "loss_probability_within_horizon",
                "ordered_dependency_row_ids", "abstract_plan_id", "audit_id",
            },
            "successor base audit preview",
        )["root_state"],
        "successor transaction root",
    )
    transaction_groups = (
        (root["first_decision_recovery_transactions"], "first", source),
        (root["second_decision_recovery_transactions"], "second", successor_transaction_root),
    )
    for transactions, group, transaction_root in transaction_groups:
        if type(transactions) is not list:
            _fail("transaction collection changed")
        for ordinal, transaction in enumerate(transactions, 1):
            tx = _exact(
                transaction,
                {
                    "transaction_index", "failed_audit_id", "failed_status",
                    "predecessor_world_model_id", "recovered_frontier_count",
                    "recovered_ground_outcome_count", "recovered_quotient_row_ids",
                    "successor_world_model_id", "ground_access_before_failed_audit",
                },
                "recovery transaction",
            )
            if (
                tx["transaction_index"] != ordinal
                or tx["failed_status"] != "FAILED_PROOF_FRONTIER"
                or tx["predecessor_world_model_id"] != current_id
                or tx["ground_access_before_failed_audit"] is not False
                or type(tx["recovered_quotient_row_ids"]) is not list
                or len(tx["recovered_quotient_row_ids"]) != tx["recovered_frontier_count"]
            ):
                _fail("recovery transaction identity changed")
            missing = _missing(current, transaction_root, PLANNING_HORIZON)
            missing_documents = [
                {
                    "state": {"board_ranks": list(key[0]), "status": key[1]},
                    "action": key[2],
                }
                for key in missing
            ]
            failed_payload = {
                "schema": "acfqp.standard_2048_partial_model_audit.v1",
                "schema_version": SCHEMA_VERSION,
                "world_model_id": current_id,
                "root_state": _sdoc(transaction_root),
                "horizon": PLANNING_HORIZON,
                "objective": "MAX_EXPECTED_MERGE_SCORE_THEN_MIN_LOSS_PROBABILITY_V1",
                "status": "FAILED_PROOF_FRONTIER",
                "missing_frontier": missing_documents,
                "missing_frontier_count": len(missing),
                "selected_action": None,
                "expected_merge_score": None,
                "loss_probability_within_horizon": None,
                "ordered_dependency_row_ids": [],
                "abstract_plan_id": None,
            }
            if (
                not missing
                or tx["failed_audit_id"]
                != content_id(
                    CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN,
                    failed_payload,
                )
            ):
                _fail("transaction is not authorized by its exact failed frontier")
            expected_recovered_ids = []
            for key in missing:
                final_row = final_rows.get(key)
                if final_row is None:
                    _fail("failed frontier is absent from the final model")
                expected_recovered_ids.append(final_row.row_id)
            if tx["recovered_quotient_row_ids"] != expected_recovered_ids:
                _fail("transaction recovered rows outside its failed frontier")
            added: list[_Row] = []
            for identifier in tx["recovered_quotient_row_ids"]:
                row = known_rows_by_id.get(_cid(identifier, "recovered row"))
                if row is None or row.key in current:
                    _fail("transaction recovered a missing or duplicate row")
                current[row.key] = row
                added.append(row)
            if tx["recovered_ground_outcome_count"] != sum(row.ground_count for row in added):
                _fail("transaction ground outcome count changed")
            model_payload = {
                "schema": "acfqp.standard_2048_d4_world_model.v1",
                "schema_version": SCHEMA_VERSION,
                "semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_EXACT_SPAWN_V1",
                "abstraction": "EXACT_D4_STATE_ACTION_QUOTIENT_V1",
                "query_neutral": True,
                "known_spawn_distribution": [
                    {"rank": rank, "probability": p} for rank, p in SPAWN_DISTRIBUTION
                ],
                "rows": [
                    {
                        "schema": "acfqp.standard_2048_quotient_row.v1",
                        "schema_version": SCHEMA_VERSION,
                        "state": _sdoc(row.state),
                        "action": row.action.value,
                        "outcomes": [
                            {
                                "probability": _fdoc(outcome.probability),
                                "next_state": _sdoc(outcome.next_state),
                                "merge_score": outcome.merge_score,
                                "represented_ground_outcome_count": outcome.count,
                            }
                            for outcome in row.outcomes
                        ],
                        "ground_outcome_count": row.ground_count,
                        "ground_row_materialized_after_failed_proof": True,
                        "spawn_law_known_exact_not_learned": True,
                        "quotient_row_id": row.row_id,
                    }
                    for _, row in sorted(current.items())
                ],
                "row_count": len(current),
                "ground_outcome_count": sum(row.ground_count for row in current.values()),
            }
            current_id = content_id(CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN, model_payload)
            models[current_id] = dict(current)
            if tx["successor_world_model_id"] != current_id:
                _fail("transaction successor model changed")
            if group == "first":
                first_count += len(added)
            else:
                second_count += len(added)
    if current_id != final_model_id or current != final_rows:
        _fail("transaction chain did not reconstruct the final model")

    initial_root, initial_value = _replay_audit(
        root["initial_empty_model_audit"], models, "initial audit"
    )
    first_root, first_value = _replay_audit(root["first_decision_plan"], models, "first plan")
    successor_base_root, successor_base_value = _replay_audit(
        root["successor_base_audit"], models, "successor base audit"
    )
    successor_root, second_value = _replay_audit(
        root["second_decision_plan"], models, "second plan"
    )
    heldout_root, heldout_value = _replay_audit(
        root["heldout_d4_reuse_audit"], models, "heldout reuse audit"
    )
    if (
        initial_root != source
        or initial_value is not None
        or first_root != source
        or first_value is None
        or successor_base_root != successor_root
        or successor_base_value is not None
        or second_value is None
        or heldout_root != heldout
        or heldout_value is None
    ):
        _fail("audit root or classification chain changed")

    execution = _exact(
        root["executed_first_transition"],
        {
            "action", "selected_spawn_tape_digest", "selected_outcome_probability",
            "spawned_cell", "spawned_rank", "merge_score", "successor_state",
        },
        "executed transition",
    )
    action = Swipe2048Action(execution["action"])
    outcome, digest = select_seeded_outcome_v1(
        step_v1(source, action), seed=HELDOUT_SPAWN_SEED, decision_index=0
    )
    if (
        first_value.action is not action
        or execution["selected_spawn_tape_digest"] != digest
        or execution["selected_outcome_probability"] != outcome.probability
        or execution["spawned_cell"] != outcome.spawned_cell
        or execution["spawned_rank"] != outcome.spawned_rank
        or execution["merge_score"] != outcome.merge_score
        or execution["successor_state"] != _sdoc(outcome.next_state)
        or successor_root != outcome.next_state
    ):
        _fail("executed first transition changed")

    direct = _exact(
        root["matched_direct_baseline"],
        {
            "first_decision", "second_decision", "total_ground_state_action_row_count",
            "total_ground_outcome_count",
        },
        "matched direct baseline",
    )
    first_direct_rows, first_direct_outcomes = _replay_direct(direct["first_decision"], source)
    second_direct_rows, second_direct_outcomes = _replay_direct(
        direct["second_decision"], successor_root
    )
    if (
        direct["total_ground_state_action_row_count"] != first_direct_rows + second_direct_rows
        or direct["total_ground_outcome_count"] != first_direct_outcomes + second_direct_outcomes
        or root["world_model_ground_row_count"] != len(final_rows)
        or root["world_model_ground_outcome_count"]
        != sum(row.ground_count for row in final_rows.values())
        or root["first_decision_ground_row_count"] != first_count
        or root["second_decision_incremental_ground_row_count"] != second_count
        or root["heldout_reuse_incremental_ground_row_count"] != 0
        or first_value.action.value != direct["first_decision"]["selected_action"]
        or first_value.score != direct["first_decision"]["expected_merge_score"]
        or second_value.action.value != direct["second_decision"]["selected_action"]
        or second_value.score != direct["second_decision"]["expected_merge_score"]
        or heldout_value.action
        is not transform_action_v1(first_value.action, HELDOUT_TRANSFORM)
    ):
        _fail("campaign work totals, direct match, or heldout transport changed")

    return Standard2048IndependentVerificationV1(
        campaign_id, prereg_id, final_model_id, len(final_rows),
        first_direct_rows + second_direct_rows,
    )


__all__ = (
    "ConstructionK7Standard2048IndependentVerifierV1Error",
    "Standard2048IndependentVerificationV1",
    "verify_standard_2048_receding_campaign_bytes_independently_v1",
)
