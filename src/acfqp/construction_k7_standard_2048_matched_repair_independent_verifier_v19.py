"""Producer-free replay of matched active and no-prior 2048 repair."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_repair_independent_verifier_v18 as target_v18
from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
from acfqp.domains.g2048 import D4_ELEMENTS, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "19.0.0"
PREREGISTRATION_ID = "247ad097f7e4b46831cf4bde18193e440a413a579a9613a1359b2f20ecdecc43"
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
EXPECTED_CAMPAIGN_ID = "1154337025f11c493a1805744f27ea7e9057fd2f2b4884c8e3eb46e4535847b7"
EXPECTED_VERIFICATION_ID = "123b803fff1d7a9a9acf638150d0c5d0f9212757dabb0d1e23419bddeea731c7"
PROGRAM_ARM = "PROGRAM_PRIOR_ACTIVE_SPLIT"
TABLE_ARM = "STRICT_NO_PRIOR_CONTEXT_TABLE"
HORIZON = 3
BASE_RATE = Fraction(1, 10)
TARGET_BOARDS = (
    (1, 2, 4, 4, 3, 4, 4, 0, 3, 2, 3, 2, 6, 3, 1, 1),
    (3, 0, 5, 1, 5, 3, 1, 2, 4, 5, 0, 2, 4, 6, 5, 2),
    (4, 2, 4, 0, 1, 4, 6, 3, 3, 0, 2, 0, 6, 0, 3, 3),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v178-matched-repair-target-{index:02d}-20260813"
    for index in range(3)
)
Candidate = tuple[str, int, Fraction]


class ConstructionK7Standard2048MatchedRepairIndependentVerifierV19Error(ValueError):
    """Matched campaign differs from independent acquisition or target replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MatchedRepairIndependentVerifierV19Error(message)


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state schema changed")
    state = Swipe2048State(tuple(document["board_ranks"]), Swipe2048Status(document["status"]))
    if state_from_board_v1(state.board) != state:
        _fail("state status changed")
    return state


def _candidates() -> tuple[Candidate, ...]:
    rows: list[Candidate] = [("NO_OVERRIDE", 0, BASE_RATE)]
    for threshold in range(1, 9):
        for rate in (Fraction(3, 20), Fraction(1, 5), Fraction(1, 4)):
            rows.append(
                (
                    f"EMPTY_COUNT_LE_{threshold}__RANK_TWO_{rate.numerator}_OVER_{rate.denominator}",
                    threshold,
                    rate,
                )
            )
    return tuple(rows)


def _predict(candidate: Candidate, count: int) -> Fraction:
    return candidate[2] if candidate[1] and count <= candidate[1] else BASE_RATE


def _active_query(candidates: tuple[Candidate, ...], frontier: tuple[int, ...]) -> int:
    scores = []
    for count in frontier:
        buckets: dict[Fraction, int] = {}
        for candidate in candidates:
            prediction = _predict(candidate, count)
            buckets[prediction] = buckets.get(prediction, 0) + 1
        if len(buckets) > 1:
            scores.append((max(buckets.values()), count))
    if not scores:
        _fail("independent active query has no disagreement")
    return min(scores)[1]


@lru_cache(maxsize=None)
def _canonical(board: tuple[int, ...]) -> tuple[int, ...]:
    rows = []
    for transform in D4_ELEMENTS:
        result = [0] * 16
        for source, rank in enumerate(board):
            result[transform_cell(source, 4, transform)] = rank
        rows.append(tuple(result))
    return min(rows)


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


def _rows(values: tuple[_Value, ...]) -> list[dict[str, Any]]:
    return [
        {"action": row.action, "expected_merge_score": row.score, "loss_probability_within_horizon": row.loss}
        for row in values
    ]


def _verify_preregistration(document: Any) -> None:
    row = _verify_id(
        document,
        "matched_repair_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN,
        "preregistration",
    )
    if (
        row["matched_repair_preregistration_id"] != PREREGISTRATION_ID
        or row.get("outcome_fields_present") is not False
        or row.get("target_execution_performed") is not False
        or row.get("strict_query_reduction_observed") is not False
    ):
        _fail("preregistration identity or outcome locks changed")


def _verify_failure(
    observed: Any, *, arm: str, episode: int, decision: int,
    state: Swipe2048State, frontier: tuple[int, ...], unresolved: tuple[int, ...],
) -> dict[str, Any]:
    row = _verify_id(
        observed, "matched_repair_failure_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN,
        "failure",
    )
    if (
        row.get("arm") != arm
        or row.get("episode_index") != episode
        or row.get("decision_index") != decision
        or _state(row.get("root_state")) != state
        or tuple(row.get("frontier_empty_counts", [])) != frontier
        or tuple(row.get("unresolved_empty_counts", [])) != unresolved
        or row.get("ground_query_count_before_failure") != 0
        or row.get("target_transition_accessed_before_failure") is not False
        or row.get("cold_ground_planner_accessed_before_failure") is not False
        or row.get("failure_frozen_before_acquisition") is not True
    ):
        _fail("failed-certificate semantics changed")
    return row


def _verify_acquisition(
    row: Any, *, arm: str, failure_id: str, ordinal: int, count: int,
    before: int | None, after: int | None,
) -> None:
    item = _verify_id(
        row, "matched_repair_acquisition_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN,
        "acquisition",
    )
    if (
        item.get("arm") != arm
        or item.get("matched_repair_failure_id") != failure_id
        or item.get("query_ordinal_within_arm") != ordinal
        or item.get("queried_empty_count") != count
        or item.get("observed_rank_two_probability")
        != target_v18.independently_replay_rank_two_probability_v18(count)
        or item.get("candidate_count_before") != before
        or item.get("candidate_count_after") != after
        or item.get("query_was_in_frozen_failed_frontier") is not True
        or item.get("query_after_failure_freeze") is not True
        or item.get("full_ground_state_action_row_materialized") is not False
    ):
        _fail("acquisition semantics changed")


def _verify_overlay(
    row: Any, *, arm: str, acquisition_ids: list[str], candidates: tuple[Candidate, ...],
    table: dict[int, Fraction],
) -> dict[str, Any]:
    item = _verify_id(
        row, "matched_repair_overlay_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN,
        "overlay",
    )
    if item.get("arm") != arm or item.get("acquisition_ids") != acquisition_ids:
        _fail("overlay lineage changed")
    if arm == PROGRAM_ARM:
        expected_prediction = [
            {"empty_count": count, "rank_two_probability": _predict(candidates[0], count)}
            for count in range(1, 17)
        ]
        if (
            len(candidates) != 1
            or item.get("selected_candidate_key") != candidates[0][0]
            or item.get("candidate_version_space_count") != 1
            or item.get("context_table") != []
            or item.get("prediction_table") != expected_prediction
        ):
            _fail("program overlay changed")
    else:
        expected_table = [
            {"empty_count": count, "rank_two_probability": table[count]}
            for count in sorted(table)
        ]
        if (
            item.get("selected_candidate_key") is not None
            or item.get("candidate_version_space_count") != 0
            or item.get("context_table") != expected_table
            or item.get("prediction_table") != []
        ):
            _fail("no-prior table overlay changed")
    if item.get("persistent_reuse") is not True or item.get("full_state_action_table_materialized") is not False:
        _fail("overlay claim locks changed")
    return item


def _verify_certificate(
    observed: Any, *, arm: str, episode: int, decision: int, state: Swipe2048State,
    overlay_id: str, planner: _Planner,
) -> tuple[_Value, ...]:
    row = _verify_id(
        observed, "matched_repair_certificate_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN,
        "certificate",
    )
    before = (planner.rows, planner.outcomes)
    values = planner.roots(state)
    selected = _best(values)
    if (
        row.get("arm") != arm
        or row.get("episode_index") != episode
        or row.get("decision_index") != decision
        or _state(row.get("root_state")) != state
        or row.get("matched_repair_overlay_id") != overlay_id
        or row.get("root_action_exact_values") != _rows(values)
        or row.get("selected_action") != selected.action
        or row.get("selected_expected_merge_score") != selected.score
        or row.get("selected_loss_probability_within_horizon") != selected.loss
        or row.get("factored_action_row_evaluation_count") != planner.rows - before[0]
        or row.get("factored_support_outcome_evaluation_count") != planner.outcomes - before[1]
        or row.get("ground_query_count_during_planning") != 0
        or row.get("ground_state_action_row_count") != 0
        or row.get("target_transition_accessed_before_certificate_freeze") is not False
    ):
        _fail("matched repaired certificate changed")
    return values


def _replay(document: dict[str, Any]) -> tuple[int, int]:
    _verify_preregistration(document.get("matched_repair_preregistration"))
    if document.get("target_kernel_id") != TARGET_KERNEL_ID:
        _fail("target kernel binding changed")
    candidates = _candidates()
    table: dict[int, Fraction] = {}
    program_ids: list[str] = []
    table_ids: list[str] = []
    program_planner = table_planner = None
    program_overlay_id = table_overlay_id = None
    program_failures = table_failures = 0
    for episode_index, episode in enumerate(document.get("episodes", [])):
        _verify_id(
            episode, "matched_repair_episode_id",
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN,
            "episode",
        )
        if episode.get("episode_index") != episode_index or episode.get("execution_seed") != TARGET_SEEDS[episode_index]:
            _fail("episode identity or ordering changed")
        state = state_from_board_v1(TARGET_BOARDS[episode_index])
        if _state(episode.get("initial_state")) != state:
            _fail("episode initial state changed")
        for decision_index, decision in enumerate(episode.get("decisions", [])):
            if decision.get("decision_index") != decision_index or _state(decision.get("predecision_state")) != state:
                _fail("decision state or ordering changed")
            frontier = target_v18.independently_replay_structural_frontier_v18(state)
            if tuple(decision.get("frontier_empty_counts", [])) != frontier:
                _fail("decision frontier changed")
            program = decision.get("program_prior_arm")
            table_arm = decision.get("no_prior_table_arm")
            if type(program) is not dict or type(table_arm) is not dict:
                _fail("matched arm document changed")
            disagreement = tuple(
                count for count in frontier
                if len({_predict(candidate, count) for candidate in candidates}) > 1
            )
            if disagreement:
                failure = _verify_failure(
                    program.get("failure"), arm=PROGRAM_ARM, episode=episode_index,
                    decision=decision_index, state=state, frontier=frontier, unresolved=disagreement,
                )
                acquisitions = program.get("acquisitions")
                if type(acquisitions) is not list:
                    _fail("program acquisitions changed")
                start = len(program_ids)
                observed_ordinal = 0
                while len(candidates) > 1:
                    count = _active_query(candidates, frontier)
                    before = candidates
                    probability = target_v18.independently_replay_rank_two_probability_v18(count)
                    candidates = tuple(row for row in candidates if _predict(row, count) == probability)
                    if observed_ordinal >= len(acquisitions):
                        _fail("program acquisition missing")
                    _verify_acquisition(
                        acquisitions[observed_ordinal], arm=PROGRAM_ARM,
                        failure_id=failure["matched_repair_failure_id"],
                        ordinal=start + observed_ordinal, count=count,
                        before=len(before), after=len(candidates),
                    )
                    program_ids.append(acquisitions[observed_ordinal]["matched_repair_acquisition_id"])
                    observed_ordinal += 1
                if observed_ordinal != len(acquisitions):
                    _fail("extra program acquisition")
                program_failures += 1
                program_planner = _Planner(lambda count, row=candidates[0]: _predict(row, count))
            elif program.get("failure") is not None or program.get("acquisitions") != []:
                _fail("program arm did not persist its overlay")
            program_overlay = _verify_overlay(
                program.get("overlay"), arm=PROGRAM_ARM, acquisition_ids=program_ids,
                candidates=candidates, table=table,
            )
            program_overlay_id = program_overlay["matched_repair_overlay_id"]
            if program_planner is None:
                _fail("program planner absent")
            program_values = _verify_certificate(
                program.get("certificate"), arm=PROGRAM_ARM, episode=episode_index,
                decision=decision_index, state=state, overlay_id=program_overlay_id,
                planner=program_planner,
            )

            missing = tuple(count for count in frontier if count not in table)
            if missing:
                failure = _verify_failure(
                    table_arm.get("failure"), arm=TABLE_ARM, episode=episode_index,
                    decision=decision_index, state=state, frontier=frontier, unresolved=missing,
                )
                acquisitions = table_arm.get("acquisitions")
                if type(acquisitions) is not list or len(acquisitions) != len(missing):
                    _fail("no-prior acquisitions changed")
                start = len(table_ids)
                for offset, count in enumerate(missing):
                    _verify_acquisition(
                        acquisitions[offset], arm=TABLE_ARM,
                        failure_id=failure["matched_repair_failure_id"],
                        ordinal=start + offset, count=count, before=None, after=None,
                    )
                    table[count] = target_v18.independently_replay_rank_two_probability_v18(count)
                    table_ids.append(acquisitions[offset]["matched_repair_acquisition_id"])
                table_failures += 1
                table_planner = _Planner(lambda count: table[count])
            elif table_arm.get("failure") is not None or table_arm.get("acquisitions") != []:
                _fail("no-prior arm did not persist its table")
            table_overlay = _verify_overlay(
                table_arm.get("overlay"), arm=TABLE_ARM, acquisition_ids=table_ids,
                candidates=candidates, table=table,
            )
            table_overlay_id = table_overlay["matched_repair_overlay_id"]
            if table_planner is None:
                _fail("table planner absent")
            table_values = _verify_certificate(
                table_arm.get("certificate"), arm=TABLE_ARM, episode=episode_index,
                decision=decision_index, state=state, overlay_id=table_overlay_id,
                planner=table_planner,
            )
            independent_roots = target_v18.independently_replay_target_root_values_v18(state)
            expected_rows = [
                {"action": action, "expected_merge_score": score, "loss_probability_within_horizon": loss}
                for action, score, loss in independent_roots
            ]
            control = decision.get("cold_target_ground_control")
            if (
                type(control) is not dict
                or control.get("root_action_exact_values") != expected_rows
                or control.get("selected_action") != _best(program_values).action
                or control.get("lane") != "STANDALONE_EVALUATION_ONLY"
                or control.get("route_or_certificate_authority") is not False
                or _rows(program_values) != expected_rows
                or _rows(table_values) != expected_rows
                or _best(program_values).action != _best(table_values).action
                or decision.get("both_arms_exactly_match_cold_target_ground") is not True
                or decision.get("certificate_frozen_before_target_transition") is not True
            ):
                _fail("matched quality or evaluation lane changed")
            selected = _best(program_values).action
            outcome, tape = select_seeded_outcome_v1(
                target_v18.apply_independently_replayed_target_outcomes_v18(
                    state, Swipe2048Action(selected)
                ),
                seed=TARGET_SEEDS[episode_index], decision_index=decision_index,
            )
            if (
                decision.get("executed_action") != selected
                or decision.get("execution_tape_sha256") != tape
                or _state(decision.get("executed_next_state")) != outcome.next_state
                or decision.get("target_observation_used_for_either_model") is not False
            ):
                _fail("shared target transition changed")
            state = outcome.next_state
        if _state(episode.get("final_state")) != state or episode.get("all_matched_arm_values_and_actions_exact") is not True:
            _fail("episode closure changed")
    if (
        document.get("program_prior_final_overlay_id") != program_overlay_id
        or document.get("no_prior_final_overlay_id") != table_overlay_id
        or document.get("program_prior_failure_count") != program_failures
        or document.get("no_prior_failure_count") != table_failures
        or document.get("program_prior_selected_candidate_key") != candidates[0][0]
        or document.get("no_prior_final_context_count") != len(table)
    ):
        _fail("final model or failure aggregate changed")
    return len(program_ids), len(table_ids)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MatchedRepairIndependentVerificationV19:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("matched verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("matched verification bytes changed")
        payload = {key: value for key, value in document.items() if key != "matched_repair_verification_id"}
        if (
            document.get("matched_repair_verification_id") != self.verification_id
            or document.get("matched_repair_campaign_id") != self.campaign_id
            or content_id(CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN, payload)
            != self.verification_id
        ):
            _fail("matched verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("matched verification is not an object")
        return document


def verify_standard_2048_matched_repair_bytes_independently_v19(
    canonical_bytes: bytes,
) -> Standard2048MatchedRepairIndependentVerificationV19:
    observed = loads_canonical_json(canonical_bytes)
    root = _verify_id(
        observed, "matched_repair_campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN,
        "campaign",
    )
    if root["matched_repair_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("matched campaign identity changed")
    program_queries, table_queries = _replay(root)
    if (
        program_queries != 4
        or table_queries != 10
        or root.get("decision_count") != 12
        or root.get("program_prior_unique_ground_distinction_query_count") != 4
        or root.get("no_prior_unique_ground_distinction_query_count") != 10
        or root.get("strict_ground_distinction_query_reduction") != 6
        or root.get("program_prior_query_fraction_of_no_prior") != Fraction(2, 5)
        or root.get("strict_reduction_observed") is not True
        or root.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or root.get("total_operational_work_saving_claimed") is not False
        or root.get("official_execution_allowed") is not False
    ):
        _fail("matched aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_matched_repair_independent_verification.v19",
        "schema_version": SCHEMA_VERSION,
        "matched_repair_preregistration_id": PREREGISTRATION_ID,
        "matched_repair_campaign_id": EXPECTED_CAMPAIGN_ID,
        "target_kernel_id": TARGET_KERNEL_ID,
        "program_prior_four_queries_independently_replayed": True,
        "no_prior_ten_queries_independently_replayed": True,
        "strict_six_query_reduction_independently_verified": True,
        "both_12_decision_arms_independently_replanned": True,
        "all_12_shared_target_transitions_independently_replayed": True,
        "all_root_values_and_actions_match_independent_target_ground": True,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_broad_world_model_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN, payload
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen matched verification identity changed")
    return Standard2048MatchedRepairIndependentVerificationV19(
        _ISSUER,
        canonical_json_bytes({**payload, "matched_repair_verification_id": verification_id}),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048MatchedRepairIndependentVerifierV19Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048MatchedRepairIndependentVerificationV19",
    "verify_standard_2048_matched_repair_bytes_independently_v19",
)
