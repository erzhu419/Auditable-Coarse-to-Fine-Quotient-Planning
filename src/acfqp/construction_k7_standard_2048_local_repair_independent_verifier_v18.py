"""Producer-free semantic replay of the V18 local-repair campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
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
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    support_outcomes_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "18.0.0"
PREREGISTRATION_ID = "d7e0a21868fc53854db8df3818c6cfbb6d10ea504802ed0e784dc69e8b7ad747"
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
EXPECTED_CAMPAIGN_ID = "666509cc46b596fb1241fb5d066440e31547cbbd540b79f5bd535acfa3232ede"
EXPECTED_VERIFICATION_ID = "0529828cc943310226f2643b575a0f0985c7075781630814d4c987b972a1a9db"
V16_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
HORIZON = 3
BASE_RATE = Fraction(1, 10)
TARGET_THRESHOLD = 4
TARGET_OVERRIDE_RATE = Fraction(1, 5)
TARGET_BOARDS = (
    (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6, 2, 2, 1, 1),
    (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6, 1, 1, 2, 2),
    (1, 2, 3, 4, 1, 2, 3, 4, 2, 3, 4, 5, 2, 3, 4, 5),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v177-local-repair-target-{index:02d}-20260813"
    for index in range(3)
)


class ConstructionK7Standard2048LocalRepairIndependentVerifierV18Error(ValueError):
    """The campaign differs from independent recovery and planning replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LocalRepairIndependentVerifierV18Error(message)


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} schema changed")
    return value


def _state(document: Any) -> Swipe2048State:
    row = _exact_keys(document, {"board_ranks", "status"}, "state")
    state = Swipe2048State(tuple(row["board_ranks"]), Swipe2048Status(row["status"]))
    if state_from_board_v1(state.board) != state:
        _fail("state status changed")
    return state


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
    if max(board) >= GOAL_RANK:
        return Swipe2048Status.WON.value
    return Swipe2048Status.ACTIVE.value if _actions(board) else Swipe2048Status.LOST.value


def _target_probability(empty_count: int) -> Fraction:
    return TARGET_OVERRIDE_RATE if empty_count <= TARGET_THRESHOLD else BASE_RATE


def _target_outcomes(state: Swipe2048State, action: Swipe2048Action) -> tuple[Swipe2048Outcome, ...]:
    support = support_outcomes_v1(state, action)
    count = len(support) // 2
    p2 = _target_probability(count)
    by_rank = {1: 1 - p2, 2: p2}
    return tuple(
        Swipe2048Outcome(
            by_rank[row.spawned_rank] / count,
            row.next_state,
            row.merge_score,
            row.spawned_cell,
            row.spawned_rank,
        )
        for row in support
    )


def _frontier(root: Swipe2048State) -> tuple[int, ...]:
    counts: set[int] = set()
    seen: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(board: tuple[int, ...], status: str, remaining: int) -> None:
        board = _canonical(board)
        key = (board, status, remaining)
        if remaining == 0 or status != "ACTIVE" or key in seen:
            return
        seen.add(key)
        for action in _actions(board):
            moved, _ = _swipe(board, action)
            empty = tuple(i for i, rank in enumerate(moved) if rank == 0)
            counts.add(len(empty))
            for cell in empty:
                for rank in (1, 2):
                    child = list(moved)
                    child[cell] = rank
                    child_board = tuple(child)
                    walk(child_board, _status(child_board), remaining - 1)

    walk(root.board, root.status.value, HORIZON)
    return tuple(sorted(counts))


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


class _Planner:
    def __init__(self) -> None:
        self.cache: dict[tuple[tuple[int, ...], str, int], _Value] = {}

    def action_value(self, board: tuple[int, ...], action: str, remaining: int) -> _Value:
        moved, merge = _swipe(board, action)
        empty = tuple(i for i, rank in enumerate(moved) if rank == 0)
        p2 = _target_probability(len(empty))
        score = Fraction()
        loss = Fraction()
        for cell in empty:
            for rank, rank_probability in ((1, 1 - p2), (2, p2)):
                child = list(moved)
                child[cell] = rank
                child_board = tuple(child)
                value = self.state_value(child_board, _status(child_board), remaining - 1)
                probability = rank_probability / len(empty)
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
        return tuple(self.action_value(state.board, action, HORIZON) for action in _actions(state.board))


def _best(values: tuple[_Value, ...]) -> _Value:
    best = None
    for value in values:
        if _better(value, best):
            best = value
    if best is None or best.action is None:
        _fail("active root has no action")
    return best


def _expected_root_rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {
            "action": value.action,
            "expected_merge_score": value.score,
            "loss_probability_within_horizon": value.loss,
        }
        for value in values
    ]


def apply_independently_replayed_target_outcomes_v18(
    state: Swipe2048State,
    action: Swipe2048Action,
) -> tuple[Swipe2048Outcome, ...]:
    """Expose the producer-free target row for successor verifiers."""

    if type(state) is not Swipe2048State or type(action) is not Swipe2048Action:
        _fail("independent target-row primitive requires exact inputs")
    return _target_outcomes(state, action)


def independently_replay_rank_two_probability_v18(empty_count: int) -> Fraction:
    """Expose the exact producer-free local distinction query result."""

    if type(empty_count) is not int or not 1 <= empty_count <= 16:
        _fail("independent rank-law query is outside the registered board")
    return _target_probability(empty_count)


def independently_replay_structural_frontier_v18(
    state: Swipe2048State,
) -> tuple[int, ...]:
    """Expose the exact H=3 empty-count proof frontier."""

    if type(state) is not Swipe2048State:
        _fail("independent frontier primitive requires one exact state")
    return _frontier(state)


def independently_replay_target_root_values_v18(
    state: Swipe2048State,
) -> tuple[tuple[str, Fraction, Fraction], ...]:
    """Return exact H=3 root values from the independent target semantics."""

    if type(state) is not Swipe2048State:
        _fail("independent root-value primitive requires one exact state")
    values = _Planner().roots(state)
    return tuple((row.action, row.score, row.loss) for row in values if row.action is not None)


def _verify_preregistration(document: Any) -> None:
    if type(document) is not dict:
        _fail("embedded preregistration changed")
    payload = {key: value for key, value in document.items() if key != "local_repair_preregistration_id"}
    if (
        document.get("local_repair_preregistration_id") != PREREGISTRATION_ID
        or content_id(CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN, payload)
        != PREREGISTRATION_ID
        or document.get("outcome_fields_present") is not False
        or document.get("target_execution_performed") is not False
    ):
        _fail("embedded preregistration identity or locks changed")


def _verify_id(document: dict[str, Any], id_key: str, domain: str, label: str) -> None:
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")


def _verify_semantics(document: dict[str, Any]) -> tuple[int, int]:
    _verify_preregistration(document.get("local_repair_preregistration"))
    kernel_document = document.get("target_kernel_binding")
    if type(kernel_document) is not dict:
        _fail("kernel binding changed")
    _verify_id(kernel_document, "target_kernel_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN, "kernel")
    if kernel_document["target_kernel_id"] != TARGET_KERNEL_ID:
        _fail("target kernel identity changed")
    overlay = document.get("persistent_local_repair_overlay")
    if type(overlay) is not dict:
        _fail("overlay changed")
    _verify_id(overlay, "local_repair_overlay_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN, "overlay")
    if (
        overlay.get("selected_override_threshold") != TARGET_THRESHOLD
        or overlay.get("selected_override_rank_two_probability") != TARGET_OVERRIDE_RATE
        or overlay.get("base_rank_two_probability") != BASE_RATE
        or overlay.get("candidate_version_space_count") != 1
        or overlay.get("ground_distinction_query_count") != 2
    ):
        _fail("overlay program differs from independent recovery")

    query_count = failure_count = 0
    for episode_index, episode in enumerate(document.get("episodes", [])):
        if type(episode) is not dict or episode.get("episode_index") != episode_index:
            _fail("episode ordering changed")
        _verify_id(episode, "local_repair_episode_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN, "episode")
        if episode.get("execution_seed") != TARGET_SEEDS[episode_index]:
            _fail("episode seed changed")
        state = state_from_board_v1(TARGET_BOARDS[episode_index])
        planner = _Planner()
        for decision_index, decision in enumerate(episode.get("decisions", [])):
            if decision.get("decision_index") != decision_index or _state(decision.get("predecision_state")) != state:
                _fail("decision state or order changed")
            frontier = _frontier(state)
            if tuple(decision.get("structural_frontier_empty_counts", [])) != frontier:
                _fail("structural frontier changed")
            failure = decision.get("base_failure")
            acquisitions = decision.get("local_acquisitions")
            if episode_index == 0 and decision_index == 0:
                if type(failure) is not dict or type(acquisitions) is not list:
                    _fail("first failed certificate or acquisition disappeared")
                _verify_id(failure, "local_repair_failure_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN, "failure")
                if (
                    failure.get("ground_probability_query_count_before_failure") != 0
                    or failure.get("target_transition_accessed_before_failure") is not False
                    or tuple(failure.get("disagreement_empty_counts", [])) != frontier
                ):
                    _fail("failure-before-ground order changed")
                if [row.get("queried_empty_count") for row in acquisitions] != [5, 4]:
                    _fail("adaptive distinction query order changed")
                for row, expected_probability in zip(acquisitions, (BASE_RATE, TARGET_OVERRIDE_RATE), strict=True):
                    _verify_id(row, "local_repair_acquisition_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN, "acquisition")
                    if row.get("observed_rank_two_probability") != expected_probability:
                        _fail("ground distinction answer changed")
                query_count += 2
                failure_count += 1
            elif failure is not None or acquisitions != []:
                _fail("persistent overlay was not reused without ground acquisition")
            certificate = decision.get("certificate")
            if type(certificate) is not dict:
                _fail("certificate changed")
            _verify_id(certificate, "local_repair_certificate_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN, "certificate")
            values = planner.roots(state)
            selected = _best(values)
            if (
                certificate.get("root_action_exact_values") != _expected_root_rows(values)
                or certificate.get("selected_action") != selected.action
                or certificate.get("selected_expected_merge_score") != selected.score
                or certificate.get("selected_loss_probability_within_horizon") != selected.loss
                or certificate.get("ground_probability_query_count_during_planning") != 0
                or certificate.get("ground_state_action_row_count") != 0
            ):
                _fail("abstract repaired plan certificate changed")
            control = decision.get("matched_cold_target_ground_control")
            if type(control) is not dict or control.get("root_action_exact_values") != _expected_root_rows(values):
                _fail("cold target-ground values changed")
            if control.get("lane") != "STANDALONE_EVALUATION_ONLY" or control.get("route_or_certificate_authority") is not False:
                _fail("evaluation lane changed")
            if decision.get("executed_action") != selected.action or decision.get("certificate_frozen_before_target_transition") is not True:
                _fail("certificate freeze or execution changed")
            outcome, tape = select_seeded_outcome_v1(
                _target_outcomes(state, Swipe2048Action(selected.action)),
                seed=TARGET_SEEDS[episode_index],
                decision_index=decision_index,
            )
            if decision.get("execution_tape_sha256") != tape or _state(decision.get("executed_next_state")) != outcome.next_state:
                _fail("target transition replay changed")
            state = outcome.next_state
        if _state(episode.get("final_state")) != state:
            _fail("episode final state changed")
    return failure_count, query_count


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048LocalRepairIndependentVerificationV18:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("independent verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("independent verification bytes changed")
        payload = {key: value for key, value in document.items() if key != "local_repair_verification_id"}
        if (
            document.get("local_repair_verification_id") != self.verification_id
            or document.get("local_repair_campaign_id") != self.campaign_id
            or content_id(CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN, payload)
            != self.verification_id
        ):
            _fail("independent verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("verification is not an object")
        return document


def verify_standard_2048_local_repair_bytes_independently_v18(
    canonical_bytes: bytes,
) -> Standard2048LocalRepairIndependentVerificationV18:
    observed = loads_canonical_json(canonical_bytes)
    if type(observed) is not dict or canonical_json_bytes(observed) != canonical_bytes:
        _fail("campaign bytes changed")
    _verify_id(observed, "local_repair_campaign_id", CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN, "campaign")
    if observed.get("local_repair_campaign_id") != EXPECTED_CAMPAIGN_ID:
        _fail("campaign identity changed")
    failure_count, query_count = _verify_semantics(observed)
    if (
        failure_count != 1
        or query_count != 2
        or observed.get("decision_count") != 12
        or observed.get("program_prior_ground_query_difference") != 3
        or observed.get("all_root_action_values_and_selected_actions_match_cold_target_ground") is not True
        or observed.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or observed.get("official_execution_allowed") is not False
    ):
        _fail("campaign aggregate or claim locks changed")
    payload = {
        "schema": "acfqp.standard_2048_local_repair_independent_verification.v18",
        "schema_version": SCHEMA_VERSION,
        "local_repair_preregistration_id": PREREGISTRATION_ID,
        "local_repair_campaign_id": EXPECTED_CAMPAIGN_ID,
        "target_kernel_id": TARGET_KERNEL_ID,
        "base_failure_before_ground_independently_verified": True,
        "two_adaptive_ground_distinctions_independently_replayed": True,
        "unique_reusable_program_overlay_independently_recovered": True,
        "all_12_repaired_abstract_h3_plans_independently_replayed": True,
        "all_12_target_transitions_independently_replayed": True,
        "all_root_values_and_actions_match_cold_target_ground": True,
        "registered_program_prior_query_difference_verified": 3,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_broad_world_model_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN, payload
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen independent verification identity changed")
    return Standard2048LocalRepairIndependentVerificationV18(
        _ISSUER,
        canonical_json_bytes({**payload, "local_repair_verification_id": verification_id}),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048LocalRepairIndependentVerifierV18Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048LocalRepairIndependentVerificationV18",
    "apply_independently_replayed_target_outcomes_v18",
    "independently_replay_rank_two_probability_v18",
    "independently_replay_structural_frontier_v18",
    "independently_replay_target_root_values_v18",
    "verify_standard_2048_local_repair_bytes_independently_v18",
)
