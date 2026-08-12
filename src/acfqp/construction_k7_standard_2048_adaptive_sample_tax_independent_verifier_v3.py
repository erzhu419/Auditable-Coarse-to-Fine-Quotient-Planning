"""Producer-free replay of the standard-2048 adaptive sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import math
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_fresh_board_support_independent_verifier_v2
    as base,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_VERIFICATION_V3_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.157"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_sample_tax_v3"
SOURCE_CHECKPOINTS = (8, 32, 128, 512, 2048, 8192)
VALIDATION_CHECKPOINTS = (4, 16, 64, 256, 1024)
POSITION_RADII = {
    8: Fraction(1),
    32: Fraction(1, 2),
    128: Fraction(1, 4),
    512: Fraction(1, 8),
    2048: Fraction(1, 16),
    8192: Fraction(1, 32),
}
RANK_RADII = {
    8: Fraction(1, 4),
    32: Fraction(1, 8),
    128: Fraction(1, 16),
    512: Fraction(1, 32),
    2048: Fraction(1, 64),
    8192: Fraction(1, 128),
}
DOMAINS = {
    "profile": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN,
    "prior": CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN,
    "arm": CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN,
}
VERIFICATION_DOMAIN = CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_VERIFICATION_V3_DOMAIN


class ConstructionK7Standard2048AdaptiveSampleTaxIndependentVerifierV3Error(
    ValueError
):
    """The campaign differs from producer-free raw and semantic replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveSampleTaxIndependentVerifierV3Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _prefix(
    records: tuple[tuple[int, int, int, bool], ...], count: int
) -> tuple[tuple[int, int, int, bool], ...]:
    result: list[tuple[int, int, int, bool]] = []
    for cardinality in range(1, 17):
        block = tuple(row for row in records if row[0] == cardinality)
        if len(block) < count:
            _fail("raw observation prefix is incomplete")
        result.extend(block[:count])
    return tuple(result)


def _pack(records: tuple[tuple[int, int, int, bool], ...]) -> bytes:
    packed = bytearray()
    for cardinality, ordinal, rank, valid in records:
        if (
            not 1 <= cardinality <= 16
            or not 0 <= ordinal < cardinality
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("raw observation changed")
        packed.extend((cardinality, ordinal | ((rank - 1) << 4) | (int(valid) << 5)))
    return bytes(packed)


def _profile_document() -> dict[str, Any]:
    taylor = sum(
        Fraction(16) ** term / math.factorial(term) for term in range(13)
    )
    if not taylor > 165 * 10000:
        _fail("conditional confidence arithmetic changed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_profile.v3",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_checkpoints_per_cardinality": list(SOURCE_CHECKPOINTS),
        "validation_checkpoints_per_cardinality": list(VALIDATION_CHECKPOINTS),
        "position_radii": [
            {"checkpoint": count, "radius": _fdoc(POSITION_RADII[count])}
            for count in SOURCE_CHECKPOINTS
        ],
        "rank_radii": [
            {"checkpoint": count, "radius": _fdoc(RANK_RADII[count])}
            for count in SOURCE_CHECKPOINTS
        ],
        "unknown_support_mass_upper": [
            {"checkpoint": count, "upper": _fdoc(RANK_RADII[count])}
            for count in SOURCE_CHECKPOINTS
        ],
        "conditional_family_confidence_lower": _fdoc(Fraction(9999, 10000)),
        "union_bound_coefficient": 165,
        "hoeffding_exponent": 16,
        "exp_sixteen_taylor_last_term": 12,
        "exp_sixteen_rational_lower_bound": _fdoc(taylor),
        "confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_archives_do_not_establish_iid": True,
        "meta_start_checkpoint": 8,
        "no_prior_start_checkpoint": 8,
        "fixed_source_per_cardinality": base.SOURCE_RECORDS_PER_CARDINALITY,
        "fixed_validation_per_cardinality": base.VALIDATION_RECORDS_PER_CARDINALITY,
        "stopping_rule": (
            "UNIQUE_SOURCE_SUPPORT_AND_HELDOUT_INTERVALS_AND_ALL_REGISTERED_"
            "FRESH_BOARD_CERTIFICATES"
        ),
        "matched_direct_is_evaluation_only": True,
        "matched_direct_has_stopping_authority": False,
        "matched_direct_not_used_to_construct_intervals_or_models": True,
        "all_checkpoints_and_radii_frozen_before_observations": True,
        "hard_cap_fail_closed": True,
        "iid_claimed": False,
    }
    return {**payload, "adaptive_profile_id": content_id(DOMAINS["profile"], payload)}


def _prior_document(profile_id: str) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_identity_bound_meta_prior.v3",
        "schema_version": SCHEMA_VERSION,
        "adaptive_profile_id": profile_id,
        "prior_kind": "PREREGISTERED_CHECKPOINT_ONLY_PHILOSOPHICAL_PRIOR",
        "source_support_proposal_id": None,
        "offline_training_observation_count": 0,
        "observation_derived_prior": False,
        "structural_family": "STANDARD_4X4_SWIPE_SPAWN_D4_V1",
        "proposed_first_source_checkpoint": 8,
        "proposal_only": True,
        "interval_narrowing_authority": False,
        "certificate_authority": False,
        "target_transition_access": False,
        "stopping_rule_mutation_authority": False,
        "hard_cap_mutation_authority": False,
        "ood_must_abstain_to_no_prior": True,
    }
    return {**payload, "meta_prior_id": content_id(DOMAINS["prior"], payload)}


def _violations(
    records: tuple[tuple[int, int, int, bool], ...], candidate: str
) -> int:
    return sum(
        not base._candidate_covers(candidate, cardinality, ordinal, valid)  # noqa: SLF001
        for cardinality, ordinal, _, valid in records
    )


def _checkpoint(count: int, validation_count: int) -> tuple[
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
    Fraction,
    bool,
    dict[str, Any],
]:
    source = _prefix(base._source_support_records(), count)  # noqa: SLF001
    validation = _prefix(  # noqa: SLF001
        base._validation_support_records(), validation_count
    )
    evaluations = tuple(
        (candidate, _violations(source, candidate))
        for candidate in base.SUPPORT_CANDIDATES
    )
    selected = tuple(candidate for candidate, violations in evaluations if not violations)
    support_unique = selected == (base.SELECTED_SUPPORT_RULE,)
    support_valid = support_unique and not _violations(
        validation, base.SELECTED_SUPPORT_RULE
    )
    radius = POSITION_RADII[count]
    position_bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]] = {}
    heldout_inside = True
    for cardinality in range(1, 17):
        source_block = tuple(row for row in source if row[0] == cardinality)
        validation_block = tuple(row for row in validation if row[0] == cardinality)
        categories: list[tuple[Fraction, Fraction]] = []
        for ordinal in range(cardinality):
            empirical = Fraction(
                sum(row[1] == ordinal for row in source_block), count
            )
            lower = max(Fraction(), empirical - radius)
            upper = min(Fraction(1), empirical + radius)
            validation_empirical = Fraction(
                sum(row[1] == ordinal for row in validation_block),
                validation_count,
            )
            heldout_inside &= lower <= validation_empirical <= upper
            categories.append((lower, upper))
        heldout_inside &= (
            sum((row[0] for row in categories), Fraction())
            <= 1
            <= sum((row[1] for row in categories), Fraction())
        )
        position_bounds[cardinality] = tuple(categories)
    rank_empirical = Fraction(sum(row[2] == 2 for row in source), len(source))
    rank_lower = max(Fraction(), rank_empirical - RANK_RADII[count])
    rank_upper = min(Fraction(1), rank_empirical + RANK_RADII[count])
    validation_rank = Fraction(
        sum(row[2] == 2 for row in validation), len(validation)
    )
    heldout_inside &= rank_lower <= validation_rank <= rank_upper
    evidence = {
        "source_checkpoint_per_cardinality": count,
        "validation_checkpoint_per_cardinality": validation_count,
        "source_transition_observation_count": len(source),
        "validation_transition_observation_count": len(validation),
        "source_prefix_sha256": hashlib.sha256(_pack(source)).hexdigest(),
        "validation_prefix_sha256": hashlib.sha256(_pack(validation)).hexdigest(),
        "candidate_source_violation_counts": [
            {"candidate": candidate, "violations": violations}
            for candidate, violations in evaluations
        ],
        "support_selected_uniquely_from_source": support_unique,
        "heldout_support_and_intervals_passed": support_valid and heldout_inside,
        "rank_two_source_empirical": _fdoc(rank_empirical),
        "rank_two_lower": _fdoc(rank_lower),
        "rank_two_upper": _fdoc(rank_upper),
        "rank_two_validation_empirical": _fdoc(validation_rank),
        "position_radius": _fdoc(radius),
        "unknown_support_mass_upper": _fdoc(RANK_RADII[count]),
    }
    return (
        position_bounds,
        rank_lower,
        rank_upper,
        RANK_RADII[count],
        support_valid and heldout_inside,
        evidence,
    )


def _forced_value(
    state: base.Swipe2048State,
    horizon: int,
    forced_action: base.Swipe2048Action,
) -> tuple[Fraction, Fraction]:
    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status: str, remaining: int) -> base._ExactValueV1:
        current = base.Swipe2048State(board, base.Swipe2048Status(status))
        if remaining == 0 or current.status is base.Swipe2048Status.WON:
            return base._ExactValueV1(Fraction(), Fraction(), None)  # noqa: SLF001
        if current.status is base.Swipe2048Status.LOST:
            return base._ExactValueV1(Fraction(), Fraction(1), None)  # noqa: SLF001
        best = None
        for action in base.legal_actions_v1(current.board):
            score = Fraction()
            loss = Fraction()
            for outcome in base.step_v1(current, action):
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = base._ExactValueV1(score, loss, action)  # noqa: SLF001
            if base._better_exact(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            return base._ExactValueV1(Fraction(), Fraction(1), None)  # noqa: SLF001
        return best

    score = Fraction()
    loss = Fraction()
    for outcome in base.step_v1(state, forced_action):
        child = solve(
            outcome.next_state.board,
            outcome.next_state.status.value,
            horizon - 1,
        )
        score += outcome.probability * (outcome.merge_score + child.expected_score)
        loss += outcome.probability * child.loss_probability
    return score, loss


def _workload(
    position_bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_lower: Fraction,
    rank_upper: Fraction,
    unknown_mass: Fraction,
) -> dict[str, Any]:
    original_unknown = base.UNKNOWN_SUPPORT_MASS_UPPER
    rows: dict[tuple[tuple[int, ...], str, str], base.Standard2048SupportPartialRowV2] = {}
    decisions: list[dict[str, Any]] = []
    direct_rows = 0
    equivalent_count = 0
    try:
        base.UNKNOWN_SUPPORT_MASS_UPPER = unknown_mass
        for episode_index, (board, seed) in enumerate(
            zip(base.REGISTERED_FRESH_BOARDS, base.HELDOUT_EPISODE_SEEDS, strict=True)
        ):
            state = base.state_from_board_v1(board)
            for decision_index in range(base.EPISODE_DECISION_COUNT):
                transactions, certified, _, _ = base._recover_to_certificate(  # noqa: SLF001
                    rows,
                    state,
                    base.PLANNING_HORIZON,
                    "2" * 64,
                    "3" * 64,
                    "4" * 64,
                    "5" * 64,
                    position_bounds,
                    rank_lower,
                    rank_upper,
                )
                direct = base._direct_plan(state, base.PLANNING_HORIZON)  # noqa: SLF001
                exact_score = base._fraction_from_document(  # noqa: SLF001
                    direct["expected_merge_score"]
                )
                exact_loss = base._fraction_from_document(  # noqa: SLF001
                    direct["loss_probability_within_horizon"]
                )
                inside = (
                    base._fraction_from_document(certified["robust_score_lower"])  # noqa: SLF001
                    <= exact_score
                    <= base._fraction_from_document(certified["robust_score_upper"])  # noqa: SLF001
                    and exact_loss
                    <= base._fraction_from_document(  # noqa: SLF001
                        certified["robust_loss_probability_upper"]
                    )
                )
                selected = base.Swipe2048Action(certified["selected_action"])
                direct_action = base.Swipe2048Action(direct["selected_action"])
                label_match = selected is direct_action
                equivalent = label_match
                if not label_match:
                    forced_score, forced_loss = _forced_value(
                        state, base.PLANNING_HORIZON, selected
                    )
                    equivalent = forced_score == exact_score and forced_loss == exact_loss
                equivalent_count += int(equivalent)
                decisions.append(
                    {
                        "episode_index": episode_index,
                        "decision_index": decision_index,
                        "selected_action": selected.value,
                        "direct_action": direct_action.value,
                        "action_label_matches": label_match,
                        "exact_value_and_loss_equivalent": equivalent,
                        "exact_value_inside_robust_envelope": inside,
                        "recovery_transaction_count": len(transactions),
                    }
                )
                direct_rows += direct["ground_state_action_row_count"]
                outcome, _ = base.select_seeded_outcome_v1(
                    base.step_v1(state, selected),
                    seed=seed,
                    decision_index=decision_index,
                )
                state = outcome.next_state
    except base.ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error:
        return {
            "all_registered_decisions_certified": False,
            "all_actions_match_cold_direct": False,
            "all_actions_exact_value_and_loss_equivalent_to_cold_direct": False,
            "exact_values_inside_robust_envelopes": False,
            "decision_count": len(decisions),
            "partial_world_model_row_count": len(rows),
            "matched_direct_ground_row_count": direct_rows,
            "decision_summaries": decisions,
        }
    finally:
        base.UNKNOWN_SUPPORT_MASS_UPPER = original_unknown
    return {
        "all_registered_decisions_certified": len(decisions) == 8,
        "all_actions_match_cold_direct": all(
            row["selected_action"] == row["direct_action"] for row in decisions
        ),
        "all_actions_exact_value_and_loss_equivalent_to_cold_direct": (
            equivalent_count == len(decisions)
        ),
        "exact_values_inside_robust_envelopes": all(
            row["exact_value_inside_robust_envelope"] for row in decisions
        ),
        "decision_count": len(decisions),
        "partial_world_model_row_count": len(rows),
        "matched_direct_ground_row_count": direct_rows,
        "decision_summaries": decisions,
    }


@lru_cache(maxsize=None)
def _checkpoint_replay(count: int, validation_count: int) -> tuple[
    dict[str, Any], bool, dict[str, Any]
]:
    bounds, rank_lower, rank_upper, unknown, passed, evidence = _checkpoint(
        count, validation_count
    )
    return _workload(bounds, rank_lower, rank_upper, unknown), passed, evidence


def _arm(
    *, name: str, profile_id: str, prior_id: str | None, start: int
) -> dict[str, Any]:
    checkpoints: list[dict[str, Any]] = []
    final = None
    selected_source = selected_validation = 0
    for count in SOURCE_CHECKPOINTS:
        if count < start:
            continue
        validation_count = max(
            item
            for item in VALIDATION_CHECKPOINTS
            if item <= min(count // 2, base.VALIDATION_RECORDS_PER_CARDINALITY)
        )
        workload, passed, evidence = _checkpoint_replay(count, validation_count)
        stopped = passed and workload["all_registered_decisions_certified"]
        checkpoints.append(
            {
                **evidence,
                "matched_workload_evaluation": workload,
                "stop": stopped,
                "stop_reason": (
                    "SOURCE_SUPPORT_HELDOUT_INTERVAL_AND_PARTIAL_CERTIFICATE_PASSED"
                    if stopped
                    else "CONTINUE_OR_FAIL_CLOSED"
                ),
                "target_observations_used_to_construct_interval": 0,
                "matched_direct_used_to_construct_interval": False,
            }
        )
        if stopped:
            selected_source = count
            selected_validation = validation_count
            final = workload
            break
    if final is None:
        _fail("adaptive replay exhausted its cap")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_arm.v3",
        "schema_version": SCHEMA_VERSION,
        "arm": name,
        "adaptive_profile_id": profile_id,
        "meta_prior_id": prior_id,
        "start_checkpoint": start,
        "checkpoints": checkpoints,
        "selected_source_checkpoint_per_cardinality": selected_source,
        "selected_validation_checkpoint_per_cardinality": selected_validation,
        "source_transition_observation_count": 16 * selected_source,
        "validation_transition_observation_count": 16 * selected_validation,
        "offline_transition_observation_count": 16
        * (selected_source + selected_validation),
        "online_target_transition_observation_count": 8,
        "final_registered_workload": final,
        "first_passing_checkpoint_stops": True,
        "interval_and_certificate_use_same_data_as_no_prior": True,
        "meta_prior_proposal_only": prior_id is not None,
        "matched_direct_evaluation_only": True,
        "physical_iid_claimed": False,
    }
    return {**payload, "acquisition_arm_id": content_id(DOMAINS["arm"], payload)}


def _fixed_arm(profile_id: str) -> dict[str, Any]:
    source_count = base.SOURCE_RECORDS_PER_CARDINALITY
    validation_count = base.VALIDATION_RECORDS_PER_CARDINALITY
    workload, passed, evidence = _checkpoint_replay(source_count, validation_count)
    if not (
        passed
        and workload["all_registered_decisions_certified"]
        and workload["all_actions_exact_value_and_loss_equivalent_to_cold_direct"]
        and workload["exact_values_inside_robust_envelopes"]
    ):
        _fail("fixed-budget control replay failed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_arm.v3",
        "schema_version": SCHEMA_VERSION,
        "arm": "FIXED_BUDGET_CONTROL",
        "adaptive_profile_id": profile_id,
        "meta_prior_id": None,
        "start_checkpoint": source_count,
        "checkpoints": [
            {
                **evidence,
                "matched_workload_evaluation": workload,
                "stop": True,
                "stop_reason": "FIXED_BUDGET_CONTROL_COMPLETED",
                "target_observations_used_to_construct_interval": 0,
                "matched_direct_used_to_construct_interval": False,
            }
        ],
        "selected_source_checkpoint_per_cardinality": source_count,
        "selected_validation_checkpoint_per_cardinality": validation_count,
        "source_transition_observation_count": 16 * source_count,
        "validation_transition_observation_count": 16 * validation_count,
        "offline_transition_observation_count": 16 * (source_count + validation_count),
        "online_target_transition_observation_count": 8,
        "final_registered_workload": workload,
        "first_passing_checkpoint_stops": False,
        "interval_and_certificate_use_same_data_as_no_prior": True,
        "meta_prior_proposal_only": False,
        "matched_direct_evaluation_only": True,
        "physical_iid_claimed": False,
    }
    return {**payload, "acquisition_arm_id": content_id(DOMAINS["arm"], payload)}


@lru_cache(maxsize=1)
def _expected_campaign_bytes() -> bytes:
    profile = _profile_document()
    prior = _prior_document(profile["adaptive_profile_id"])
    meta = _arm(
        name="IDENTITY_BOUND_META_PRIOR",
        profile_id=profile["adaptive_profile_id"],
        prior_id=prior["meta_prior_id"],
        start=8,
    )
    no_prior = _arm(
        name="STRICT_NO_PRIOR",
        profile_id=profile["adaptive_profile_id"],
        prior_id=None,
        start=8,
    )
    fixed = _fixed_arm(profile["adaptive_profile_id"])
    ood = {**no_prior, "arm": "OOD_META_PRIOR_ABSTENTION"}
    ood_payload = {key: value for key, value in ood.items() if key != "acquisition_arm_id"}
    ood["acquisition_arm_id"] = content_id(DOMAINS["arm"], ood_payload)
    fixed_draws = fixed["offline_transition_observation_count"]
    adaptive_draws = meta["offline_transition_observation_count"]
    no_prior_draws = no_prior["offline_transition_observation_count"]
    if not adaptive_draws == no_prior_draws < fixed_draws:
        _fail("sample-tax comparison replay changed")
    positive = (
        meta["final_registered_workload"],
        no_prior["final_registered_workload"],
        fixed["final_registered_workload"],
    )
    if not all(
        item["decision_count"] == 8
        and item["all_registered_decisions_certified"]
        and item["all_actions_match_cold_direct"]
        and item["all_actions_exact_value_and_loss_equivalent_to_cold_direct"]
        and item["exact_values_inside_robust_envelopes"]
        for item in positive
    ):
        _fail("post-stop validation replay changed")
    saving = fixed_draws - adaptive_draws
    payload = {
        "schema": "acfqp.standard_2048_adaptive_sample_tax_campaign.v3",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "adaptive_profile": profile,
        "identity_bound_meta_prior": prior,
        "identity_bound_meta_prior_arm": meta,
        "strict_no_prior_arm": no_prior,
        "ood_abstention_arm": ood,
        "fixed_budget_control_arm": fixed,
        "fixed_budget_offline_transition_observations": fixed_draws,
        "adaptive_meta_offline_transition_observations": adaptive_draws,
        "adaptive_no_prior_offline_transition_observations": no_prior_draws,
        "adaptive_meta_offline_saving": saving,
        "adaptive_meta_offline_reduction": _fdoc(Fraction(saving, fixed_draws)),
        "registered_workload_sample_tax_reduced": True,
        "accuracy_or_certificate_relaxed": False,
        "all_positive_arms_preserve_same_cold_direct_value_and_loss": True,
        "all_positive_arm_action_labels_identical": True,
        "meta_prior_has_incremental_saving_over_no_prior": False,
        "sample_tax_reduction_attributed_to": (
            "CERTIFICATE_SENSITIVE_SEQUENTIAL_STOPPING_NOT_META_PRIOR"
        ),
        "ood_exactly_abstains_to_no_prior": True,
        "wrong_or_ood_prior_can_issue_certificate": False,
        "full_standard_2048_game_completed": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "sample_efficiency_gate_status": "REGISTERED_WORKLOAD_ONLY_NOT_BROAD_GATE",
        "actual_initial_board_long_episode_control": {
            "registered_double_tile_initial_boards": 2,
            "decisions_per_board": 8,
            "planning_horizon": 2,
            "adaptive_192_sample_value_equivalent_decisions": 14,
            "adaptive_192_sample_value_nonequivalent_decisions": 2,
            "control_status": "NEGATIVE_GENERALIZATION_CONTROL",
            "control_not_used_for_stopping_or_saving_claim": True,
            "long_initial_board_sample_tax_solved": False,
        },
        "fresh_unselected_midgame_control": {
            "registered_boards": 2,
            "decisions_per_board": 4,
            "planning_horizon": 3,
            "adaptive_192_sample_certified_decisions_before_divergence": 4,
            "adaptive_192_sample_control_completed": False,
            "control_status": "NEGATIVE_GENERALIZATION_CONTROL",
            "control_not_used_for_stopping_or_saving_claim": True,
            "cross_board_family_sample_tax_solved": False,
        },
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {**payload, "campaign_id": content_id(DOMAINS["campaign"], payload)}
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveSampleTaxIndependentVerificationV3:
    campaign_id: str
    adaptive_profile_id: str
    meta_prior_id: str
    fixed_budget_draws: int
    adaptive_meta_draws: int
    adaptive_no_prior_draws: int

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "adaptive_profile_id": self.adaptive_profile_id,
                "meta_prior_id": self.meta_prior_id,
                "fixed_budget_draws": self.fixed_budget_draws,
                "adaptive_meta_draws": self.adaptive_meta_draws,
                "adaptive_no_prior_draws": self.adaptive_no_prior_draws,
                "raw_prefixes_and_stopping_replayed": True,
                "matched_certificate_and_direct_controls_replayed": True,
                "meta_prior_and_ood_authority_replayed": True,
                "broad_sample_efficiency_verified": False,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_adaptive_sample_tax_independent_verification.v3",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "adaptive_profile_id": self.adaptive_profile_id,
            "meta_prior_id": self.meta_prior_id,
            "fixed_budget_draws": self.fixed_budget_draws,
            "adaptive_meta_draws": self.adaptive_meta_draws,
            "adaptive_no_prior_draws": self.adaptive_no_prior_draws,
            "raw_prefixes_and_stopping_replayed": True,
            "matched_certificate_and_direct_controls_replayed": True,
            "meta_prior_and_ood_authority_replayed": True,
            "broad_sample_efficiency_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_adaptive_sample_tax_campaign_bytes_independently_v3(
    raw: bytes,
) -> Standard2048AdaptiveSampleTaxIndependentVerificationV3:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    observed = loads_canonical_json(raw)
    if type(observed) is not dict or canonical_json_bytes(observed) != raw:
        _fail("campaign bytes are not canonical JSON")
    if raw != _expected_campaign_bytes():
        _fail("campaign differs from producer-free raw and semantic replay")
    profile = observed["adaptive_profile"]
    prior = observed["identity_bound_meta_prior"]
    return Standard2048AdaptiveSampleTaxIndependentVerificationV3(
        parse_content_id(observed["campaign_id"]),
        parse_content_id(profile["adaptive_profile_id"]),
        parse_content_id(prior["meta_prior_id"]),
        observed["fixed_budget_offline_transition_observations"],
        observed["adaptive_meta_offline_transition_observations"],
        observed["adaptive_no_prior_offline_transition_observations"],
    )


__all__ = (
    "ConstructionK7Standard2048AdaptiveSampleTaxIndependentVerifierV3Error",
    "Standard2048AdaptiveSampleTaxIndependentVerificationV3",
    "verify_standard_2048_adaptive_sample_tax_campaign_bytes_independently_v3",
)
