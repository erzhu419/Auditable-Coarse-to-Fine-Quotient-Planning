"""Producer-free replay for the H2 affine standard-2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import math
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_adaptive_sample_tax_independent_verifier_v3
    as sample,
)
from acfqp import (
    construction_k7_standard_2048_fresh_board_support_independent_verifier_v2
    as base,
)
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    boards_from_rows_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    support_outcomes_v1,
    swipe_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_CERTIFICATE_V4_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_LONG_EPISODE_V4_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_META_PRIOR_V4_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_ROUTE_DECISION_V4_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_AFFINE_VERIFICATION_V4_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "4.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.158"
PROFILE_KEY = "construction_k7_standard_2048_affine_meta_prior_v4"
PLANNING_HORIZON = 2
DECISIONS_PER_EPISODE = 12
CONFIRMATORY_INITIAL_BOARDS = (
    boards_from_rows_v1(((1, 0, 0, 0), (0, 2, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))),
    boards_from_rows_v1(((0, 0, 0, 1), (0, 0, 0, 0), (0, 0, 0, 0), (1, 0, 0, 0))),
    boards_from_rows_v1(((0, 2, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0))),
    boards_from_rows_v1(((0, 0, 0, 0), (0, 0, 1, 0), (0, 2, 0, 0), (0, 0, 0, 0))),
)
CONFIRMATORY_EPISODE_SEEDS = tuple(
    f"standard-2048-v158-confirm-{suffix}-20260812" for suffix in "abcd"
)
DOMAINS = {
    "prior": CONSTRUCTION_K7_STANDARD_2048_AFFINE_META_PRIOR_V4_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_AFFINE_CERTIFICATE_V4_DOMAIN,
    "decision": CONSTRUCTION_K7_STANDARD_2048_AFFINE_ROUTE_DECISION_V4_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_AFFINE_LONG_EPISODE_V4_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN,
}
VERIFICATION_DOMAIN = CONSTRUCTION_K7_STANDARD_2048_AFFINE_VERIFICATION_V4_DOMAIN


class ConstructionK7Standard2048AffineMetaPriorIndependentVerifierV4Error(
    ValueError
):
    """The affine campaign differs from producer-free semantic replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AffineMetaPriorIndependentVerifierV4Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@dataclass(frozen=True, slots=True)
class _AffineValue:
    action: Swipe2048Action
    score_intercept: Fraction
    score_slope: Fraction
    loss_intercept: Fraction
    loss_slope: Fraction
    support_count: int
    child_evaluations: int
    zero_loss: bool

    def at(self, probability: Fraction) -> tuple[Fraction, Fraction]:
        return (
            self.score_intercept + self.score_slope * probability,
            self.loss_intercept + self.loss_slope * probability,
        )

    def document(self, lower: Fraction, upper: Fraction) -> dict[str, Any]:
        lower_score, lower_loss = self.at(lower)
        upper_score, upper_loss = self.at(upper)
        return {
            "action": self.action.value,
            "score_intercept": _fdoc(self.score_intercept),
            "score_rank_two_slope": _fdoc(self.score_slope),
            "loss_intercept": _fdoc(self.loss_intercept),
            "loss_rank_two_slope": _fdoc(self.loss_slope),
            "lower_endpoint_score": _fdoc(lower_score),
            "upper_endpoint_score": _fdoc(upper_score),
            "lower_endpoint_loss": _fdoc(lower_loss),
            "upper_endpoint_loss": _fdoc(upper_loss),
            "root_support_outcome_count": self.support_count,
            "child_action_evaluation_count": self.child_evaluations,
            "zero_loss_structural_witness": self.zero_loss,
        }


def _rank_evidence() -> tuple[Fraction, Fraction, dict[str, Any]]:
    _, lower, upper, _, passed, evidence = sample._checkpoint(8, 4)  # noqa: SLF001
    if not passed:
        _fail("rank evidence replay no longer validates")
    return lower, upper, {
        "source_checkpoint_per_cardinality": 8,
        "validation_checkpoint_per_cardinality": 4,
        "source_transition_observation_count": evidence[
            "source_transition_observation_count"
        ],
        "validation_transition_observation_count": evidence[
            "validation_transition_observation_count"
        ],
        "offline_transition_observation_count": evidence[
            "source_transition_observation_count"
        ]
        + evidence["validation_transition_observation_count"],
        "source_prefix_sha256": evidence["source_prefix_sha256"],
        "validation_prefix_sha256": evidence["validation_prefix_sha256"],
        "rank_two_source_empirical": evidence["rank_two_source_empirical"],
        "rank_two_validation_empirical": evidence[
            "rank_two_validation_empirical"
        ],
        "rank_two_lower": _fdoc(lower),
        "rank_two_upper": _fdoc(upper),
        "heldout_rank_interval_passed": True,
        "position_observations_ignored_by_affine_model": True,
    }


def _prior_document(evidence: dict[str, Any]) -> dict[str, Any]:
    taylor = sum(Fraction(16) ** term / math.factorial(term) for term in range(13))
    if not taylor > 20000:
        _fail("rank confidence proof changed")
    payload = {
        "schema": "acfqp.standard_2048_affine_structural_meta_prior.v4",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "prior_kind": "ZERO_TRAINING_SAMPLE_STRUCTURAL_META_PRIOR",
        "offline_prior_training_observation_count": 0,
        "registered_mechanics": [
            "WHOLE_BOARD_SWIPE",
            "ALL_EMPTY_CELLS_IN_SPAWN_SUPPORT",
            "UNIFORM_EXCHANGEABLE_POSITION_GIVEN_EMPTY_COUNT",
            "ONE_GLOBAL_RANK_TWO_PARAMETER_SHARED_ACROSS_ROWS",
            "H2_AFFINE_BELLMAN_REDUCTION",
        ],
        "rank_evidence": evidence,
        "rank_interval_conditional_confidence_lower": _fdoc(Fraction(9999, 10000)),
        "rank_confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_archive_does_not_establish_iid": True,
        "uniform_position_law_observation_derived": False,
        "uniform_position_law_is_registered_prior": True,
        "exact_rank_probability_accessed": False,
        "target_transition_accessed_by_prior": False,
        "certificate_or_route_authority": False,
        "open_ended_operator_invention_claimed": False,
    }
    return {**payload, "affine_meta_prior_id": content_id(DOMAINS["prior"], payload)}


def _child_value(
    state: Swipe2048State,
) -> tuple[Fraction, Fraction, int, bool]:
    if state.status is Swipe2048Status.WON:
        return Fraction(), Fraction(), 0, True
    if state.status is Swipe2048Status.LOST:
        return Fraction(), Fraction(1), 0, False
    actions = legal_actions_v1(state.board)
    scored = tuple(
        (
            Fraction(swipe_board_v1(state.board, action)[1]),
            all(
                outcome.next_state.status is not Swipe2048Status.LOST
                for outcome in support_outcomes_v1(state, action)
            ),
        )
        for action in actions
    )
    best = max(score for score, _ in scored)
    zero_loss = any(score == best and safe for score, safe in scored)
    return best, Fraction() if zero_loss else Fraction(1), len(actions), zero_loss


def _action_value(state: Swipe2048State, action: Swipe2048Action) -> _AffineValue:
    support = support_outcomes_v1(state, action)
    by_rank: dict[int, tuple[Fraction, Fraction]] = {}
    evaluations = 0
    safe = True
    for rank in (1, 2):
        scores: list[Fraction] = []
        losses: list[Fraction] = []
        rank_rows = tuple(row for row in support if row.spawned_rank == rank)
        for row in rank_rows:
            score, loss, count, zero_loss = _child_value(row.next_state)
            scores.append(score)
            losses.append(loss)
            evaluations += count
            safe &= zero_loss
        by_rank[rank] = (
            sum(scores, Fraction()) / len(scores),
            sum(losses, Fraction()) / len(losses),
        )
    return _AffineValue(
        action,
        Fraction(support[0].merge_score) + by_rank[1][0],
        by_rank[2][0] - by_rank[1][0],
        by_rank[1][1],
        by_rank[2][1] - by_rank[1][1],
        len(support),
        evaluations,
        safe,
    )


def _dominates(candidate: _AffineValue, challenger: _AffineValue, p: Fraction) -> bool:
    score, loss = candidate.at(p)
    other_score, other_loss = challenger.at(p)
    return score > other_score or (score == other_score and loss <= other_loss)


def _certificate(
    state: Swipe2048State,
    lower: Fraction,
    upper: Fraction,
    prior_id: str,
) -> dict[str, Any]:
    values = tuple(_action_value(state, action) for action in legal_actions_v1(state.board))
    all_safe = all(value.zero_loss for value in values)
    eligible = (
        tuple(
            candidate.action
            for candidate in values
            if all(
                candidate.action is challenger.action
                or (
                    _dominates(candidate, challenger, lower)
                    and _dominates(candidate, challenger, upper)
                )
                for challenger in values
            )
        )
        if all_safe
        else ()
    )
    selected = next((action for action in ACTION_ORDER if action in eligible), None)
    payload = {
        "schema": "acfqp.standard_2048_h2_affine_endpoint_certificate.v4",
        "schema_version": SCHEMA_VERSION,
        "affine_meta_prior_id": prior_id,
        "root_state": _state_document(state),
        "planning_horizon": PLANNING_HORIZON,
        "rank_two_lower": _fdoc(lower),
        "rank_two_upper": _fdoc(upper),
        "action_affine_values": [value.document(lower, upper) for value in values],
        "globally_optimal_action_set": [action.value for action in eligible],
        "selected_action": None if selected is None else selected.value,
        "status": (
            "CERTIFIED_AFFINE_ENDPOINT_OPTIMAL"
            if selected is not None
            else "FAILED_AFFINE_ENDPOINT_DOMINANCE"
        ),
        "endpoint_dominance_sufficient_for_affine_interval": True,
        "all_actions_zero_loss_structural_witness": all_safe,
        "exact_rank_probability_accessed": False,
        "ground_transition_kernel_accessed": False,
        "cold_direct_accessed": False,
        "root_support_outcome_count": sum(value.support_count for value in values),
        "child_action_evaluation_count": sum(
            value.child_evaluations for value in values
        ),
    }
    return {**payload, "affine_certificate_id": content_id(DOMAINS["certificate"], payload)}


def _forced_value(
    root: Swipe2048State, action: Swipe2048Action
) -> tuple[Fraction, Fraction]:
    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status: str, remaining: int) -> base._ExactValueV1:
        state = Swipe2048State(board, Swipe2048Status(status))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return base._ExactValueV1(Fraction(), Fraction(), None)  # noqa: SLF001
        if state.status is Swipe2048Status.LOST:
            return base._ExactValueV1(Fraction(), Fraction(1), None)  # noqa: SLF001
        best = None
        for child_action in legal_actions_v1(state.board):
            score = Fraction()
            loss = Fraction()
            for outcome in step_v1(state, child_action):
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = base._ExactValueV1(score, loss, child_action)  # noqa: SLF001
            if base._better_exact(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            return base._ExactValueV1(Fraction(), Fraction(1), None)  # noqa: SLF001
        return best

    score = Fraction()
    loss = Fraction()
    for outcome in step_v1(root, action):
        child = solve(
            outcome.next_state.board,
            outcome.next_state.status.value,
            PLANNING_HORIZON - 1,
        )
        score += outcome.probability * (outcome.merge_score + child.expected_score)
        loss += outcome.probability * child.loss_probability
    return score, loss


def _route(
    certificate: dict[str, Any],
    fallback: dict[str, Any] | None,
    episode_index: int,
    decision_index: int,
) -> dict[str, Any]:
    certified = certificate["status"] == "CERTIFIED_AFFINE_ENDPOINT_OPTIMAL"
    if certified != (fallback is None):
        _fail("fallback replay disagrees with certificate")
    payload = {
        "schema": "acfqp.standard_2048_affine_route_decision.v4",
        "schema_version": SCHEMA_VERSION,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "affine_certificate_id": certificate["affine_certificate_id"],
        "route": "ABSTRACT_AFFINE" if certified else "COLD_GROUND_FALLBACK",
        "selected_action": (
            certificate["selected_action"] if certified else fallback["selected_action"]
        ),
        "fallback_plan_id": None if fallback is None else fallback["matched_direct_plan_id"],
        "fallback_triggered_only_by_certificate_failure": fallback is not None,
        "matched_evaluation_used_for_route_choice": False,
    }
    return {**payload, "route_decision_id": content_id(DOMAINS["decision"], payload)}


def _episode(
    index: int,
    board: tuple[int, ...],
    seed: str,
    lower: Fraction,
    upper: Fraction,
    prior_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    state = state_from_board_v1(board)
    initial = _state_document(state)
    decisions: list[dict[str, Any]] = []
    totals = {
        "abstract": 0,
        "fallback": 0,
        "fallback_rows": 0,
        "fallback_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
        "support_outcomes": 0,
        "child_evaluations": 0,
    }
    for decision_index in range(DECISIONS_PER_EPISODE):
        certificate = _certificate(state, lower, upper, prior_id)
        fallback = None
        if certificate["selected_action"] is None:
            fallback = base._direct_plan(state, PLANNING_HORIZON)  # noqa: SLF001
            totals["fallback"] += 1
            totals["fallback_rows"] += fallback["ground_state_action_row_count"]
            totals["fallback_outcomes"] += fallback["ground_outcome_count"]
        else:
            totals["abstract"] += 1
        route = _route(certificate, fallback, index, decision_index)
        evaluation = base._direct_plan(state, PLANNING_HORIZON)  # noqa: SLF001
        totals["evaluation_rows"] += evaluation["ground_state_action_row_count"]
        totals["evaluation_outcomes"] += evaluation["ground_outcome_count"]
        totals["support_outcomes"] += certificate["root_support_outcome_count"]
        totals["child_evaluations"] += certificate["child_action_evaluation_count"]
        action = Swipe2048Action(route["selected_action"])
        forced_score, forced_loss = _forced_value(state, action)
        if not (
            forced_score
            == base._fraction_from_document(evaluation["expected_merge_score"])  # noqa: SLF001
            and forced_loss
            == base._fraction_from_document(  # noqa: SLF001
                evaluation["loss_probability_within_horizon"]
            )
        ):
            _fail("confirmatory action replay is not exact-value equivalent")
        outcome, digest = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=decision_index
        )
        decisions.append(
            {
                "decision_index": decision_index,
                "predecision_state": _state_document(state),
                "affine_certificate": certificate,
                "route_decision": route,
                "matched_cold_direct": evaluation,
                "selected_action_exact_value_and_loss_equivalent": True,
                "matched_action_label_identical": (
                    route["selected_action"] == evaluation["selected_action"]
                ),
                "execution_tape_sha256": digest,
                "executed_next_state": _state_document(outcome.next_state),
                "online_target_transition_observation_count": 1,
            }
        )
        state = outcome.next_state
    payload = {
        "schema": "acfqp.standard_2048_affine_long_episode.v4",
        "schema_version": SCHEMA_VERSION,
        "episode_index": index,
        "initial_state": initial,
        "execution_seed": seed,
        "planning_horizon": PLANNING_HORIZON,
        "decision_count": len(decisions),
        "decisions": decisions,
        "final_state": _state_document(state),
        "abstract_route_count": totals["abstract"],
        "fallback_route_count": totals["fallback"],
        "all_selected_actions_exact_value_and_loss_equivalent": True,
        "all_matched_action_labels_identical": all(
            row["matched_action_label_identical"] for row in decisions
        ),
    }
    return {**payload, "affine_long_episode_id": content_id(DOMAINS["episode"], payload)}, totals


@lru_cache(maxsize=1)
def _expected_campaign_bytes() -> bytes:
    lower, upper, evidence = _rank_evidence()
    prior = _prior_document(evidence)
    episodes = []
    aggregate = {
        "abstract": 0,
        "fallback": 0,
        "fallback_rows": 0,
        "fallback_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
        "support_outcomes": 0,
        "child_evaluations": 0,
    }
    for index, (board, seed) in enumerate(
        zip(CONFIRMATORY_INITIAL_BOARDS, CONFIRMATORY_EPISODE_SEEDS, strict=True)
    ):
        episode, totals = _episode(
            index, board, seed, lower, upper, prior["affine_meta_prior_id"]
        )
        episodes.append(episode)
        for key in aggregate:
            aggregate[key] += totals[key]
    if not (
        aggregate["abstract"] == 47
        and aggregate["fallback"] == 1
        and all(row["all_selected_actions_exact_value_and_loss_equivalent"] for row in episodes)
        and all(row["all_matched_action_labels_identical"] for row in episodes)
    ):
        _fail("fresh confirmatory replay changed")
    payload = {
        "schema": "acfqp.standard_2048_affine_meta_prior_campaign.v4",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "affine_meta_prior": prior,
        "confirmatory_initial_boards_frozen_before_execution": [
            list(board) for board in CONFIRMATORY_INITIAL_BOARDS
        ],
        "confirmatory_episode_seeds_frozen_before_execution": list(
            CONFIRMATORY_EPISODE_SEEDS
        ),
        "episodes": episodes,
        "episode_count": 4,
        "decision_count": 48,
        "offline_transition_observation_count": evidence[
            "offline_transition_observation_count"
        ],
        "online_target_transition_observation_count": 48,
        "additional_model_acquisition_observation_count_during_episodes": 0,
        "abstract_route_count": aggregate["abstract"],
        "cold_ground_fallback_route_count": aggregate["fallback"],
        "matched_cold_direct_operational_route_count_control": 48,
        "ground_fallback_route_count_saving_vs_direct": 48
        - aggregate["fallback"],
        "abstract_route_fraction": _fdoc(Fraction(aggregate["abstract"], 48)),
        "operational_fallback_ground_state_action_row_count": aggregate[
            "fallback_rows"
        ],
        "operational_fallback_ground_outcome_count": aggregate[
            "fallback_outcomes"
        ],
        "operational_affine_support_outcome_count": aggregate["support_outcomes"],
        "operational_affine_child_action_evaluation_count": aggregate[
            "child_evaluations"
        ],
        "evaluation_cold_direct_ground_state_action_row_count": aggregate[
            "evaluation_rows"
        ],
        "evaluation_cold_direct_ground_outcome_count": aggregate[
            "evaluation_outcomes"
        ],
        "all_48_selected_actions_exact_value_and_loss_equivalent": True,
        "all_48_action_labels_identical_to_cold_direct": True,
        "fallback_triggered_only_by_certificate_failure": True,
        "matched_direct_has_route_authority": False,
        "meta_prior_reduces_long_episode_ground_fallback_tax": True,
        "total_operational_work_saving_claimed": False,
        "offline_sample_tax_below_v3_192_claimed": False,
        "uniform_position_prior_learned_from_observations": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "externally_preregistered_before_algorithm_design": False,
        "fresh_fixture_is_formal_confirmatory_gate": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "sample_efficiency_gate_status": "FRESH_REGISTERED_INITIAL_BOARD_PREFIX_ONLY",
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {**payload, "affine_campaign_id": content_id(DOMAINS["campaign"], payload)}
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class Standard2048AffineMetaPriorIndependentVerificationV4:
    campaign_id: str
    prior_id: str
    decision_count: int
    abstract_route_count: int
    fallback_route_count: int

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "prior_id": self.prior_id,
                "decision_count": self.decision_count,
                "abstract_route_count": self.abstract_route_count,
                "fallback_route_count": self.fallback_route_count,
                "raw_rank_prefix_replayed": True,
                "affine_endpoint_certificates_replayed": True,
                "fallback_and_cold_direct_replayed": True,
                "broad_sample_efficiency_verified": False,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_affine_independent_verification.v4",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "prior_id": self.prior_id,
            "decision_count": self.decision_count,
            "abstract_route_count": self.abstract_route_count,
            "fallback_route_count": self.fallback_route_count,
            "raw_rank_prefix_replayed": True,
            "affine_endpoint_certificates_replayed": True,
            "fallback_and_cold_direct_replayed": True,
            "broad_sample_efficiency_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_affine_meta_prior_campaign_bytes_independently_v4(
    raw: bytes,
) -> Standard2048AffineMetaPriorIndependentVerificationV4:
    if type(raw) is not bytes:
        _fail("independent affine verifier requires exact bytes")
    observed = loads_canonical_json(raw)
    if type(observed) is not dict or canonical_json_bytes(observed) != raw:
        _fail("affine campaign bytes are not canonical JSON")
    if raw != _expected_campaign_bytes():
        _fail("affine campaign differs from producer-free replay")
    return Standard2048AffineMetaPriorIndependentVerificationV4(
        parse_content_id(observed["affine_campaign_id"]),
        parse_content_id(observed["affine_meta_prior"]["affine_meta_prior_id"]),
        observed["decision_count"],
        observed["abstract_route_count"],
        observed["cold_ground_fallback_route_count"],
    )


__all__ = (
    "ConstructionK7Standard2048AffineMetaPriorIndependentVerifierV4Error",
    "Standard2048AffineMetaPriorIndependentVerificationV4",
    "verify_standard_2048_affine_meta_prior_campaign_bytes_independently_v4",
)
