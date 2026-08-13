"""Producer-free exact semantic replay of the V0-169 long 2048 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_fresh_board_support_independent_verifier_v2
    as support_v2,
)
from acfqp import (
    construction_k7_standard_2048_long_episode_preregistration_v11 as pre,
)
from acfqp import (
    construction_k7_standard_2048_targeted_acquisition_independent_verifier_v7
    as targeted_v7,
)
from acfqp.domains.g2048 import inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    swipe_board_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROPOSED_CONTRACT_VERSION = pre.PROPOSED_CONTRACT_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = pre.PREREGISTRATION_ID
PREREGISTRATION_COMMIT = "c953c98"
DOMAINS = pre.FUTURE_DOMAINS
EPISODE_PROCESS_COUNT = 4
EXPECTED_CAMPAIGN_ID = (
    "158dfab7d25c70d46aabc98620d4bccd55ff5f2a39c354aa6ca918346e191fdd"
)
EXPECTED_CANONICAL_BYTE_COUNT = 431255
EXPECTED_CANONICAL_SHA256 = (
    "d23ae1212c073343ee63395c759bec7dfb08a65e8734f88c66ec137253238ee9"
)
EXPECTED_SOURCE_ARCHIVE_ID = (
    "397f7926abb0380c66504bb56fc86a142c73ea213225fed931f12dabbfe6fdbd"
)
EXPECTED_VALIDATION_ARCHIVE_ID = (
    "16687c2b90bc89d8b6c7a0c05e29bcc89ec77fd48b3fc84d321c2424ca4b30c4"
)


class ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error(
    ValueError
):
    """The V0-169 bytes differ from independent exact semantic replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _fraction(value: Any) -> Fraction:
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        _fail("rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _dynamics_identity_document(kind: str) -> dict[str, Any]:
    if kind == "STANDARD_UNIFORM":
        semantics = {
            "board_shape": [4, 4],
            "transition_order": "DETERMINISTIC_SWIPE_THEN_ONE_SPAWN",
            "spawn_position": "UNIFORM_OVER_ALL_POST_SWIPE_EMPTY_CELLS",
            "spawn_rank_support": [1, 2],
            "rank_law": "ONE_SHARED_BERNOULLI_PARAMETER",
            "registered_family_member": True,
        }
    elif kind == "OOD_FIRST_EMPTY_BIASED":
        semantics = {
            "board_shape": [4, 4],
            "transition_order": "DETERMINISTIC_SWIPE_THEN_ONE_SPAWN",
            "spawn_position": (
                "FIRST_SORTED_POST_SWIPE_EMPTY_CELL_WITH_PROBABILITY_ONE_HALF_"
                "REMAINDER_UNIFORM"
            ),
            "spawn_rank_support": [1, 2],
            "rank_law": "ONE_SHARED_BERNOULLI_PARAMETER",
            "registered_family_member": False,
        }
    else:
        _fail("unknown dynamics identity")
    payload = {
        "schema": "acfqp.standard_2048_long_dynamics_identity.v11",
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "semantics": semantics,
    }
    return {
        **payload,
        "dynamics_identity_id": content_id(
            DOMAINS["dynamics_identity"], payload
        ),
    }


@lru_cache(maxsize=1)
def _operator_binding() -> tuple[
    dict[str, Any],
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
]:
    source_archive = targeted_v7._archive("SOURCE")  # noqa: SLF001
    validation_archive = targeted_v7._archive("VALIDATION")  # noqa: SLF001
    if (
        source_archive["targeted_source_archive_id"]
        != EXPECTED_SOURCE_ARCHIVE_ID
        or validation_archive["targeted_validation_archive_id"]
        != EXPECTED_VALIDATION_ARCHIVE_ID
    ):
        _fail("independently regenerated raw archive identity changed")
    source_counts = (8,) * 16
    validation_counts = (4,) * 16
    _, rank_lower, rank_upper, raw = targeted_v7._snapshot(  # noqa: SLF001
        source_counts, validation_counts
    )
    if (
        raw["unique_offline_transition_observation_count"] != 192
        or not raw["heldout_support_and_intervals_passed"]
    ):
        _fail("independently regenerated meta-prior prefix changed")
    evidence = {
        "arm": "STRUCTURAL_META_PRIOR",
        "targeted_source_archive_id": EXPECTED_SOURCE_ARCHIVE_ID,
        "targeted_validation_archive_id": EXPECTED_VALIDATION_ARCHIVE_ID,
        "source_counts_by_cardinality": list(source_counts),
        "validation_counts_by_cardinality": list(validation_counts),
        "unique_offline_transition_observation_count": 192,
        "position_probability_semantics": (
            "REGISTERED_EXACT_UNIFORM_EXCHANGEABILITY_GIVEN_EMPTY_COUNT"
        ),
        "rank_two_probability_lower": _fdoc(rank_lower),
        "rank_two_probability_upper": _fdoc(rank_upper),
        "rank_two_source_empirical": raw["rank_two_source_empirical"],
        "rank_two_validation_empirical": raw[
            "rank_two_validation_empirical"
        ],
        "rank_two_radius": raw["rank_two_radius"],
        "support_prefix_validation_passed": True,
        "uniform_exchangeability_is_registered_prior": True,
        "uniform_exchangeability_proven_by_finite_samples": False,
        "conditional_on_registered_shared_law_family": True,
    }
    bounds = {
        count: tuple(
            (Fraction(1, count), Fraction(1, count)) for _ in range(count)
        )
        for count in range(1, 17)
    }
    payload = {
        "schema": "acfqp.standard_2048_long_operator_binding.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "v167_meta_route_campaign_id": pre.V167_META_ROUTE_CAMPAIGN_ID,
        "accepted_dynamics_identity": _dynamics_identity_document(
            "STANDARD_UNIFORM"
        ),
        "offline_evidence": evidence,
        "offline_observation_count": 192,
        "additional_model_acquisition_observation_count": 0,
        "binding_status": "EXACT_DYNAMICS_IDENTITY_BOUND",
        "support_rule": "ALL_SORTED_EMPTY_ORDINALS",
        "position_law": "REGISTERED_EXACT_UNIFORM_EXCHANGEABILITY",
        "rank_law": "POOLED_PREFIX_INTERVAL",
        "planning_horizon": pre.PLANNING_HORIZON,
        "successors_generated_lazily_inside_bellman_backup": True,
        "state_action_rows_serialized_or_persisted": False,
        "exact_rational_arithmetic": True,
        "target_observation_accessed_before_binding": False,
        "ground_transition_accessed_before_binding": False,
        "identity_match_is_not_a_route_certificate": True,
    }
    document = {
        **payload,
        "long_operator_binding_id": content_id(
            DOMAINS["operator_binding"], payload
        ),
    }
    return document, bounds, rank_lower, rank_upper


def _no_transfer_document() -> dict[str, Any]:
    accepted = _dynamics_identity_document("STANDARD_UNIFORM")
    candidate = _dynamics_identity_document("OOD_FIRST_EMPTY_BIASED")
    payload = {
        "schema": "acfqp.standard_2048_long_no_transfer.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "accepted_dynamics_identity_id": accepted["dynamics_identity_id"],
        "candidate_dynamics_identity": candidate,
        "identity_match": False,
        "status": "NO_TRANSFER_DYNAMICS_IDENTITY_MISMATCH",
        "operator_binding_created": False,
        "operator_accessed": False,
        "target_execution_performed": False,
        "target_observation_accessed": False,
        "ground_transition_accessed": False,
        "route_decision_created": False,
        "ood_generalization_claimed": False,
    }
    return {
        **payload,
        "long_no_transfer_id": content_id(DOMAINS["no_transfer"], payload),
    }


@dataclass(frozen=True, slots=True)
class _RowView:
    outcomes: tuple[support_v2.Standard2048SupportPartialOutcomeV2, ...]
    support_outcome_count: int
    unknown_support_mass_upper: Fraction
    row_id: str


@lru_cache(maxsize=None)
def _canonical_spawn_state(board: tuple[int, ...]) -> Swipe2048State:
    return canonicalize_state_v1(state_from_board_v1(board))[0]


@lru_cache(maxsize=None)
def _swipe(
    board: tuple[int, ...], action: Swipe2048Action
) -> tuple[tuple[int, ...], int, bool]:
    return swipe_board_v1(board, action)


class _LazyRows:
    def __init__(
        self,
        bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
        operator_id: str,
    ) -> None:
        self._bounds = bounds
        self._operator_id = operator_id
        self.invocation_count = 0
        self.support_outcome_evaluation_count = 0

    def get(self, key: tuple[tuple[int, ...], str, str]) -> _RowView:
        self.invocation_count += 1
        board, status_value, action_value = key
        state = Swipe2048State(board, Swipe2048Status(status_value))
        action = Swipe2048Action(action_value)
        moved, merge_score, changed = _swipe(state.board, action)
        if not changed:
            _fail("factored row received a nonchanging action")
        empty_cells = tuple(
            index for index, rank in enumerate(moved) if rank == 0
        )
        position_bounds = self._bounds.get(len(empty_cells))
        if position_bounds is None or len(position_bounds) != len(empty_cells):
            _fail("position interval cardinality changed")
        grouped: dict[tuple[Any, ...], int] = {}
        for ordinal in range(len(empty_cells)):
            for rank in (1, 2):
                spawned = list(moved)
                spawned[empty_cells[ordinal]] = rank
                representative = _canonical_spawn_state(tuple(spawned))
                lower, upper = position_bounds[ordinal]
                group_key = (
                    rank,
                    ordinal,
                    representative.board,
                    representative.status.value,
                    merge_score,
                    lower,
                    upper,
                )
                grouped[group_key] = grouped.get(group_key, 0) + 1
        outcomes = tuple(
            support_v2.Standard2048SupportPartialOutcomeV2(
                rank,
                ordinal,
                lower,
                upper,
                Swipe2048State(next_board, Swipe2048Status(next_status)),
                outcome_merge_score,
                count,
            )
            for (
                rank,
                ordinal,
                next_board,
                next_status,
                outcome_merge_score,
                lower,
                upper,
            ), count in sorted(grouped.items())
        )
        support_count = 2 * len(empty_cells)
        self.support_outcome_evaluation_count += support_count
        return _RowView(outcomes, support_count, Fraction(), self._operator_id)


def _action_row_keys(
    board: tuple[int, ...], status_value: str
) -> tuple[
    tuple[Swipe2048Action, tuple[tuple[int, ...], str, str]], ...
]:
    state = Swipe2048State(board, Swipe2048Status(status_value))
    return tuple(
        (action, support_v2._row_key(state, action))  # noqa: SLF001
        for action in legal_actions_v1(board)
    )


class _PersistentBellman:
    def __init__(self, rank_lower: Fraction, rank_upper: Fraction) -> None:
        self._rank_lower = rank_lower
        self._rank_upper = rank_upper
        self._cache: dict[
            tuple[tuple[int, ...], str, int], support_v2._RobustValueV1
        ] = {}
        self.cache_hits = 0

    def _state_value(
        self,
        rows: _LazyRows,
        board: tuple[int, ...],
        status_value: str,
        remaining: int,
    ) -> support_v2._RobustValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        key = (board, status_value, remaining)
        cached = self._cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        if remaining == 0 or state.status is Swipe2048Status.WON:
            value = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(), None
            )
            self._cache[key] = value
            return value
        if state.status is Swipe2048Status.LOST:
            value = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
            self._cache[key] = value
            return value
        best = None
        for action, row_key in _action_row_keys(board, status_value):
            candidate = self._action_value(rows, state, action, row_key, remaining)
            if support_v2._better_robust(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            best = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
        self._cache[key] = best
        return best

    def _action_value(
        self,
        rows: _LazyRows,
        representative: Swipe2048State,
        action: Swipe2048Action,
        row_key: tuple[tuple[int, ...], str, str],
        remaining: int,
    ) -> support_v2._RobustValueV1:
        row = rows.get(row_key)
        by_rank: dict[int, tuple[Fraction, Fraction, Fraction]] = {}
        for rank in (1, 2):
            rank_outcomes = tuple(
                outcome for outcome in row.outcomes if outcome.spawn_rank == rank
            )
            lower_values = []
            upper_values = []
            loss_values = []
            for outcome in rank_outcomes:
                child = self._state_value(
                    rows,
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                lower_values.append(outcome.merge_score + child.score_lower)
                upper_values.append(outcome.merge_score + child.score_upper)
                loss_values.append(child.loss_upper)
            lower_bounds = tuple(
                outcome.position_probability_lower for outcome in rank_outcomes
            )
            upper_bounds = tuple(
                outcome.position_probability_upper for outcome in rank_outcomes
            )
            by_rank[rank] = (
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(lower_values), lower_bounds, upper_bounds, maximize=False
                ),
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(upper_values), lower_bounds, upper_bounds, maximize=True
                ),
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(loss_values), lower_bounds, upper_bounds, maximize=True
                ),
            )
        lower_endpoints = tuple(
            (1 - probability) * by_rank[1][0]
            + probability * by_rank[2][0]
            for probability in (self._rank_lower, self._rank_upper)
        )
        upper_endpoints = tuple(
            (1 - probability) * by_rank[1][1]
            + probability * by_rank[2][1]
            for probability in (self._rank_lower, self._rank_upper)
        )
        loss_endpoints = tuple(
            (1 - probability) * by_rank[1][2]
            + probability * by_rank[2][2]
            for probability in (self._rank_lower, self._rank_upper)
        )
        known_upper = max(upper_endpoints)
        unknown_score_upper = support_v2._unknown_spawn_score_upper(  # noqa: SLF001
            representative,
            merge_score=row.outcomes[0].merge_score,
            remaining=remaining,
        )
        return support_v2._RobustValueV1(  # noqa: SLF001
            (1 - row.unknown_support_mass_upper) * min(lower_endpoints),
            known_upper
            + row.unknown_support_mass_upper
            * max(Fraction(), unknown_score_upper - known_upper),
            min(
                Fraction(1),
                row.unknown_support_mass_upper
                + (1 - row.unknown_support_mass_upper) * max(loss_endpoints),
            ),
            action,
        )

    def root_action_values(
        self, rows: _LazyRows, root: Swipe2048State
    ) -> tuple[support_v2._RobustValueV1, ...]:
        representative, transform = canonicalize_state_v1(root)
        output = []
        for action, row_key in _action_row_keys(
            representative.board, representative.status.value
        ):
            value = self._action_value(
                rows, representative, action, row_key, pre.PLANNING_HORIZON
            )
            lifted = transform_action_v1(action, inverse_d4(transform))
            output.append(
                support_v2._RobustValueV1(  # noqa: SLF001
                    value.score_lower,
                    value.score_upper,
                    value.loss_upper,
                    lifted,
                )
            )
        return tuple(
            sorted(
                output,
                key=lambda value: ACTION_ORDER.index(value.selected_action),
            )
        )


def _certificate_document(
    state: Swipe2048State,
    operator_id: str,
    rows: _LazyRows,
    bellman: _PersistentBellman,
) -> dict[str, Any]:
    before_rows = rows.invocation_count
    before_outcomes = rows.support_outcome_evaluation_count
    before_hits = bellman.cache_hits
    values = bellman.root_action_values(rows, state)
    eligible = tuple(
        candidate
        for candidate in values
        if all(
            candidate is challenger
            or candidate.score_lower > challenger.score_upper
            for challenger in values
        )
    )
    if len(eligible) > 1:
        _fail("strict dominance produced multiple actions")
    selected = None if not eligible else eligible[0].selected_action
    payload = {
        "schema": "acfqp.standard_2048_long_route_certificate.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "long_operator_binding_id": operator_id,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "root_action_intervals": [
            {
                "action": value.selected_action.value,
                "score_lower": _fdoc(value.score_lower),
                "score_upper": _fdoc(value.score_upper),
                "loss_probability_upper": _fdoc(value.loss_upper),
            }
            for value in values
        ],
        "certificate_rule": (
            "ONE_ROOT_ACTION_SCORE_LOWER_STRICTLY_EXCEEDS_EVERY_"
            "CHALLENGER_SCORE_UPPER"
        ),
        "selected_action": None if selected is None else selected.value,
        "status": (
            "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE"
            if selected is not None
            else "FAILED_STRICT_ROOT_INTERVAL_DOMINANCE"
        ),
        "virtual_row_invocation_count": rows.invocation_count - before_rows,
        "virtual_support_outcome_evaluation_count": (
            rows.support_outcome_evaluation_count - before_outcomes
        ),
        "closed_subproof_cache_hit_count": bellman.cache_hits - before_hits,
        "serialized_state_action_row_count": 0,
        "persistent_state_action_row_count": 0,
        "ground_transition_accessed": False,
        "cold_direct_accessed": False,
        "target_observation_accessed": False,
    }
    return {
        **payload,
        "long_route_certificate_id": content_id(DOMAINS["certificate"], payload),
    }


def _forced_exact(
    root: Swipe2048State, forced_action: Swipe2048Action
) -> dict[str, Any]:
    @lru_cache(maxsize=None)
    def solve(
        board: tuple[int, ...], status_value: str, remaining: int
    ) -> support_v2._ExactValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return support_v2._ExactValueV1(  # noqa: SLF001
                Fraction(), Fraction(), None
            )
        if state.status is Swipe2048Status.LOST:
            return support_v2._ExactValueV1(  # noqa: SLF001
                Fraction(), Fraction(1), None
            )
        best = None
        for action in legal_actions_v1(state.board):
            score = Fraction()
            loss = Fraction()
            for outcome in step_v1(state, action):
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = support_v2._ExactValueV1(  # noqa: SLF001
                score, loss, action
            )
            if support_v2._better_exact(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            return support_v2._ExactValueV1(  # noqa: SLF001
                Fraction(), Fraction(1), None
            )
        return best

    score = Fraction()
    loss = Fraction()
    for outcome in step_v1(root, forced_action):
        child = solve(
            outcome.next_state.board,
            outcome.next_state.status.value,
            pre.PLANNING_HORIZON - 1,
        )
        score += outcome.probability * (
            outcome.merge_score + child.expected_score
        )
        loss += outcome.probability * child.loss_probability
    return {
        "forced_action": forced_action.value,
        "expected_merge_score": _fdoc(score),
        "loss_probability_within_horizon": _fdoc(loss),
        "evaluation_lane_only": True,
    }


def _episode_task(
    task: tuple[
        int,
        tuple[int, ...],
        str,
        dict[str, Any],
        dict[int, tuple[tuple[Fraction, Fraction], ...]],
        Fraction,
        Fraction,
    ],
) -> dict[str, Any]:
    episode_index, board, seed, binding, bounds, rank_lower, rank_upper = task
    state = state_from_board_v1(board)
    initial_state = _state_document(state)
    rows = _LazyRows(bounds, binding["long_operator_binding_id"])
    bellman = _PersistentBellman(rank_lower, rank_upper)
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        certificate = _certificate_document(
            state, binding["long_operator_binding_id"], rows, bellman
        )
        exact = support_v2._direct_plan(  # noqa: SLF001
            state, pre.PLANNING_HORIZON
        )
        if certificate["selected_action"] is None:
            selected = Swipe2048Action(exact["selected_action"])
            route = "COLD_EXACT_DIRECT_GROUND_FALLBACK"
            matched_lane = "OPERATIONAL_FALLBACK"
        else:
            selected = Swipe2048Action(certificate["selected_action"])
            route = "ABSTRACT_CERTIFIED"
            matched_lane = "EVALUATION_ONLY"
        forced = None
        if selected.value != exact["selected_action"]:
            forced = _forced_exact(state, selected)
            equivalent = (
                _fraction(forced["expected_merge_score"])
                == _fraction(exact["expected_merge_score"])
                and _fraction(forced["loss_probability_within_horizon"])
                == _fraction(exact["loss_probability_within_horizon"])
            )
        else:
            equivalent = True
        outcome, tape_digest = select_seeded_outcome_v1(
            step_v1(state, selected),
            seed=seed,
            decision_index=decision_index,
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "state_before_decision": _state_document(state),
                "certificate": certificate,
                "route_decision": {
                    "route": route,
                    "selected_action": selected.value,
                    "certificate_id": certificate[
                        "long_route_certificate_id"
                    ],
                    "route_frozen_before_ground_access": True,
                    "fallback_only_after_certificate_failure": (
                        route != "COLD_EXACT_DIRECT_GROUND_FALLBACK"
                        or certificate["status"]
                        == "FAILED_STRICT_ROOT_INTERVAL_DOMINANCE"
                    ),
                },
                "matched_cold_direct": exact,
                "matched_direct_lane": matched_lane,
                "forced_selected_action_exact_evaluation": forced,
                "selected_action_exact_value_and_loss_equivalent": equivalent,
                "selected_action_label_identical": (
                    selected.value == exact["selected_action"]
                ),
                "executed_target_transition": {
                    "selected_action": selected.value,
                    "spawn_tape_digest": tape_digest,
                    "spawned_cell": outcome.spawned_cell,
                    "spawned_rank": outcome.spawned_rank,
                    "merge_score": outcome.merge_score,
                    "successor_state": _state_document(outcome.next_state),
                    "online_target_transition_observation_count": 1,
                    "not_used_before_route_freeze": True,
                },
            }
        )
        state = outcome.next_state
    abstract_count = sum(
        row["route_decision"]["route"] == "ABSTRACT_CERTIFIED"
        for row in decisions
    )
    terminal = state.status is not Swipe2048Status.ACTIVE
    maximum_rank = max(state.board)
    payload = {
        "schema": "acfqp.standard_2048_long_episode.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "long_operator_binding_id": binding["long_operator_binding_id"],
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "decisions": decisions,
        "decision_count": len(decisions),
        "maximum_registered_decision_count": pre.MAXIMUM_DECISIONS_PER_EPISODE,
        "closure_reason": (
            "TERMINAL_STATE" if terminal else "REGISTERED_DECISION_LIMIT"
        ),
        "abstract_route_count": abstract_count,
        "fallback_route_count": len(decisions) - abstract_count,
        "virtual_row_invocation_count": rows.invocation_count,
        "virtual_support_outcome_evaluation_count": (
            rows.support_outcome_evaluation_count
        ),
        "closed_subproof_cache_hit_count": bellman.cache_hits,
        "serialized_state_action_row_count": 0,
        "persistent_state_action_row_count": 0,
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": maximum_rank,
        "tile_2048_reached": maximum_rank >= 11,
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
    }
    return {
        **payload,
        "long_episode_id": content_id(DOMAINS["episode"], payload),
    }


@lru_cache(maxsize=1)
def _expected_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_long_episode_preregistration_v11()
    no_transfer = _no_transfer_document()
    binding, bounds, rank_lower, rank_upper = _operator_binding()
    tasks = [
        (episode_index, board, seed, binding, bounds, rank_lower, rank_upper)
        for episode_index, (board, seed) in enumerate(
            zip(
                pre.PREREGISTERED_INITIAL_BOARDS,
                pre.PREREGISTERED_EPISODE_SEEDS,
                strict=True,
            )
        )
    ]
    with ProcessPoolExecutor(max_workers=EPISODE_PROCESS_COUNT) as executor:
        episodes = list(executor.map(_episode_task, tasks, chunksize=1))
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    abstract_count = sum(
        row["route_decision"]["route"] == "ABSTRACT_CERTIFIED"
        for row in decisions
    )
    fallback_count = len(decisions) - abstract_count
    operational_rows = sum(
        row["matched_cold_direct"]["ground_state_action_row_count"]
        for row in decisions
        if row["matched_direct_lane"] == "OPERATIONAL_FALLBACK"
    )
    operational_outcomes = sum(
        row["matched_cold_direct"]["ground_outcome_count"]
        for row in decisions
        if row["matched_direct_lane"] == "OPERATIONAL_FALLBACK"
    )
    evaluation_rows = sum(
        row["matched_cold_direct"]["ground_state_action_row_count"]
        for row in decisions
        if row["matched_direct_lane"] == "EVALUATION_ONLY"
    )
    evaluation_outcomes = sum(
        row["matched_cold_direct"]["ground_outcome_count"]
        for row in decisions
        if row["matched_direct_lane"] == "EVALUATION_ONLY"
    )
    all_exact = all(
        row["selected_action_exact_value_and_loss_equivalent"]
        for row in decisions
    )
    all_certified = all(
        row["route_decision"]["route"] != "ABSTRACT_CERTIFIED"
        or row["certificate"]["status"]
        == "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE"
        for row in decisions
    )
    fallback_after_failure = all(
        row["route_decision"]["fallback_only_after_certificate_failure"]
        for row in decisions
    )
    required_passed = (
        len(episodes) == 4
        and no_transfer["status"]
        == "NO_TRANSFER_DYNAMICS_IDENTITY_MISMATCH"
        and binding["binding_status"] == "EXACT_DYNAMICS_IDENTITY_BOUND"
        and binding["offline_observation_count"] == 192
        and binding["additional_model_acquisition_observation_count"] == 0
        and all_exact
        and all_certified
        and fallback_after_failure
        and all(
            episode["serialized_state_action_row_count"] == 0
            for episode in episodes
        )
        and all(
            episode["persistent_state_action_row_count"] == 0
            for episode in episodes
        )
    )
    payload = {
        "schema": "acfqp.standard_2048_long_episode_campaign.v11",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "long_episode_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "ood_no_transfer": no_transfer,
        "accepted_operator_binding": binding,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "maximum_registered_decision_count": 4
        * pre.MAXIMUM_DECISIONS_PER_EPISODE,
        "offline_transition_observation_count": 192,
        "additional_model_acquisition_observation_count": 0,
        "abstract_route_count": abstract_count,
        "fallback_route_count": fallback_count,
        "factored_virtual_row_invocation_count": sum(
            episode["virtual_row_invocation_count"] for episode in episodes
        ),
        "factored_virtual_support_outcome_evaluation_count": sum(
            episode["virtual_support_outcome_evaluation_count"]
            for episode in episodes
        ),
        "closed_subproof_cache_hit_count": sum(
            episode["closed_subproof_cache_hit_count"] for episode in episodes
        ),
        "factored_operational_serialized_state_action_row_count": 0,
        "factored_operational_persistent_state_action_row_count": 0,
        "operational_fallback_ground_state_action_row_count": operational_rows,
        "operational_fallback_ground_outcome_count": operational_outcomes,
        "evaluation_cold_direct_ground_state_action_row_count": evaluation_rows,
        "evaluation_cold_direct_ground_outcome_count": evaluation_outcomes,
        "exact_value_and_loss_equivalent_decision_count": sum(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
        "exact_label_identical_decision_count": sum(
            row["selected_action_label_identical"] for row in decisions
        ),
        "all_selected_actions_exact_value_and_loss_equivalent": all_exact,
        "all_abstract_routes_have_strict_root_dominance_certificate": (
            all_certified
        ),
        "fallback_only_after_certificate_failure": fallback_after_failure,
        "maximum_final_board_tile_rank": max(
            episode["maximum_final_board_tile_rank"] for episode in episodes
        ),
        "tile_2048_reached": any(
            episode["tile_2048_reached"] for episode in episodes
        ),
        "all_required_preregistered_conditions_passed": required_passed,
        "registered_long_episode_outcome": (
            "POSITIVE_REGISTERED_CONDITIONAL_LONG_EPISODE_RESULT"
            if required_passed
            else "NEGATIVE_REGISTERED_CONDITIONAL_LONG_EPISODE_RESULT"
        ),
        "dynamics_identity_match_not_treated_as_certificate": True,
        "ood_target_execution_performed": False,
        "ood_generalization_claimed": False,
        "physical_iid_randomness_claimed": False,
        "full_standard_2048_game_completed": all(
            episode["closure_reason"] == "TERMINAL_STATE"
            for episode in episodes
        ),
        "broad_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "long_episode_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    if document["long_episode_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("independent campaign identity differs from registered result")
    return document


@lru_cache(maxsize=1)
def _expected_bytes() -> bytes:
    return canonical_json_bytes(_expected_document())


@dataclass(frozen=True, slots=True)
class Standard2048LongEpisodeIndependentVerificationV11:
    campaign_id: str

    @property
    def verification_id(self) -> str:
        payload = {
            "campaign_id": self.campaign_id,
            "episode_count": 4,
            "decision_count": 128,
            "exact_semantic_replay_passed": True,
            "producer_imported": False,
            "official_execution_allowed": False,
        }
        return content_id(DOMAINS["verification"], payload)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.standard_2048_long_episode_independent_verification.v11"
            ),
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "episode_count": 4,
            "decision_count": 128,
            "exact_semantic_replay_passed": True,
            "raw_observation_archive_regenerated": True,
            "factored_bellman_replayed": True,
            "cold_direct_controls_replayed": True,
            "seeded_target_tapes_replayed": True,
            "ood_no_transfer_replayed": True,
            "producer_imported": False,
            "full_standard_2048_game_verified": False,
            "broad_sample_efficiency_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_long_episode_campaign_bytes_independently_v11(
    raw: bytes,
) -> Standard2048LongEpisodeIndependentVerificationV11:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    try:
        document = loads_canonical_json(raw)
    except Phase3EIdentityError as error:
        raise ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error(
            "campaign is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("campaign is not canonical JSON")
    if raw != _expected_bytes():
        _fail("campaign differs from producer-free exact semantic replay")
    return Standard2048LongEpisodeIndependentVerificationV11(
        parse_content_id(document["long_episode_campaign_id"])
    )


__all__ = (
    "ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error",
    "Standard2048LongEpisodeIndependentVerificationV11",
    "verify_standard_2048_long_episode_campaign_bytes_independently_v11",
)
