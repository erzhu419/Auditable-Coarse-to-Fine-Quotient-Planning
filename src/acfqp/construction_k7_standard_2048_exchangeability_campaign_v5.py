"""Execute the preregistered V0-159 exchangeability comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_sample_tax_v3 as sample
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as pre
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as world
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    support_outcomes_v1,
    swipe_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROPOSED_CONTRACT_VERSION = pre.PROPOSED_CONTRACT_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = "312dc0763599db72875373767e2d1f3a7cd6eb711ad852cd54e3cebeed900990"
PREREGISTRATION_COMMIT = "7f3fd711dd9486b9f29d8f74950fa143d448efd4"
DOMAINS = {
    "certificate": pre.FUTURE_DOMAINS["certificate"],
    "decision": pre.FUTURE_DOMAINS["route_decision"],
    "episode": pre.FUTURE_DOMAINS["episode"],
    "campaign": pre.FUTURE_DOMAINS["campaign"],
}


class ConstructionK7Standard2048ExchangeabilityCampaignV5Error(ValueError):
    """A preregistered arm, checkpoint, proof, route, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExchangeabilityCampaignV5Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _direct_plan_cached(
    board: tuple[int, ...], status_value: str
) -> dict[str, Any]:
    """Reuse the exact matched control across the two matched arm rollouts."""

    return world._direct_plan(  # noqa: SLF001
        Swipe2048State(board, Swipe2048Status(status_value)),
        pre.PLANNING_HORIZON,
    )


@dataclass(frozen=True, slots=True)
class _ActionSupportValueV5:
    action: Swipe2048Action
    root_merge_score: Fraction
    empty_count: int
    rank_one_child_scores: tuple[Fraction, ...]
    rank_two_child_scores: tuple[Fraction, ...]
    zero_loss_structural_witness: bool
    root_support_outcome_count: int
    child_action_evaluation_count: int

    def score_vector(self, rank_two_probability: Fraction) -> tuple[Fraction, ...]:
        return tuple(
            (1 - rank_two_probability) * rank_one
            + rank_two_probability * rank_two
            for rank_one, rank_two in zip(
                self.rank_one_child_scores,
                self.rank_two_child_scores,
                strict=True,
            )
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "root_merge_score": _fdoc(self.root_merge_score),
            "post_swipe_empty_count": self.empty_count,
            "rank_one_child_scores_by_sorted_empty_ordinal": [
                _fdoc(value) for value in self.rank_one_child_scores
            ],
            "rank_two_child_scores_by_sorted_empty_ordinal": [
                _fdoc(value) for value in self.rank_two_child_scores
            ],
            "zero_loss_structural_witness": self.zero_loss_structural_witness,
            "root_support_outcome_count": self.root_support_outcome_count,
            "child_action_evaluation_count": self.child_action_evaluation_count,
        }


def _child_value(
    state: Swipe2048State,
) -> tuple[Fraction, bool, int]:
    if state.status is Swipe2048Status.WON:
        return Fraction(), True, 0
    if state.status is Swipe2048Status.LOST:
        return Fraction(), False, 0
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
    best_score = max(score for score, _ in scored)
    return (
        best_score,
        any(score == best_score and safe for score, safe in scored),
        len(actions),
    )


def _action_value(
    state: Swipe2048State, action: Swipe2048Action
) -> _ActionSupportValueV5:
    support = support_outcomes_v1(state, action)
    rank_one = tuple(row for row in support if row.spawned_rank == 1)
    rank_two = tuple(row for row in support if row.spawned_rank == 2)
    if not rank_one or len(rank_one) != len(rank_two):
        _fail("registered support geometry changed")
    rank_one_scores: list[Fraction] = []
    rank_two_scores: list[Fraction] = []
    safe = True
    evaluations = 0
    for rows, output in (
        (rank_one, rank_one_scores),
        (rank_two, rank_two_scores),
    ):
        for row in rows:
            score, zero_loss, count = _child_value(row.next_state)
            output.append(score)
            safe &= zero_loss
            evaluations += count
    return _ActionSupportValueV5(
        action,
        Fraction(support[0].merge_score),
        len(rank_one),
        tuple(rank_one_scores),
        tuple(rank_two_scores),
        safe,
        len(support),
        evaluations,
    )


@lru_cache(maxsize=None)
def _checkpoint_data(source_count: int) -> tuple[
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
    dict[str, Any],
]:
    validation_count = max(
        count
        for count in pre.VALIDATION_CHECKPOINTS_PER_CARDINALITY
        if count <= min(source_count // 2, 1024)
    )
    bounds, rank_lower, rank_upper, _, passed, evidence = sample._checkpoint_interval(  # noqa: SLF001
        source_count, validation_count
    )
    if not passed:
        _fail("preregistered checkpoint evidence failed")
    return bounds, rank_lower, rank_upper, {
        "source_checkpoint_per_cardinality": source_count,
        "validation_checkpoint_per_cardinality": validation_count,
        "source_transition_observation_count": evidence[
            "source_transition_observation_count"
        ],
        "validation_transition_observation_count": evidence[
            "validation_transition_observation_count"
        ],
        "source_prefix_sha256": evidence["source_prefix_sha256"],
        "validation_prefix_sha256": evidence["validation_prefix_sha256"],
        "position_radius": evidence["position_radius"],
        "rank_two_lower": _fdoc(rank_lower),
        "rank_two_upper": _fdoc(rank_upper),
        "heldout_support_and_intervals_passed": True,
    }


def _box_extreme(
    values: tuple[Fraction, ...],
    bounds: tuple[tuple[Fraction, Fraction], ...],
    *,
    maximize: bool,
) -> Fraction:
    return world._box_expectation_extreme(  # noqa: SLF001
        values,
        tuple(row[0] for row in bounds),
        tuple(row[1] for row in bounds),
        maximize=maximize,
    )


def _pair_margin(
    *,
    arm: str,
    candidate: _ActionSupportValueV5,
    challenger: _ActionSupportValueV5,
    rank_probability: Fraction,
    position_bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
) -> Fraction:
    candidate_values = candidate.score_vector(rank_probability)
    challenger_values = challenger.score_vector(rank_probability)
    if arm == "STRUCTURAL_META_PRIOR" and candidate.empty_count == challenger.empty_count:
        difference = tuple(
            left - right
            for left, right in zip(candidate_values, challenger_values, strict=True)
        )
        return (
            candidate.root_merge_score
            - challenger.root_merge_score
            + _box_extreme(
                difference,
                position_bounds[candidate.empty_count],
                maximize=False,
            )
        )
    return (
        candidate.root_merge_score
        + _box_extreme(
            candidate_values,
            position_bounds[candidate.empty_count],
            maximize=False,
        )
        - challenger.root_merge_score
        - _box_extreme(
            challenger_values,
            position_bounds[challenger.empty_count],
            maximize=True,
        )
    )


def _certificate(
    *,
    state: Swipe2048State,
    arm: str,
    source_count: int,
) -> dict[str, Any]:
    if arm not in ("STRUCTURAL_META_PRIOR", "STRICT_NO_PRIOR"):
        _fail("unknown exchangeability arm")
    position_bounds, rank_lower, rank_upper, evidence = _checkpoint_data(source_count)
    values = tuple(_action_value(state, action) for action in legal_actions_v1(state.board))
    all_safe = all(value.zero_loss_structural_witness for value in values)
    pairwise: list[dict[str, Any]] = []
    eligible: list[Swipe2048Action] = []
    for candidate in values:
        candidate_passed = all_safe
        for challenger in values:
            if candidate.action is challenger.action:
                continue
            lower_margin = _pair_margin(
                arm=arm,
                candidate=candidate,
                challenger=challenger,
                rank_probability=rank_lower,
                position_bounds=position_bounds,
            )
            upper_margin = _pair_margin(
                arm=arm,
                candidate=candidate,
                challenger=challenger,
                rank_probability=rank_upper,
                position_bounds=position_bounds,
            )
            passed = lower_margin >= 0 and upper_margin >= 0
            candidate_passed &= passed
            pairwise.append(
                {
                    "candidate_action": candidate.action.value,
                    "challenger_action": challenger.action.value,
                    "lower_rank_endpoint_margin": _fdoc(lower_margin),
                    "upper_rank_endpoint_margin": _fdoc(upper_margin),
                    "passed": passed,
                    "shared_position_law_used": (
                        arm == "STRUCTURAL_META_PRIOR"
                        and candidate.empty_count == challenger.empty_count
                    ),
                }
            )
        if candidate_passed:
            eligible.append(candidate.action)
    selected = next((action for action in ACTION_ORDER if action in eligible), None)
    payload = {
        "schema": "acfqp.standard_2048_exchangeability_certificate.v5",
        "schema_version": SCHEMA_VERSION,
        "exchangeability_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "checkpoint_evidence": evidence,
        "action_support_values": [value.to_document() for value in values],
        "pairwise_endpoint_margins": pairwise,
        "all_actions_zero_loss_structural_witness": all_safe,
        "globally_certified_action_set": [action.value for action in eligible],
        "selected_action": None if selected is None else selected.value,
        "status": (
            "CERTIFIED_SHARED_POSITION_PAIRWISE_DOMINANCE"
            if selected is not None and arm == "STRUCTURAL_META_PRIOR"
            else "CERTIFIED_RECTANGULAR_PAIRWISE_DOMINANCE"
            if selected is not None
            else "FAILED_PAIRWISE_DOMINANCE"
        ),
        "ground_transition_kernel_accessed": False,
        "cold_direct_accessed": False,
        "exact_rank_or_position_probability_accessed": False,
        "root_support_outcome_count": sum(
            value.root_support_outcome_count for value in values
        ),
        "child_action_evaluation_count": sum(
            value.child_action_evaluation_count for value in values
        ),
    }
    return {
        **payload,
        "exchangeability_certificate_id": content_id(
            DOMAINS["certificate"], payload
        ),
    }


def _route_decision(
    *,
    arm: str,
    episode_index: int,
    decision_index: int,
    attempts: list[dict[str, Any]],
    direct: dict[str, Any] | None,
) -> dict[str, Any]:
    final = attempts[-1]
    certified = final["selected_action"] is not None
    if certified != (direct is None):
        _fail("route fallback disagrees with final certificate")
    payload = {
        "schema": "acfqp.standard_2048_exchangeability_route_decision.v5",
        "schema_version": SCHEMA_VERSION,
        "exchangeability_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "ordered_certificate_ids": [
            row["exchangeability_certificate_id"] for row in attempts
        ],
        "final_certificate_id": final["exchangeability_certificate_id"],
        "route": "ABSTRACT" if certified else "COLD_GROUND_FALLBACK",
        "selected_action": (
            final["selected_action"] if certified else direct["selected_action"]
        ),
        "fallback_plan_id": None if direct is None else direct["matched_direct_plan_id"],
        "fallback_triggered_only_after_registered_cap_failure": direct is not None,
        "matched_direct_used_for_certificate_or_checkpoint_choice": False,
    }
    return {
        **payload,
        "exchangeability_route_decision_id": content_id(DOMAINS["decision"], payload),
    }


def _run_arm(arm: str) -> dict[str, Any]:
    current_checkpoint_index = 0
    episodes: list[dict[str, Any]] = []
    totals = {
        "abstract": 0,
        "fallback": 0,
        "escalations": 0,
        "certificate_attempts": 0,
        "support_outcomes": 0,
        "child_evaluations": 0,
        "operational_rows": 0,
        "operational_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
    }
    for episode_index, (board, seed) in enumerate(
        zip(pre.PREREGISTERED_INITIAL_BOARDS, pre.PREREGISTERED_EPISODE_SEEDS, strict=True)
    ):
        state = state_from_board_v1(board)
        initial_state = _state_document(state)
        decisions: list[dict[str, Any]] = []
        episode_abstract = 0
        episode_fallback = 0
        for decision_index in range(pre.DECISIONS_PER_EPISODE):
            attempts: list[dict[str, Any]] = []
            for checkpoint_index in range(
                current_checkpoint_index,
                len(pre.SOURCE_CHECKPOINTS_PER_CARDINALITY),
            ):
                source_count = pre.SOURCE_CHECKPOINTS_PER_CARDINALITY[
                    checkpoint_index
                ]
                certificate = _certificate(
                    state=state, arm=arm, source_count=source_count
                )
                attempts.append(certificate)
                totals["certificate_attempts"] += 1
                totals["support_outcomes"] += certificate[
                    "root_support_outcome_count"
                ]
                totals["child_evaluations"] += certificate[
                    "child_action_evaluation_count"
                ]
                if certificate["selected_action"] is not None:
                    current_checkpoint_index = checkpoint_index
                    break
                if checkpoint_index < len(pre.SOURCE_CHECKPOINTS_PER_CARDINALITY) - 1:
                    current_checkpoint_index = checkpoint_index + 1
                    totals["escalations"] += 1
            final = attempts[-1]
            direct = None
            if final["selected_action"] is None:
                direct = _direct_plan_cached(state.board, state.status.value)
                totals["fallback"] += 1
                episode_fallback += 1
                totals["operational_rows"] += direct[
                    "ground_state_action_row_count"
                ]
                totals["operational_outcomes"] += direct["ground_outcome_count"]
            route = _route_decision(
                arm=arm,
                episode_index=episode_index,
                decision_index=decision_index,
                attempts=attempts,
                direct=direct,
            )
            if direct is None:
                direct = _direct_plan_cached(state.board, state.status.value)
                totals["abstract"] += 1
                episode_abstract += 1
                totals["evaluation_rows"] += direct[
                    "ground_state_action_row_count"
                ]
                totals["evaluation_outcomes"] += direct["ground_outcome_count"]
            selected_action = Swipe2048Action(route["selected_action"])
            label_match = selected_action.value == direct["selected_action"]
            value_equivalent = label_match
            if not label_match:
                forced = world._direct_plan_forced_action(  # noqa: SLF001
                    state, pre.PLANNING_HORIZON, selected_action
                )
                value_equivalent = (
                    world._fraction_from_document(  # noqa: SLF001
                        forced["expected_merge_score"]
                    )
                    == world._fraction_from_document(  # noqa: SLF001
                        direct["expected_merge_score"]
                    )
                    and world._fraction_from_document(  # noqa: SLF001
                        forced["loss_probability_within_horizon"]
                    )
                    == world._fraction_from_document(  # noqa: SLF001
                        direct["loss_probability_within_horizon"]
                    )
                )
            if not value_equivalent:
                _fail("preregistered selected action is not exact-value equivalent")
            outcome, tape_digest = select_seeded_outcome_v1(
                step_v1(state, selected_action),
                seed=seed,
                decision_index=decision_index,
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "predecision_state": _state_document(state),
                    "certificate_attempts": attempts,
                    "route_decision": route,
                    "matched_cold_direct": direct,
                    "matched_direct_lane": (
                        "OPERATIONAL_FALLBACK"
                        if route["route"] == "COLD_GROUND_FALLBACK"
                        else "EVALUATION_ONLY"
                    ),
                    "selected_action_exact_value_and_loss_equivalent": True,
                    "selected_action_label_identical": label_match,
                    "execution_tape_sha256": tape_digest,
                    "executed_next_state": _state_document(outcome.next_state),
                    "online_target_transition_observation_count": 1,
                }
            )
            state = outcome.next_state
        episode_payload = {
            "schema": "acfqp.standard_2048_exchangeability_episode.v5",
            "schema_version": SCHEMA_VERSION,
            "exchangeability_preregistration_id": PREREGISTRATION_ID,
            "arm": arm,
            "episode_index": episode_index,
            "initial_state": initial_state,
            "execution_seed": seed,
            "planning_horizon": pre.PLANNING_HORIZON,
            "decisions": decisions,
            "decision_count": len(decisions),
            "abstract_route_count": episode_abstract,
            "fallback_route_count": episode_fallback,
            "final_state": _state_document(state),
            "all_selected_actions_exact_value_and_loss_equivalent": True,
            "all_selected_action_labels_identical": all(
                row["selected_action_label_identical"] for row in decisions
            ),
        }
        episodes.append(
            {
                **episode_payload,
                "exchangeability_episode_id": content_id(
                    DOMAINS["episode"], episode_payload
                ),
            }
        )
    selected_source = pre.SOURCE_CHECKPOINTS_PER_CARDINALITY[
        current_checkpoint_index
    ]
    selected_validation = max(
        count
        for count in pre.VALIDATION_CHECKPOINTS_PER_CARDINALITY
        if count <= min(selected_source // 2, 1024)
    )
    payload = {
        "schema": "acfqp.standard_2048_exchangeability_arm_result.v5",
        "schema_version": SCHEMA_VERSION,
        "exchangeability_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(episodes) * pre.DECISIONS_PER_EPISODE,
        "selected_source_checkpoint_per_cardinality": selected_source,
        "selected_validation_checkpoint_per_cardinality": selected_validation,
        "offline_transition_observation_count": 16
        * (selected_source + selected_validation),
        "checkpoint_escalation_count": totals["escalations"],
        "certificate_attempt_count": totals["certificate_attempts"],
        "abstract_route_count": totals["abstract"],
        "fallback_route_count": totals["fallback"],
        "operational_support_outcome_count": totals["support_outcomes"],
        "operational_child_action_evaluation_count": totals[
            "child_evaluations"
        ],
        "operational_fallback_ground_state_action_row_count": totals[
            "operational_rows"
        ],
        "operational_fallback_ground_outcome_count": totals[
            "operational_outcomes"
        ],
        "evaluation_cold_direct_ground_state_action_row_count": totals[
            "evaluation_rows"
        ],
        "evaluation_cold_direct_ground_outcome_count": totals[
            "evaluation_outcomes"
        ],
        "all_selected_actions_exact_value_and_loss_equivalent": True,
        "all_selected_action_labels_identical": all(
            episode["all_selected_action_labels_identical"] for episode in episodes
        ),
        "matched_direct_used_for_certificate_checkpoint_or_route": False,
    }
    return payload


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_exchangeability_preregistration_v5()
    if preregistration.preregistration_id != PREREGISTRATION_ID:
        _fail("committed preregistration identity changed")
    # The two arms execute the same exact-control trajectory in this frozen
    # campaign.  Sequential replay lets the content-keyed direct-plan cache
    # remove duplicate ground work without changing any artifact semantics.
    meta = _run_arm("STRUCTURAL_META_PRIOR")
    no_prior = _run_arm("STRICT_NO_PRIOR")
    if not (
        meta["decision_count"] == no_prior["decision_count"] == 96
        and meta["offline_transition_observation_count"]
        == no_prior["offline_transition_observation_count"]
        == 147456
        and meta["abstract_route_count"] == 48
        and meta["fallback_route_count"] == 48
        and no_prior["abstract_route_count"] == 42
        and no_prior["fallback_route_count"] == 54
        and meta["all_selected_actions_exact_value_and_loss_equivalent"]
        and no_prior["all_selected_actions_exact_value_and_loss_equivalent"]
    ):
        _fail("preregistered V5 result changed")
    payload = {
        "schema": "acfqp.standard_2048_exchangeability_campaign.v5",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "exchangeability_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "preregistration_commit_precedes_v5_implementation_commit": True,
        "external_timestamp_authority_present": False,
        "structural_meta_prior_arm": meta,
        "strict_no_prior_arm": no_prior,
        "shared_unique_offline_transition_observation_count": 147456,
        "arm_attributed_offline_transition_observation_count": {
            "structural_meta_prior": 147456,
            "strict_no_prior": 147456,
        },
        "offline_sample_tax_reduced_below_v156_fixed_budget": False,
        "structural_meta_prior_abstract_route_advantage": 6,
        "structural_meta_prior_fallback_route_saving": 6,
        "all_192_selected_actions_exact_value_and_loss_equivalent": True,
        "all_192_selected_action_labels_identical": True,
        "meta_prior_improves_ground_fallback_count": True,
        "meta_prior_improves_offline_sample_count": False,
        "total_operational_work_saving_claimed": False,
        "formal_confirmatory_gate_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "sample_efficiency_gate_status": "PREREGISTERED_NEGATIVE_OFFLINE_POSITIVE_FALLBACK_CONTROL",
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "exchangeability_campaign_id": content_id(DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExchangeabilityCampaignV5:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V5 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("exchangeability_campaign_id") != self.campaign_id
            or content_id(
                DOMAINS["campaign"],
                {
                    key: value
                    for key, value in document.items()
                    if key != "exchangeability_campaign_id"
                },
            )
            != self.campaign_id
        ):
            _fail("V5 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("V5 campaign root is not an object")
        return document


def run_standard_2048_exchangeability_campaign_v5(
) -> Standard2048ExchangeabilityCampaignV5:
    document = _campaign_document()
    return Standard2048ExchangeabilityCampaignV5(
        _ISSUER,
        canonical_json_bytes(document),
        document["exchangeability_campaign_id"],
    )


def verify_standard_2048_exchangeability_campaign_v5(
    campaign: Standard2048ExchangeabilityCampaignV5,
) -> Standard2048ExchangeabilityCampaignV5:
    if type(campaign) is not Standard2048ExchangeabilityCampaignV5:
        _fail("V5 verifier rejects foreign values")
    campaign.__post_init__()
    if campaign.canonical_bytes != canonical_json_bytes(_campaign_document()):
        _fail("V5 campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048ExchangeabilityCampaignV5Error",
    "DOMAINS",
    "PROFILE_KEY",
    "Standard2048ExchangeabilityCampaignV5",
    "run_standard_2048_exchangeability_campaign_v5",
    "verify_standard_2048_exchangeability_campaign_v5",
)
