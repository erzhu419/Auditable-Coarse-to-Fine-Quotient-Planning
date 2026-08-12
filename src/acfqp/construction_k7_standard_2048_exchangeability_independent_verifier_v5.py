"""Producer-free replay of the preregistered V0-159 2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_adaptive_sample_tax_independent_verifier_v3
    as sample,
)
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as pre
from acfqp import (
    construction_k7_standard_2048_fresh_board_support_independent_verifier_v2
    as base,
)
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
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


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
VERIFICATION_DOMAIN = pre.FUTURE_DOMAINS["verification"]


class ConstructionK7Standard2048ExchangeabilityIndependentVerifierV5Error(
    ValueError
):
    """The V0-159 bytes differ from independent semantic replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExchangeabilityIndependentVerifierV5Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@dataclass(frozen=True, slots=True)
class _ActionValue:
    action: Swipe2048Action
    root_score: Fraction
    empty_count: int
    rank_one: tuple[Fraction, ...]
    rank_two: tuple[Fraction, ...]
    zero_loss: bool
    support_count: int
    child_evaluations: int

    def score_vector(self, probability: Fraction) -> tuple[Fraction, ...]:
        return tuple(
            (1 - probability) * left + probability * right
            for left, right in zip(self.rank_one, self.rank_two, strict=True)
        )

    def document(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "root_merge_score": _fdoc(self.root_score),
            "post_swipe_empty_count": self.empty_count,
            "rank_one_child_scores_by_sorted_empty_ordinal": [
                _fdoc(value) for value in self.rank_one
            ],
            "rank_two_child_scores_by_sorted_empty_ordinal": [
                _fdoc(value) for value in self.rank_two
            ],
            "zero_loss_structural_witness": self.zero_loss,
            "root_support_outcome_count": self.support_count,
            "child_action_evaluation_count": self.child_evaluations,
        }


def _child_value(state: Swipe2048State) -> tuple[Fraction, bool, int]:
    if state.status is Swipe2048Status.WON:
        return Fraction(), True, 0
    if state.status is Swipe2048Status.LOST:
        return Fraction(), False, 0
    actions = legal_actions_v1(state.board)
    scored = tuple(
        (
            Fraction(swipe_board_v1(state.board, action)[1]),
            all(
                row.next_state.status is not Swipe2048Status.LOST
                for row in support_outcomes_v1(state, action)
            ),
        )
        for action in actions
    )
    best = max(score for score, _ in scored)
    return best, any(score == best and safe for score, safe in scored), len(actions)


def _action_value(state: Swipe2048State, action: Swipe2048Action) -> _ActionValue:
    support = support_outcomes_v1(state, action)
    rank_one_rows = tuple(row for row in support if row.spawned_rank == 1)
    rank_two_rows = tuple(row for row in support if row.spawned_rank == 2)
    if not rank_one_rows or len(rank_one_rows) != len(rank_two_rows):
        _fail("support geometry changed")
    rank_one: list[Fraction] = []
    rank_two: list[Fraction] = []
    zero_loss = True
    evaluations = 0
    for rows, values in ((rank_one_rows, rank_one), (rank_two_rows, rank_two)):
        for row in rows:
            score, safe, count = _child_value(row.next_state)
            values.append(score)
            zero_loss &= safe
            evaluations += count
    return _ActionValue(
        action,
        Fraction(support[0].merge_score),
        len(rank_one_rows),
        tuple(rank_one),
        tuple(rank_two),
        zero_loss,
        len(support),
        evaluations,
    )


@lru_cache(maxsize=None)
def _checkpoint(source_count: int) -> tuple[
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
    bounds, rank_lower, rank_upper, _, passed, evidence = sample._checkpoint(  # noqa: SLF001
        source_count, validation_count
    )
    if not passed:
        _fail("checkpoint evidence failed independent replay")
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


def _extreme(
    values: tuple[Fraction, ...],
    bounds: tuple[tuple[Fraction, Fraction], ...],
    *,
    maximize: bool,
) -> Fraction:
    return base._box_expectation_extreme(  # noqa: SLF001
        values,
        tuple(row[0] for row in bounds),
        tuple(row[1] for row in bounds),
        maximize=maximize,
    )


def _margin(
    arm: str,
    candidate: _ActionValue,
    challenger: _ActionValue,
    probability: Fraction,
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
) -> Fraction:
    candidate_values = candidate.score_vector(probability)
    challenger_values = challenger.score_vector(probability)
    if arm == "STRUCTURAL_META_PRIOR" and candidate.empty_count == challenger.empty_count:
        difference = tuple(
            left - right
            for left, right in zip(candidate_values, challenger_values, strict=True)
        )
        return (
            candidate.root_score
            - challenger.root_score
            + _extreme(difference, bounds[candidate.empty_count], maximize=False)
        )
    return (
        candidate.root_score
        + _extreme(candidate_values, bounds[candidate.empty_count], maximize=False)
        - challenger.root_score
        - _extreme(challenger_values, bounds[challenger.empty_count], maximize=True)
    )


def _certificate(
    state: Swipe2048State, arm: str, source_count: int
) -> dict[str, Any]:
    if arm not in ("STRUCTURAL_META_PRIOR", "STRICT_NO_PRIOR"):
        _fail("unknown arm")
    bounds, rank_lower, rank_upper, evidence = _checkpoint(source_count)
    values = tuple(_action_value(state, action) for action in legal_actions_v1(state.board))
    all_safe = all(value.zero_loss for value in values)
    pairwise: list[dict[str, Any]] = []
    eligible: list[Swipe2048Action] = []
    for candidate in values:
        candidate_passed = all_safe
        for challenger in values:
            if candidate.action is challenger.action:
                continue
            lower = _margin(arm, candidate, challenger, rank_lower, bounds)
            upper = _margin(arm, candidate, challenger, rank_upper, bounds)
            passed = lower >= 0 and upper >= 0
            candidate_passed &= passed
            pairwise.append(
                {
                    "candidate_action": candidate.action.value,
                    "challenger_action": challenger.action.value,
                    "lower_rank_endpoint_margin": _fdoc(lower),
                    "upper_rank_endpoint_margin": _fdoc(upper),
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
        "action_support_values": [value.document() for value in values],
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
        "root_support_outcome_count": sum(value.support_count for value in values),
        "child_action_evaluation_count": sum(
            value.child_evaluations for value in values
        ),
    }
    return {
        **payload,
        "exchangeability_certificate_id": content_id(
            DOMAINS["certificate"], payload
        ),
    }


@lru_cache(maxsize=None)
def _direct(board: tuple[int, ...], status_value: str) -> dict[str, Any]:
    return base._direct_plan(  # noqa: SLF001
        Swipe2048State(board, Swipe2048Status(status_value)),
        pre.PLANNING_HORIZON,
    )


def _route(
    arm: str,
    episode_index: int,
    decision_index: int,
    attempts: list[dict[str, Any]],
    direct: dict[str, Any] | None,
) -> dict[str, Any]:
    final = attempts[-1]
    certified = final["selected_action"] is not None
    if certified != (direct is None):
        _fail("route does not follow final certificate")
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


def _arm(arm: str) -> dict[str, Any]:
    checkpoint_index = 0
    episodes: list[dict[str, Any]] = []
    totals = {
        "abstract": 0,
        "fallback": 0,
        "escalations": 0,
        "attempts": 0,
        "support": 0,
        "child": 0,
        "operational_rows": 0,
        "operational_outcomes": 0,
        "evaluation_rows": 0,
        "evaluation_outcomes": 0,
    }
    for episode_index, (board, seed) in enumerate(
        zip(pre.PREREGISTERED_INITIAL_BOARDS, pre.PREREGISTERED_EPISODE_SEEDS, strict=True)
    ):
        state = state_from_board_v1(board)
        initial = _state_document(state)
        decisions: list[dict[str, Any]] = []
        episode_abstract = 0
        episode_fallback = 0
        for decision_index in range(pre.DECISIONS_PER_EPISODE):
            attempts: list[dict[str, Any]] = []
            for candidate_index in range(
                checkpoint_index, len(pre.SOURCE_CHECKPOINTS_PER_CARDINALITY)
            ):
                certificate = _certificate(
                    state,
                    arm,
                    pre.SOURCE_CHECKPOINTS_PER_CARDINALITY[candidate_index],
                )
                attempts.append(certificate)
                totals["attempts"] += 1
                totals["support"] += certificate["root_support_outcome_count"]
                totals["child"] += certificate["child_action_evaluation_count"]
                if certificate["selected_action"] is not None:
                    checkpoint_index = candidate_index
                    break
                if candidate_index < len(pre.SOURCE_CHECKPOINTS_PER_CARDINALITY) - 1:
                    checkpoint_index = candidate_index + 1
                    totals["escalations"] += 1
            exact = _direct(state.board, state.status.value)
            fallback = attempts[-1]["selected_action"] is None
            direct_for_route = exact if fallback else None
            route = _route(
                arm, episode_index, decision_index, attempts, direct_for_route
            )
            if route["selected_action"] != exact["selected_action"]:
                _fail("registered action no longer equals matched direct")
            if fallback:
                totals["fallback"] += 1
                episode_fallback += 1
                totals["operational_rows"] += exact["ground_state_action_row_count"]
                totals["operational_outcomes"] += exact["ground_outcome_count"]
            else:
                totals["abstract"] += 1
                episode_abstract += 1
                totals["evaluation_rows"] += exact["ground_state_action_row_count"]
                totals["evaluation_outcomes"] += exact["ground_outcome_count"]
            action = Swipe2048Action(route["selected_action"])
            outcome, digest = select_seeded_outcome_v1(
                step_v1(state, action), seed=seed, decision_index=decision_index
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "predecision_state": _state_document(state),
                    "certificate_attempts": attempts,
                    "route_decision": route,
                    "matched_cold_direct": exact,
                    "matched_direct_lane": (
                        "OPERATIONAL_FALLBACK" if fallback else "EVALUATION_ONLY"
                    ),
                    "selected_action_exact_value_and_loss_equivalent": True,
                    "selected_action_label_identical": True,
                    "execution_tape_sha256": digest,
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
            "initial_state": initial,
            "execution_seed": seed,
            "planning_horizon": pre.PLANNING_HORIZON,
            "decisions": decisions,
            "decision_count": len(decisions),
            "abstract_route_count": episode_abstract,
            "fallback_route_count": episode_fallback,
            "final_state": _state_document(state),
            "all_selected_actions_exact_value_and_loss_equivalent": True,
            "all_selected_action_labels_identical": True,
        }
        episodes.append(
            {
                **episode_payload,
                "exchangeability_episode_id": content_id(
                    DOMAINS["episode"], episode_payload
                ),
            }
        )
    source_count = pre.SOURCE_CHECKPOINTS_PER_CARDINALITY[checkpoint_index]
    validation_count = max(
        count
        for count in pre.VALIDATION_CHECKPOINTS_PER_CARDINALITY
        if count <= min(source_count // 2, 1024)
    )
    return {
        "schema": "acfqp.standard_2048_exchangeability_arm_result.v5",
        "schema_version": SCHEMA_VERSION,
        "exchangeability_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(episodes) * pre.DECISIONS_PER_EPISODE,
        "selected_source_checkpoint_per_cardinality": source_count,
        "selected_validation_checkpoint_per_cardinality": validation_count,
        "offline_transition_observation_count": 16 * (source_count + validation_count),
        "checkpoint_escalation_count": totals["escalations"],
        "certificate_attempt_count": totals["attempts"],
        "abstract_route_count": totals["abstract"],
        "fallback_route_count": totals["fallback"],
        "operational_support_outcome_count": totals["support"],
        "operational_child_action_evaluation_count": totals["child"],
        "operational_fallback_ground_state_action_row_count": totals[
            "operational_rows"
        ],
        "operational_fallback_ground_outcome_count": totals["operational_outcomes"],
        "evaluation_cold_direct_ground_state_action_row_count": totals[
            "evaluation_rows"
        ],
        "evaluation_cold_direct_ground_outcome_count": totals["evaluation_outcomes"],
        "all_selected_actions_exact_value_and_loss_equivalent": True,
        "all_selected_action_labels_identical": True,
        "matched_direct_used_for_certificate_checkpoint_or_route": False,
    }


@lru_cache(maxsize=1)
def _expected_campaign_bytes() -> bytes:
    preregistration = pre.freeze_standard_2048_exchangeability_preregistration_v5()
    if preregistration.preregistration_id != PREREGISTRATION_ID:
        _fail("committed preregistration identity changed")
    meta = _arm("STRUCTURAL_META_PRIOR")
    control = _arm("STRICT_NO_PRIOR")
    if not (
        meta["abstract_route_count"] == 48
        and meta["fallback_route_count"] == 48
        and control["abstract_route_count"] == 42
        and control["fallback_route_count"] == 54
        and meta["offline_transition_observation_count"]
        == control["offline_transition_observation_count"]
        == 147456
    ):
        _fail("preregistered replay result changed")
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
        "strict_no_prior_arm": control,
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
        "sample_efficiency_gate_status": (
            "PREREGISTERED_NEGATIVE_OFFLINE_POSITIVE_FALLBACK_CONTROL"
        ),
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "exchangeability_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class Standard2048ExchangeabilityIndependentVerificationV5:
    campaign_id: str

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "decision_count": 192,
                "meta_prior_abstract_route_count": 48,
                "strict_no_prior_abstract_route_count": 42,
                "offline_sample_tax_reduced": False,
                "exact_semantic_replay_passed": True,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_exchangeability_independent_verification.v5",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "decision_count": 192,
            "meta_prior_abstract_route_count": 48,
            "strict_no_prior_abstract_route_count": 42,
            "offline_sample_tax_reduced": False,
            "exact_semantic_replay_passed": True,
            "producer_imported": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_exchangeability_campaign_bytes_independently_v5(
    raw: bytes,
) -> Standard2048ExchangeabilityIndependentVerificationV5:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    observed = loads_canonical_json(raw)
    if type(observed) is not dict or canonical_json_bytes(observed) != raw:
        _fail("campaign is not canonical JSON")
    if raw != _expected_campaign_bytes():
        _fail("campaign differs from producer-free semantic replay")
    return Standard2048ExchangeabilityIndependentVerificationV5(
        parse_content_id(observed["exchangeability_campaign_id"])
    )


__all__ = (
    "ConstructionK7Standard2048ExchangeabilityIndependentVerifierV5Error",
    "Standard2048ExchangeabilityIndependentVerificationV5",
    "verify_standard_2048_exchangeability_campaign_bytes_independently_v5",
)
