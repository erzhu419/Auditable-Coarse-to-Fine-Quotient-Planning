"""Adaptive acquisition controls for observation-derived 2048 dynamics.

The module reuses V2's identity-separated raw source and validation streams,
but consumes only preregistered prefixes.  A source-only support proposal must
be unique, target intervals must validate, and every action chosen by the
adaptive partial model must agree with an independently cold exact planner on
the registered fresh-board workload.  Those evaluation checks are never fed
back into the production interval or planner.

The identity-bound meta-prior may propose the first source checkpoint only.
It cannot change the interval, support rule, stopping test, certificate, or
hard cap.  A strict no-prior arm uses the same checkpoint and stopping rule;
an OOD arm must reduce exactly to no-prior.  The result is scoped
to this registered workload and does not claim full-game or broad sample
efficiency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
import math
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as world
from acfqp import construction_k7_standard_2048_spawn_support_observation_v2 as observations
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.157"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_sample_tax_v3"

SOURCE_CHECKPOINTS_PER_CARDINALITY = (8, 32, 128, 512, 2048, 8192)
VALIDATION_CHECKPOINTS_PER_CARDINALITY = (4, 16, 64, 256, 1024)
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
UNKNOWN_MASS_UPPER = RANK_RADII
CONDITIONAL_FAMILY_CONFIDENCE_LOWER = Fraction(9999, 10000)
UNION_BOUND_COEFFICIENT = 165
HOEFFDING_EXPONENT = 16
EXP_TAYLOR_LAST_TERM = 12
META_START_CHECKPOINT = 8
NO_PRIOR_START_CHECKPOINT = 8
FIXED_SOURCE_PER_CARDINALITY = observations.SOURCE_RECORDS_PER_CARDINALITY
FIXED_VALIDATION_PER_CARDINALITY = observations.VALIDATION_RECORDS_PER_CARDINALITY

DOMAINS = {
    "profile": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN,
    "prior": CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN,
    "arm": CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("adaptive sample-tax domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("adaptive sample-tax domains are not registered")


class ConstructionK7Standard2048AdaptiveSampleTaxV3Error(ValueError):
    """An acquisition identity, stopping proof, control, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveSampleTaxV3Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _prefix_records(
    records: tuple[tuple[int, int, int, bool], ...], per_cardinality: int
) -> tuple[tuple[int, int, int, bool], ...]:
    output: list[tuple[int, int, int, bool]] = []
    for empty_count in range(1, 17):
        block = tuple(item for item in records if item[0] == empty_count)
        if len(block) < per_cardinality:
            _fail("raw observation archive is shorter than the checkpoint")
        output.extend(block[:per_cardinality])
    return tuple(output)


def _pack_records(records: tuple[tuple[int, int, int, bool], ...]) -> bytes:
    output = bytearray()
    for empty_count, ordinal, rank, valid in records:
        if (
            not 1 <= empty_count <= 16
            or not 0 <= ordinal < empty_count
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("adaptive raw observation changed")
        output.extend((empty_count, ordinal | ((rank - 1) << 4) | (int(valid) << 5)))
    return bytes(output)


def _profile_document() -> dict[str, Any]:
    taylor_lower = sum(
        Fraction(HOEFFDING_EXPONENT) ** term / math.factorial(term)
        for term in range(EXP_TAYLOR_LAST_TERM + 1)
    )
    if not taylor_lower > UNION_BOUND_COEFFICIENT * 10000:
        _fail("registered conditional confidence proof changed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_profile.v3",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_checkpoints_per_cardinality": list(
            SOURCE_CHECKPOINTS_PER_CARDINALITY
        ),
        "validation_checkpoints_per_cardinality": list(
            VALIDATION_CHECKPOINTS_PER_CARDINALITY
        ),
        "position_radii": [
            {"checkpoint": item, "radius": _fdoc(POSITION_RADII[item])}
            for item in SOURCE_CHECKPOINTS_PER_CARDINALITY
        ],
        "rank_radii": [
            {"checkpoint": item, "radius": _fdoc(RANK_RADII[item])}
            for item in SOURCE_CHECKPOINTS_PER_CARDINALITY
        ],
        "unknown_support_mass_upper": [
            {"checkpoint": item, "upper": _fdoc(UNKNOWN_MASS_UPPER[item])}
            for item in SOURCE_CHECKPOINTS_PER_CARDINALITY
        ],
        "conditional_family_confidence_lower": _fdoc(
            CONDITIONAL_FAMILY_CONFIDENCE_LOWER
        ),
        "union_bound_coefficient": UNION_BOUND_COEFFICIENT,
        "hoeffding_exponent": HOEFFDING_EXPONENT,
        "exp_sixteen_taylor_last_term": EXP_TAYLOR_LAST_TERM,
        "exp_sixteen_rational_lower_bound": _fdoc(taylor_lower),
        "confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_archives_do_not_establish_iid": True,
        "meta_start_checkpoint": META_START_CHECKPOINT,
        "no_prior_start_checkpoint": NO_PRIOR_START_CHECKPOINT,
        "fixed_source_per_cardinality": FIXED_SOURCE_PER_CARDINALITY,
        "fixed_validation_per_cardinality": FIXED_VALIDATION_PER_CARDINALITY,
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


def _meta_prior_document(profile_id: str) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_identity_bound_meta_prior.v3",
        "schema_version": SCHEMA_VERSION,
        "adaptive_profile_id": profile_id,
        "prior_kind": "PREREGISTERED_CHECKPOINT_ONLY_PHILOSOPHICAL_PRIOR",
        "source_support_proposal_id": None,
        "offline_training_observation_count": 0,
        "observation_derived_prior": False,
        "structural_family": "STANDARD_4X4_SWIPE_SPAWN_D4_V1",
        "proposed_first_source_checkpoint": META_START_CHECKPOINT,
        "proposal_only": True,
        "interval_narrowing_authority": False,
        "certificate_authority": False,
        "target_transition_access": False,
        "stopping_rule_mutation_authority": False,
        "hard_cap_mutation_authority": False,
        "ood_must_abstain_to_no_prior": True,
    }
    return {**payload, "meta_prior_id": content_id(DOMAINS["prior"], payload)}


def _candidate_violations(
    records: tuple[tuple[int, int, int, bool], ...], candidate: str
) -> int:
    return sum(
        not observations._candidate_covers(  # noqa: SLF001
            candidate, empty_count, ordinal, valid
        )
        for empty_count, ordinal, _, valid in records
    )


def _checkpoint_interval(
    source_count: int, validation_count: int
) -> tuple[
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
    Fraction,
    bool,
    dict[str, Any],
]:
    source = _prefix_records(observations.source_records_v2(), source_count)
    validation = _prefix_records(
        observations.validation_records_v2(), validation_count
    )
    evaluations = tuple(
        (candidate, _candidate_violations(source, candidate))
        for candidate in observations.SUPPORT_CANDIDATES
    )
    selected = tuple(candidate for candidate, violations in evaluations if violations == 0)
    support_unique = selected == (observations.SELECTED_SUPPORT_RULE,)
    support_validation = (
        support_unique
        and _candidate_violations(validation, observations.SELECTED_SUPPORT_RULE) == 0
    )
    radius = POSITION_RADII[source_count]
    position_bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]] = {}
    heldout_inside = True
    for empty_count in range(1, 17):
        source_block = tuple(item for item in source if item[0] == empty_count)
        validation_block = tuple(item for item in validation if item[0] == empty_count)
        categories: list[tuple[Fraction, Fraction]] = []
        for ordinal in range(empty_count):
            empirical = Fraction(
                sum(item[1] == ordinal for item in source_block), source_count
            )
            lower = max(Fraction(), empirical - radius)
            upper = min(Fraction(1), empirical + radius)
            validation_empirical = Fraction(
                sum(item[1] == ordinal for item in validation_block),
                validation_count,
            )
            heldout_inside &= lower <= validation_empirical <= upper
            categories.append((lower, upper))
        heldout_inside &= (
            sum((item[0] for item in categories), Fraction())
            <= 1
            <= sum((item[1] for item in categories), Fraction())
        )
        position_bounds[empty_count] = tuple(categories)
    rank_empirical = Fraction(sum(item[2] == 2 for item in source), len(source))
    rank_radius = RANK_RADII[source_count]
    rank_lower = max(Fraction(), rank_empirical - rank_radius)
    rank_upper = min(Fraction(1), rank_empirical + rank_radius)
    validation_rank = Fraction(
        sum(item[2] == 2 for item in validation), len(validation)
    )
    heldout_inside &= rank_lower <= validation_rank <= rank_upper
    evidence = {
        "source_checkpoint_per_cardinality": source_count,
        "validation_checkpoint_per_cardinality": validation_count,
        "source_transition_observation_count": len(source),
        "validation_transition_observation_count": len(validation),
        "source_prefix_sha256": hashlib.sha256(_pack_records(source)).hexdigest(),
        "validation_prefix_sha256": hashlib.sha256(
            _pack_records(validation)
        ).hexdigest(),
        "candidate_source_violation_counts": [
            {"candidate": candidate, "violations": violations}
            for candidate, violations in evaluations
        ],
        "support_selected_uniquely_from_source": support_unique,
        "heldout_support_and_intervals_passed": support_validation and heldout_inside,
        "rank_two_source_empirical": _fdoc(rank_empirical),
        "rank_two_lower": _fdoc(rank_lower),
        "rank_two_upper": _fdoc(rank_upper),
        "rank_two_validation_empirical": _fdoc(validation_rank),
        "position_radius": _fdoc(radius),
        "unknown_support_mass_upper": _fdoc(UNKNOWN_MASS_UPPER[source_count]),
    }
    return (
        position_bounds,
        rank_lower,
        rank_upper,
        UNKNOWN_MASS_UPPER[source_count],
        support_validation and heldout_inside,
        evidence,
    )


def _evaluate_registered_workload(
    *,
    position_bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_lower: Fraction,
    rank_upper: Fraction,
    unknown_mass_upper: Fraction,
) -> dict[str, Any]:
    original_unknown = world.UNKNOWN_SUPPORT_MASS_UPPER
    rows: dict[tuple[tuple[int, ...], str, str], world.Standard2048SupportPartialRowV2] = {}
    decisions: list[dict[str, Any]] = []
    total_rows = 0
    total_direct_rows = 0
    value_equivalent_count = 0
    try:
        world.UNKNOWN_SUPPORT_MASS_UPPER = unknown_mass_upper
        for episode_index, (board, seed) in enumerate(
            zip(world.REGISTERED_FRESH_BOARDS, world.HELDOUT_EPISODE_SEEDS, strict=True)
        ):
            state = world.state_from_board_v1(board)
            for decision_index in range(world.EPISODE_DECISION_COUNT):
                transactions, certified, added_rows, _ = world._recover_to_certificate(  # noqa: SLF001
                    rows,
                    state,
                    world.PLANNING_HORIZON,
                    "2" * 64,
                    "3" * 64,
                    "4" * 64,
                    "5" * 64,
                    position_bounds,
                    rank_lower,
                    rank_upper,
                )
                direct = world._direct_plan(state, world.PLANNING_HORIZON)  # noqa: SLF001
                exact_score = world._fraction_from_document(  # noqa: SLF001
                    direct["expected_merge_score"]
                )
                exact_loss = world._fraction_from_document(  # noqa: SLF001
                    direct["loss_probability_within_horizon"]
                )
                inside = (
                    world._fraction_from_document(certified["robust_score_lower"])  # noqa: SLF001
                    <= exact_score
                    <= world._fraction_from_document(certified["robust_score_upper"])  # noqa: SLF001
                    and exact_loss
                    <= world._fraction_from_document(  # noqa: SLF001
                        certified["robust_loss_probability_upper"]
                    )
                )
                selected_action = world.Swipe2048Action(certified["selected_action"])
                direct_action = world.Swipe2048Action(direct["selected_action"])
                label_match = selected_action is direct_action
                value_equivalent = label_match
                if not label_match:
                    selected_direct = world._direct_plan_forced_action(  # noqa: SLF001
                        state, world.PLANNING_HORIZON, selected_action
                    )
                    value_equivalent = (
                        world._fraction_from_document(  # noqa: SLF001
                            selected_direct["expected_merge_score"]
                        )
                        == exact_score
                        and world._fraction_from_document(  # noqa: SLF001
                            selected_direct["loss_probability_within_horizon"]
                        )
                        == exact_loss
                    )
                value_equivalent_count += int(value_equivalent)
                decisions.append(
                    {
                        "episode_index": episode_index,
                        "decision_index": decision_index,
                        "selected_action": selected_action.value,
                        "direct_action": direct_action.value,
                        "action_label_matches": label_match,
                        "exact_value_and_loss_equivalent": value_equivalent,
                        "exact_value_inside_robust_envelope": inside,
                        "recovery_transaction_count": len(transactions),
                    }
                )
                total_rows += added_rows
                total_direct_rows += direct["ground_state_action_row_count"]
                outcomes = world.step_v1(state, selected_action)
                selected, _ = world.select_seeded_outcome_v1(
                    outcomes,
                    seed=seed,
                    decision_index=decision_index,
                )
                state = selected.next_state
    except world.ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error:
        return {
            "all_registered_decisions_certified": False,
            "all_actions_match_cold_direct": False,
            "all_actions_exact_value_and_loss_equivalent_to_cold_direct": False,
            "exact_values_inside_robust_envelopes": False,
            "decision_count": len(decisions),
            "partial_world_model_row_count": len(rows),
            "matched_direct_ground_row_count": total_direct_rows,
            "decision_summaries": decisions,
        }
    finally:
        world.UNKNOWN_SUPPORT_MASS_UPPER = original_unknown
    return {
        "all_registered_decisions_certified": len(decisions) == 8,
        "all_actions_match_cold_direct": all(
            item["selected_action"] == item["direct_action"] for item in decisions
        ),
        "all_actions_exact_value_and_loss_equivalent_to_cold_direct": (
            value_equivalent_count == len(decisions)
        ),
        "exact_values_inside_robust_envelopes": all(
            item["exact_value_inside_robust_envelope"] for item in decisions
        ),
        "decision_count": len(decisions),
        "partial_world_model_row_count": len(rows),
        "matched_direct_ground_row_count": total_direct_rows,
        "decision_summaries": decisions,
    }


@lru_cache(maxsize=None)
def _evaluate_checkpoint_cached(
    source_count: int, validation_count: int
) -> tuple[dict[str, Any], bool, dict[str, Any]]:
    (
        position_bounds,
        rank_lower,
        rank_upper,
        unknown_upper,
        evidence_passed,
        evidence,
    ) = _checkpoint_interval(source_count, validation_count)
    workload = _evaluate_registered_workload(
        position_bounds=position_bounds,
        rank_lower=rank_lower,
        rank_upper=rank_upper,
        unknown_mass_upper=unknown_upper,
    )
    return workload, evidence_passed, evidence


def _run_arm(
    *,
    arm: str,
    profile_id: str,
    meta_prior_id: str | None,
    start_checkpoint: int,
) -> dict[str, Any]:
    if start_checkpoint not in SOURCE_CHECKPOINTS_PER_CARDINALITY:
        _fail("arm start checkpoint changed")
    checkpoints: list[dict[str, Any]] = []
    selected_source = 0
    selected_validation = 0
    final_workload: dict[str, Any] | None = None
    started = False
    for source_count in SOURCE_CHECKPOINTS_PER_CARDINALITY:
        if source_count < start_checkpoint:
            continue
        started = True
        validation_count = max(
            item
            for item in VALIDATION_CHECKPOINTS_PER_CARDINALITY
            if item <= min(source_count // 2, FIXED_VALIDATION_PER_CARDINALITY)
        )
        workload, evidence_passed, evidence = _evaluate_checkpoint_cached(
            source_count, validation_count
        )
        stopped = evidence_passed and workload[
            "all_registered_decisions_certified"
        ]
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
            selected_source = source_count
            selected_validation = validation_count
            final_workload = workload
            break
    if not started or final_workload is None:
        _fail("adaptive arm exhausted its cap without a registered certificate")
    source_draws = 16 * selected_source
    validation_draws = 16 * selected_validation
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_arm.v3",
        "schema_version": SCHEMA_VERSION,
        "arm": arm,
        "adaptive_profile_id": profile_id,
        "meta_prior_id": meta_prior_id,
        "start_checkpoint": start_checkpoint,
        "checkpoints": checkpoints,
        "selected_source_checkpoint_per_cardinality": selected_source,
        "selected_validation_checkpoint_per_cardinality": selected_validation,
        "source_transition_observation_count": source_draws,
        "validation_transition_observation_count": validation_draws,
        "offline_transition_observation_count": source_draws + validation_draws,
        "online_target_transition_observation_count": 8,
        "final_registered_workload": final_workload,
        "first_passing_checkpoint_stops": True,
        "interval_and_certificate_use_same_data_as_no_prior": True,
        "meta_prior_proposal_only": meta_prior_id is not None,
        "matched_direct_evaluation_only": True,
        "physical_iid_claimed": False,
    }
    return {**payload, "acquisition_arm_id": content_id(DOMAINS["arm"], payload)}


def _fixed_arm(profile_id: str) -> dict[str, Any]:
    workload, passed, evidence = _evaluate_checkpoint_cached(
        FIXED_SOURCE_PER_CARDINALITY, FIXED_VALIDATION_PER_CARDINALITY
    )
    if not (
        passed
        and workload["all_registered_decisions_certified"]
        and workload["all_actions_exact_value_and_loss_equivalent_to_cold_direct"]
        and workload["exact_values_inside_robust_envelopes"]
    ):
        _fail("fixed-budget control changed")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_acquisition_arm.v3",
        "schema_version": SCHEMA_VERSION,
        "arm": "FIXED_BUDGET_CONTROL",
        "adaptive_profile_id": profile_id,
        "meta_prior_id": None,
        "start_checkpoint": FIXED_SOURCE_PER_CARDINALITY,
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
        "selected_source_checkpoint_per_cardinality": FIXED_SOURCE_PER_CARDINALITY,
        "selected_validation_checkpoint_per_cardinality": FIXED_VALIDATION_PER_CARDINALITY,
        "source_transition_observation_count": 16 * FIXED_SOURCE_PER_CARDINALITY,
        "validation_transition_observation_count": 16 * FIXED_VALIDATION_PER_CARDINALITY,
        "offline_transition_observation_count": 16
        * (FIXED_SOURCE_PER_CARDINALITY + FIXED_VALIDATION_PER_CARDINALITY),
        "online_target_transition_observation_count": 8,
        "final_registered_workload": workload,
        "first_passing_checkpoint_stops": False,
        "interval_and_certificate_use_same_data_as_no_prior": True,
        "meta_prior_proposal_only": False,
        "matched_direct_evaluation_only": True,
        "physical_iid_claimed": False,
    }
    return {**payload, "acquisition_arm_id": content_id(DOMAINS["arm"], payload)}


def _campaign_document() -> dict[str, Any]:
    profile = _profile_document()
    prior = _meta_prior_document(profile["adaptive_profile_id"])
    meta = _run_arm(
        arm="IDENTITY_BOUND_META_PRIOR",
        profile_id=profile["adaptive_profile_id"],
        meta_prior_id=prior["meta_prior_id"],
        start_checkpoint=META_START_CHECKPOINT,
    )
    no_prior = _run_arm(
        arm="STRICT_NO_PRIOR",
        profile_id=profile["adaptive_profile_id"],
        meta_prior_id=None,
        start_checkpoint=NO_PRIOR_START_CHECKPOINT,
    )
    fixed = _fixed_arm(profile["adaptive_profile_id"])
    ood = {**no_prior, "arm": "OOD_META_PRIOR_ABSTENTION"}
    ood_payload = {key: value for key, value in ood.items() if key != "acquisition_arm_id"}
    ood["acquisition_arm_id"] = content_id(DOMAINS["arm"], ood_payload)
    fixed_draws = fixed["offline_transition_observation_count"]
    meta_draws = meta["offline_transition_observation_count"]
    no_prior_draws = no_prior["offline_transition_observation_count"]
    if not (
        meta_draws == no_prior_draws < fixed_draws
        and ood["selected_source_checkpoint_per_cardinality"]
        == no_prior["selected_source_checkpoint_per_cardinality"]
        and ood["selected_validation_checkpoint_per_cardinality"]
        == no_prior["selected_validation_checkpoint_per_cardinality"]
        and ood["final_registered_workload"] == no_prior["final_registered_workload"]
    ):
        _fail("matched sample-tax controls changed")
    positive_workloads = (
        meta["final_registered_workload"],
        no_prior["final_registered_workload"],
        fixed["final_registered_workload"],
    )
    if not all(
        workload["decision_count"] == 8
        and workload["all_registered_decisions_certified"]
        and workload["all_actions_match_cold_direct"]
        and workload["all_actions_exact_value_and_loss_equivalent_to_cold_direct"]
        and workload["exact_values_inside_robust_envelopes"]
        for workload in positive_workloads
    ):
        _fail("post-stop matched validation changed")
    saving = fixed_draws - meta_draws
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
        "adaptive_meta_offline_transition_observations": meta_draws,
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
    return {**payload, "campaign_id": content_id(DOMAINS["campaign"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveSampleTaxCampaignV3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or content_id(
                DOMAINS["campaign"],
                {key: value for key, value in document.items() if key != "campaign_id"},
            )
            != self.campaign_id
        ):
            _fail("campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("campaign root is not an object")
        return document


def run_standard_2048_adaptive_sample_tax_campaign_v3(
) -> Standard2048AdaptiveSampleTaxCampaignV3:
    document = _campaign_document()
    return Standard2048AdaptiveSampleTaxCampaignV3(
        _ISSUER, canonical_json_bytes(document), document["campaign_id"]
    )


def verify_standard_2048_adaptive_sample_tax_campaign_v3(
    campaign: Standard2048AdaptiveSampleTaxCampaignV3,
) -> Standard2048AdaptiveSampleTaxCampaignV3:
    if type(campaign) is not Standard2048AdaptiveSampleTaxCampaignV3:
        _fail("campaign verifier rejects foreign values")
    campaign.__post_init__()
    if campaign.canonical_bytes != canonical_json_bytes(_campaign_document()):
        _fail("campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048AdaptiveSampleTaxV3Error",
    "DOMAINS",
    "PROFILE_KEY",
    "Standard2048AdaptiveSampleTaxCampaignV3",
    "run_standard_2048_adaptive_sample_tax_campaign_v3",
    "verify_standard_2048_adaptive_sample_tax_campaign_v3",
)
