"""H2 affine 2048 world model with certificate-triggered ground fallback.

The registered structural prior says that, conditional on an empty-cell count,
spawn position is exchangeable and every empty cell is in support.  Only the
global rank-two probability is learned, from the first V3 source/validation
prefix.  At H=2 each root action then has exact affine score and loss functions
of that one probability.  Endpoint dominance is a sound certificate over the
whole registered interval; failure invokes a cold exact ground planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import math
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_sample_tax_v3 as sample
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as world
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
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "4.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.158"
PROFILE_KEY = "construction_k7_standard_2048_affine_meta_prior_v4"
PLANNING_HORIZON = 2
DECISIONS_PER_EPISODE = 12
SOURCE_CHECKPOINT_PER_CARDINALITY = 8
VALIDATION_CHECKPOINT_PER_CARDINALITY = 4

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
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("affine meta-prior domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("affine meta-prior domains are not registered")


class ConstructionK7Standard2048AffineMetaPriorV4Error(ValueError):
    """A structural prior, affine proof, route decision, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AffineMetaPriorV4Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@dataclass(frozen=True, slots=True)
class _AffineActionValueV4:
    action: Swipe2048Action
    score_intercept: Fraction
    score_rank_two_slope: Fraction
    loss_intercept: Fraction
    loss_rank_two_slope: Fraction
    root_support_outcome_count: int
    child_action_evaluation_count: int
    zero_loss_structural_witness: bool

    def at(self, rank_two_probability: Fraction) -> tuple[Fraction, Fraction]:
        return (
            self.score_intercept
            + self.score_rank_two_slope * rank_two_probability,
            self.loss_intercept
            + self.loss_rank_two_slope * rank_two_probability,
        )

    def to_document(self, lower: Fraction, upper: Fraction) -> dict[str, Any]:
        lower_score, lower_loss = self.at(lower)
        upper_score, upper_loss = self.at(upper)
        return {
            "action": self.action.value,
            "score_intercept": _fdoc(self.score_intercept),
            "score_rank_two_slope": _fdoc(self.score_rank_two_slope),
            "loss_intercept": _fdoc(self.loss_intercept),
            "loss_rank_two_slope": _fdoc(self.loss_rank_two_slope),
            "lower_endpoint_score": _fdoc(lower_score),
            "upper_endpoint_score": _fdoc(upper_score),
            "lower_endpoint_loss": _fdoc(lower_loss),
            "upper_endpoint_loss": _fdoc(upper_loss),
            "root_support_outcome_count": self.root_support_outcome_count,
            "child_action_evaluation_count": self.child_action_evaluation_count,
            "zero_loss_structural_witness": self.zero_loss_structural_witness,
        }


def _rank_evidence() -> tuple[Fraction, Fraction, dict[str, Any]]:
    _, lower, upper, _, passed, evidence = sample._checkpoint_interval(  # noqa: SLF001
        SOURCE_CHECKPOINT_PER_CARDINALITY,
        VALIDATION_CHECKPOINT_PER_CARDINALITY,
    )
    if not passed:
        _fail("registered rank evidence no longer validates")
    return lower, upper, {
        "source_checkpoint_per_cardinality": SOURCE_CHECKPOINT_PER_CARDINALITY,
        "validation_checkpoint_per_cardinality": VALIDATION_CHECKPOINT_PER_CARDINALITY,
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


def _prior_document(rank_evidence: dict[str, Any]) -> dict[str, Any]:
    taylor = sum(Fraction(16) ** term / math.factorial(term) for term in range(13))
    if not taylor > 20000:
        _fail("affine rank confidence arithmetic changed")
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
        "rank_evidence": rank_evidence,
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


def _best_immediate_merge_and_loss(
    state: Swipe2048State,
) -> tuple[Fraction, Fraction, int, bool]:
    if state.status is Swipe2048Status.WON:
        return Fraction(), Fraction(), 0, True
    if state.status is Swipe2048Status.LOST:
        return Fraction(), Fraction(1), 0, False
    actions = legal_actions_v1(state.board)
    if not actions:
        _fail("active child has no legal action")
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
    best_score = max(score for score, _ in scored)
    zero_loss_witness = any(
        score == best_score and support_is_zero_loss
        for score, support_is_zero_loss in scored
    )
    return (
        best_score,
        Fraction() if zero_loss_witness else Fraction(1),
        len(actions),
        zero_loss_witness,
    )


def _affine_action_value(
    state: Swipe2048State, action: Swipe2048Action
) -> _AffineActionValueV4:
    support = support_outcomes_v1(state, action)
    if not support:
        _fail("registered support mechanics returned an empty row")
    root_merge = support[0].merge_score
    by_rank: dict[int, tuple[Fraction, Fraction]] = {}
    child_action_evaluations = 0
    zero_loss_structural_witness = True
    for rank in (1, 2):
        rank_rows = tuple(row for row in support if row.spawned_rank == rank)
        if not rank_rows:
            _fail("registered rank support disappeared")
        scores: list[Fraction] = []
        losses: list[Fraction] = []
        for row in rank_rows:
            score, loss, evaluations, zero_loss = _best_immediate_merge_and_loss(
                row.next_state
            )
            scores.append(score)
            losses.append(loss)
            child_action_evaluations += evaluations
            zero_loss_structural_witness &= zero_loss
        by_rank[rank] = (
            sum(scores, Fraction()) / len(scores),
            sum(losses, Fraction()) / len(losses),
        )
    return _AffineActionValueV4(
        action,
        Fraction(root_merge) + by_rank[1][0],
        by_rank[2][0] - by_rank[1][0],
        by_rank[1][1],
        by_rank[2][1] - by_rank[1][1],
        len(support),
        child_action_evaluations,
        zero_loss_structural_witness,
    )


def _dominates_at(
    candidate: _AffineActionValueV4,
    challenger: _AffineActionValueV4,
    probability: Fraction,
) -> bool:
    candidate_score, candidate_loss = candidate.at(probability)
    challenger_score, challenger_loss = challenger.at(probability)
    return candidate_score > challenger_score or (
        candidate_score == challenger_score and candidate_loss <= challenger_loss
    )


def _certificate_document(
    *,
    state: Swipe2048State,
    lower: Fraction,
    upper: Fraction,
    prior_id: str,
) -> dict[str, Any]:
    values = tuple(_affine_action_value(state, action) for action in legal_actions_v1(state.board))
    all_actions_zero_loss = all(
        value.zero_loss_structural_witness for value in values
    )
    eligible = (
        tuple(
            candidate.action
            for candidate in values
            if all(
                candidate.action is challenger.action
                or (
                    _dominates_at(candidate, challenger, lower)
                    and _dominates_at(candidate, challenger, upper)
                )
                for challenger in values
            )
        )
        if all_actions_zero_loss
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
        "action_affine_values": [value.to_document(lower, upper) for value in values],
        "globally_optimal_action_set": [action.value for action in eligible],
        "selected_action": None if selected is None else selected.value,
        "status": (
            "CERTIFIED_AFFINE_ENDPOINT_OPTIMAL"
            if selected is not None
            else "FAILED_AFFINE_ENDPOINT_DOMINANCE"
        ),
        "endpoint_dominance_sufficient_for_affine_interval": True,
        "all_actions_zero_loss_structural_witness": all_actions_zero_loss,
        "exact_rank_probability_accessed": False,
        "ground_transition_kernel_accessed": False,
        "cold_direct_accessed": False,
        "root_support_outcome_count": sum(
            value.root_support_outcome_count for value in values
        ),
        "child_action_evaluation_count": sum(
            value.child_action_evaluation_count for value in values
        ),
    }
    return {**payload, "affine_certificate_id": content_id(DOMAINS["certificate"], payload)}


def _route_decision(
    *,
    certificate: dict[str, Any],
    fallback: dict[str, Any] | None,
    episode_index: int,
    decision_index: int,
) -> dict[str, Any]:
    certified = certificate["status"] == "CERTIFIED_AFFINE_ENDPOINT_OPTIMAL"
    if certified != (fallback is None):
        _fail("fallback presence disagrees with the affine certificate")
    selected_action = (
        certificate["selected_action"] if certified else fallback["selected_action"]
    )
    payload = {
        "schema": "acfqp.standard_2048_affine_route_decision.v4",
        "schema_version": SCHEMA_VERSION,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "affine_certificate_id": certificate["affine_certificate_id"],
        "route": "ABSTRACT_AFFINE" if certified else "COLD_GROUND_FALLBACK",
        "selected_action": selected_action,
        "fallback_plan_id": None if fallback is None else fallback["matched_direct_plan_id"],
        "fallback_triggered_only_by_certificate_failure": fallback is not None,
        "matched_evaluation_used_for_route_choice": False,
    }
    return {**payload, "route_decision_id": content_id(DOMAINS["decision"], payload)}


def _run_episode(
    *,
    episode_index: int,
    initial_board: tuple[int, ...],
    seed: str,
    lower: Fraction,
    upper: Fraction,
    prior_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    state = state_from_board_v1(initial_board)
    initial_state = _state_document(state)
    decisions: list[dict[str, Any]] = []
    totals = {
        "abstract": 0,
        "fallback": 0,
        "operational_fallback_rows": 0,
        "operational_fallback_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
        "support_outcomes": 0,
        "child_action_evaluations": 0,
    }
    for decision_index in range(DECISIONS_PER_EPISODE):
        certificate = _certificate_document(
            state=state, lower=lower, upper=upper, prior_id=prior_id
        )
        fallback = None
        if certificate["selected_action"] is None:
            fallback = world._direct_plan(state, PLANNING_HORIZON)  # noqa: SLF001
            totals["fallback"] += 1
            totals["operational_fallback_rows"] += fallback[
                "ground_state_action_row_count"
            ]
            totals["operational_fallback_outcomes"] += fallback[
                "ground_outcome_count"
            ]
        else:
            totals["abstract"] += 1
        route = _route_decision(
            certificate=certificate,
            fallback=fallback,
            episode_index=episode_index,
            decision_index=decision_index,
        )
        evaluation = world._direct_plan(state, PLANNING_HORIZON)  # noqa: SLF001
        totals["evaluation_rows"] += evaluation["ground_state_action_row_count"]
        totals["evaluation_outcomes"] += evaluation["ground_outcome_count"]
        totals["support_outcomes"] += certificate["root_support_outcome_count"]
        totals["child_action_evaluations"] += certificate[
            "child_action_evaluation_count"
        ]
        selected_action = Swipe2048Action(route["selected_action"])
        forced = world._direct_plan_forced_action(  # noqa: SLF001
            state, PLANNING_HORIZON, selected_action
        )
        exact_equivalent = (
            world._fraction_from_document(forced["expected_merge_score"])  # noqa: SLF001
            == world._fraction_from_document(evaluation["expected_merge_score"])  # noqa: SLF001
            and world._fraction_from_document(  # noqa: SLF001
                forced["loss_probability_within_horizon"]
            )
            == world._fraction_from_document(  # noqa: SLF001
                evaluation["loss_probability_within_horizon"]
            )
        )
        if not exact_equivalent:
            _fail("confirmatory affine route differs from cold exact value or loss")
        outcomes = step_v1(state, selected_action)
        selected, tape_digest = select_seeded_outcome_v1(
            outcomes, seed=seed, decision_index=decision_index
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
                "execution_tape_sha256": tape_digest,
                "executed_next_state": _state_document(selected.next_state),
                "online_target_transition_observation_count": 1,
            }
        )
        state = selected.next_state
    payload = {
        "schema": "acfqp.standard_2048_affine_long_episode.v4",
        "schema_version": SCHEMA_VERSION,
        "episode_index": episode_index,
        "initial_state": initial_state,
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
    return (
        {**payload, "affine_long_episode_id": content_id(DOMAINS["episode"], payload)},
        totals,
    )


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    lower, upper, evidence = _rank_evidence()
    prior = _prior_document(evidence)
    episodes: list[dict[str, Any]] = []
    aggregate = {
        "abstract": 0,
        "fallback": 0,
        "operational_fallback_rows": 0,
        "operational_fallback_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
        "support_outcomes": 0,
        "child_action_evaluations": 0,
    }
    for index, (board, seed) in enumerate(
        zip(CONFIRMATORY_INITIAL_BOARDS, CONFIRMATORY_EPISODE_SEEDS, strict=True)
    ):
        episode, totals = _run_episode(
            episode_index=index,
            initial_board=board,
            seed=seed,
            lower=lower,
            upper=upper,
            prior_id=prior["affine_meta_prior_id"],
        )
        episodes.append(episode)
        for key in aggregate:
            aggregate[key] += totals[key]
    total_decisions = len(episodes) * DECISIONS_PER_EPISODE
    if not (
        total_decisions == 48
        and aggregate["abstract"] == 47
        and aggregate["fallback"] == 1
        and all(row["all_selected_actions_exact_value_and_loss_equivalent"] for row in episodes)
        and all(row["all_matched_action_labels_identical"] for row in episodes)
    ):
        _fail("fresh confirmatory affine campaign changed")
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
        "episode_count": len(episodes),
        "decision_count": total_decisions,
        "offline_transition_observation_count": evidence[
            "offline_transition_observation_count"
        ],
        "online_target_transition_observation_count": total_decisions,
        "additional_model_acquisition_observation_count_during_episodes": 0,
        "abstract_route_count": aggregate["abstract"],
        "cold_ground_fallback_route_count": aggregate["fallback"],
        "matched_cold_direct_operational_route_count_control": total_decisions,
        "ground_fallback_route_count_saving_vs_direct": (
            total_decisions - aggregate["fallback"]
        ),
        "abstract_route_fraction": _fdoc(
            Fraction(aggregate["abstract"], total_decisions)
        ),
        "operational_fallback_ground_state_action_row_count": aggregate[
            "operational_fallback_rows"
        ],
        "operational_fallback_ground_outcome_count": aggregate[
            "operational_fallback_outcomes"
        ],
        "operational_affine_support_outcome_count": aggregate["support_outcomes"],
        "operational_affine_child_action_evaluation_count": aggregate[
            "child_action_evaluations"
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
    return {**payload, "affine_campaign_id": content_id(DOMAINS["campaign"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AffineMetaPriorCampaignV4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("affine campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("affine_campaign_id") != self.campaign_id
            or content_id(
                DOMAINS["campaign"],
                {
                    key: value
                    for key, value in document.items()
                    if key != "affine_campaign_id"
                },
            )
            != self.campaign_id
        ):
            _fail("affine campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("affine campaign root is not an object")
        return document


def run_standard_2048_affine_meta_prior_campaign_v4(
) -> Standard2048AffineMetaPriorCampaignV4:
    document = _campaign_document()
    return Standard2048AffineMetaPriorCampaignV4(
        _ISSUER, canonical_json_bytes(document), document["affine_campaign_id"]
    )


def verify_standard_2048_affine_meta_prior_campaign_v4(
    campaign: Standard2048AffineMetaPriorCampaignV4,
) -> Standard2048AffineMetaPriorCampaignV4:
    if type(campaign) is not Standard2048AffineMetaPriorCampaignV4:
        _fail("affine verifier rejects foreign values")
    campaign.__post_init__()
    if campaign.canonical_bytes != canonical_json_bytes(_campaign_document()):
        _fail("affine campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048AffineMetaPriorV4Error",
    "DOMAINS",
    "PROFILE_KEY",
    "Standard2048AffineMetaPriorCampaignV4",
    "run_standard_2048_affine_meta_prior_campaign_v4",
    "verify_standard_2048_affine_meta_prior_campaign_v4",
)
