"""Producer-free semantic replay of the V0-161 targeted campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
from math import isqrt
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_exchangeability_independent_verifier_v5
    as v5,
)
from acfqp import construction_k7_standard_2048_targeted_acquisition_preregistration_v7 as pre
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
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
PREREGISTRATION_ID = "f3bfb0b24fb13e32dfc1592140bf92dc05167f5cd8df1ceba7a80498dc408e82"
PREREGISTRATION_COMMIT = "49a2a50"
DOMAINS = pre.FUTURE_DOMAINS


class ConstructionK7Standard2048TargetedAcquisitionIndependentVerifierV7Error(
    ValueError
):
    """The V0-161 bytes differ from producer-free semantic replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048TargetedAcquisitionIndependentVerifierV7Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _records(
    domain: str, seed: str, records_per_cardinality: int
) -> tuple[tuple[int, int, int, bool], ...]:
    output: list[tuple[int, int, int, bool]] = []
    for cardinality in range(1, 17):
        for index in range(records_per_cardinality):
            prefix = (
                domain.encode()
                + b"\x00"
                + seed.encode()
                + b"\x00"
                + str(cardinality).encode("ascii")
                + b"\x00"
                + str(index).encode("ascii")
                + b"\x00"
            )
            position = int.from_bytes(
                hashlib.sha256(prefix + b"position").digest(), "big"
            )
            rank = int.from_bytes(
                hashlib.sha256(prefix + b"rank").digest(), "big"
            )
            output.append(
                (
                    cardinality,
                    (position * cardinality) >> 256,
                    2 if rank * 10 < (1 << 256) else 1,
                    True,
                )
            )
    return tuple(output)


def _source() -> tuple[tuple[int, int, int, bool], ...]:
    return _records(
        pre.SOURCE_STREAM_DOMAIN,
        pre.SOURCE_SEED,
        pre.SOURCE_RECORDS_PER_CARDINALITY,
    )


def _validation() -> tuple[tuple[int, int, int, bool], ...]:
    return _records(
        pre.VALIDATION_STREAM_DOMAIN,
        pre.VALIDATION_SEED,
        pre.VALIDATION_RECORDS_PER_CARDINALITY,
    )


def _pack(records: tuple[tuple[int, int, int, bool], ...]) -> bytes:
    result = bytearray()
    for cardinality, ordinal, rank, valid in records:
        if (
            not 1 <= cardinality <= 16
            or not 0 <= ordinal < cardinality
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("raw observation record changed")
        result.extend(
            (cardinality, ordinal | ((rank - 1) << 4) | (int(valid) << 5))
        )
    return bytes(result)


def _archive(lane: str) -> dict[str, Any]:
    if lane == "SOURCE":
        records = _source()
        domain = pre.SOURCE_STREAM_DOMAIN
        seed = pre.SOURCE_SEED
        tag = DOMAINS["source_archive"]
        count = pre.SOURCE_RECORDS_PER_CARDINALITY
        field = "targeted_source_archive_id"
    else:
        records = _validation()
        domain = pre.VALIDATION_STREAM_DOMAIN
        seed = pre.VALIDATION_SEED
        tag = DOMAINS["validation_archive"]
        count = pre.VALIDATION_RECORDS_PER_CARDINALITY
        field = "targeted_validation_archive_id"
    payload = {
        "schema": "acfqp.standard_2048_targeted_raw_archive.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "lane": lane,
        "stream_domain": domain,
        "seed": seed,
        "records_per_cardinality": count,
        "record_count": len(records),
        "packed_byte_count": len(records) * 2,
        "packed_sha256": hashlib.sha256(_pack(records)).hexdigest(),
        "generator": (
            "SHA256_DOMAIN_NUL_SEED_NUL_CARDINALITY_NUL_INDEX_NUL_"
            "POSITION_OR_RANK_V1"
        ),
        "physical_iid_randomness_claimed": False,
    }
    return {**payload, field: content_id(tag, payload)}


def _prefix(
    records: tuple[tuple[int, int, int, bool], ...], cardinality: int, count: int
) -> tuple[tuple[int, int, int, bool], ...]:
    block = tuple(row for row in records if row[0] == cardinality)
    if len(block) < count:
        _fail("raw observation prefix is incomplete")
    return block[:count]


def _radius(count: int) -> Fraction:
    grid = pre.RADIUS_GRID_DENOMINATOR
    ceiling = (pre.RADIUS_SQUARED_NUMERATOR * grid * grid + count - 1) // count
    root = isqrt(ceiling)
    if root * root < ceiling:
        root += 1
    return Fraction(root, grid)


def _covers(candidate: str, cardinality: int, ordinal: int, valid: bool) -> bool:
    if not valid:
        return False
    if candidate == "ALL_SORTED_EMPTY_ORDINALS":
        return 0 <= ordinal < cardinality
    if candidate == "FIRST_EMPTY_ORDINAL_ONLY":
        return ordinal == 0
    if candidate == "LAST_EMPTY_ORDINAL_ONLY":
        return ordinal == cardinality - 1
    if candidate == "EVEN_EMPTY_ORDINALS_ONLY":
        return ordinal % 2 == 0
    _fail("support grammar changed")


@lru_cache(maxsize=None)
def _snapshot(
    source_counts: tuple[int, ...], validation_counts: tuple[int, ...]
) -> tuple[
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
    dict[str, Any],
]:
    source_rows: list[tuple[int, int, int, bool]] = []
    validation_rows: list[tuple[int, int, int, bool]] = []
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]] = {}
    position_documents: list[dict[str, Any]] = []
    heldout = True
    for cardinality in range(1, 17):
        source_count = source_counts[cardinality - 1]
        validation_count = validation_counts[cardinality - 1]
        source = _prefix(_source(), cardinality, source_count)
        validation = _prefix(_validation(), cardinality, validation_count)
        source_rows.extend(source)
        validation_rows.extend(validation)
        radius = _radius(source_count)
        categories: list[tuple[Fraction, Fraction]] = []
        documents: list[dict[str, Any]] = []
        for ordinal in range(cardinality):
            empirical = Fraction(
                sum(row[1] == ordinal for row in source), source_count
            )
            lower = max(Fraction(), empirical - radius)
            upper = min(Fraction(1), empirical + radius)
            validation_empirical = Fraction(
                sum(row[1] == ordinal for row in validation), validation_count
            )
            inside = lower <= validation_empirical <= upper
            heldout &= inside
            categories.append((lower, upper))
            documents.append(
                {
                    "ordinal": ordinal,
                    "source_empirical": _fdoc(empirical),
                    "lower": _fdoc(lower),
                    "upper": _fdoc(upper),
                    "validation_empirical": _fdoc(validation_empirical),
                    "heldout_inside": inside,
                }
            )
        feasible = (
            sum((row[0] for row in categories), Fraction())
            <= 1
            <= sum((row[1] for row in categories), Fraction())
        )
        heldout &= feasible
        bounds[cardinality] = tuple(categories)
        position_documents.append(
            {
                "empty_cardinality": cardinality,
                "source_count": source_count,
                "validation_count": validation_count,
                "radius": _fdoc(radius),
                "categories": documents,
                "probability_simplex_feasible": feasible,
                "source_prefix_sha256": hashlib.sha256(_pack(source)).hexdigest(),
                "validation_prefix_sha256": hashlib.sha256(
                    _pack(validation)
                ).hexdigest(),
            }
        )
    evaluations = [
        {
            "candidate": candidate,
            "source_violation_count": sum(
                not _covers(candidate, row[0], row[1], row[3])
                for row in source_rows
            ),
            "validation_violation_count": sum(
                not _covers(candidate, row[0], row[1], row[3])
                for row in validation_rows
            ),
        }
        for candidate in pre.SUPPORT_CANDIDATES
    ]
    support_unique = tuple(
        row["candidate"] for row in evaluations if row["source_violation_count"] == 0
    ) == (pre.SELECTED_SUPPORT_RULE,)
    support_valid = support_unique and next(
        row for row in evaluations if row["candidate"] == pre.SELECTED_SUPPORT_RULE
    )["validation_violation_count"] == 0
    rank_radius = _radius(len(source_rows))
    source_rank = Fraction(sum(row[2] == 2 for row in source_rows), len(source_rows))
    validation_rank = Fraction(
        sum(row[2] == 2 for row in validation_rows), len(validation_rows)
    )
    rank_lower = max(Fraction(), source_rank - rank_radius)
    rank_upper = min(Fraction(1), source_rank + rank_radius)
    rank_inside = rank_lower <= validation_rank <= rank_upper
    heldout &= support_valid and rank_inside
    evidence = {
        "source_counts_by_cardinality": list(source_counts),
        "validation_counts_by_cardinality": list(validation_counts),
        "unique_source_transition_observation_count": len(source_rows),
        "unique_validation_transition_observation_count": len(validation_rows),
        "unique_offline_transition_observation_count": len(source_rows)
        + len(validation_rows),
        "acquired_source_identity_set_sha256": hashlib.sha256(
            _pack(tuple(source_rows))
        ).hexdigest(),
        "acquired_validation_identity_set_sha256": hashlib.sha256(
            _pack(tuple(validation_rows))
        ).hexdigest(),
        "support_candidate_evaluations": evaluations,
        "support_selected_uniquely_from_source": support_unique,
        "position_intervals": position_documents,
        "rank_two_source_empirical": _fdoc(source_rank),
        "rank_two_validation_empirical": _fdoc(validation_rank),
        "rank_two_radius": _fdoc(rank_radius),
        "rank_two_lower": _fdoc(rank_lower),
        "rank_two_upper": _fdoc(rank_upper),
        "heldout_support_and_intervals_passed": heldout,
        "physical_iid_randomness_claimed": False,
    }
    return bounds, rank_lower, rank_upper, evidence


def _certificate(
    state: Swipe2048State,
    arm: str,
    source_counts: tuple[int, ...],
    validation_counts: tuple[int, ...],
) -> dict[str, Any]:
    bounds, rank_lower, rank_upper, evidence = _snapshot(
        source_counts, validation_counts
    )
    values = [v5._action_value(state, action) for action in legal_actions_v1(state.board)]  # noqa: SLF001
    all_safe = all(value.zero_loss for value in values)
    pairwise: list[dict[str, Any]] = []
    minima: dict[Swipe2048Action, Fraction] = {}
    blockers: dict[Swipe2048Action, list[tuple[Fraction, Any]]] = {}
    eligible: list[Swipe2048Action] = []
    for candidate in values:
        pairs: list[tuple[Fraction, Any]] = []
        passed_all = all_safe
        for challenger in values:
            if candidate.action is challenger.action:
                continue
            lower = v5._margin(  # noqa: SLF001
                "STRUCTURAL_META_PRIOR",
                candidate,
                challenger,
                rank_lower,
                bounds,
            )
            upper = v5._margin(  # noqa: SLF001
                "STRUCTURAL_META_PRIOR",
                candidate,
                challenger,
                rank_upper,
                bounds,
            )
            minimum = min(lower, upper)
            passed = lower >= 0 and upper >= 0
            passed_all &= passed
            pairs.append((minimum, challenger))
            pairwise.append(
                {
                    "candidate_action": candidate.action.value,
                    "challenger_action": challenger.action.value,
                    "candidate_empty_cardinality": candidate.empty_count,
                    "challenger_empty_cardinality": challenger.empty_count,
                    "lower_rank_endpoint_margin": _fdoc(lower),
                    "upper_rank_endpoint_margin": _fdoc(upper),
                    "minimum_endpoint_margin": _fdoc(minimum),
                    "passed": passed,
                    "shared_position_law_used": (
                        candidate.empty_count == challenger.empty_count
                    ),
                }
            )
        minima[candidate.action] = min((row[0] for row in pairs), default=Fraction())
        blockers[candidate.action] = pairs
        if passed_all:
            eligible.append(candidate.action)
    selected = next((action for action in ACTION_ORDER if action in eligible), None)
    closest = max(
        values,
        key=lambda value: (minima[value.action], -ACTION_ORDER.index(value.action)),
    )
    blocking = min(
        blockers[closest.action],
        key=lambda row: (row[0], ACTION_ORDER.index(row[1].action)),
        default=None,
    )
    blocker = None if blocking is None else blocking[1]
    evidence_valid = evidence["heldout_support_and_intervals_passed"]
    if not evidence_valid:
        selected = None
    repairable = selected is None and all_safe and evidence_valid and blocker is not None
    frontier = (
        sorted({closest.empty_count, blocker.empty_count}) if repairable else []
    )
    payload = {
        "schema": "acfqp.standard_2048_targeted_certificate.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "acquisition_evidence": evidence,
        "action_support_values": [value.document() for value in values],
        "pairwise_endpoint_margins": pairwise,
        "all_actions_zero_loss_structural_witness": all_safe,
        "globally_certified_action_set": [action.value for action in eligible],
        "selected_action": None if selected is None else selected.value,
        "closest_candidate_action": closest.action.value,
        "closest_candidate_minimum_margin": _fdoc(minima[closest.action]),
        "blocking_challenger_action": None if blocker is None else blocker.action.value,
        "failed_pairwise_frontier_cardinalities": frontier,
        "failure_is_sample_repairable": repairable,
        "status": (
            "CERTIFIED_TARGETED_PAIRWISE_DOMINANCE"
            if selected is not None and arm == "FRONTIER_CONDITIONED"
            else "CERTIFIED_GLOBAL_PAIRWISE_DOMINANCE"
            if selected is not None
            else "FAILED_HELDOUT_EVIDENCE"
            if not evidence_valid
            else "FAILED_ZERO_LOSS_WITNESS"
            if not all_safe
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
        "targeted_certificate_id": content_id(DOMAINS["certificate"], payload),
    }


def _validation_count(source_count: int) -> int:
    return min(source_count // 2, pre.VALIDATION_RECORDS_PER_CARDINALITY)


def _upgrade(
    arm: str, counts: tuple[int, ...], frontier: list[int]
) -> tuple[int, ...] | None:
    if arm == "GLOBAL_PREFIX_CONTROL":
        if len(set(counts)) != 1:
            _fail("global count vector changed")
        index = pre.GLOBAL_SOURCE_LEVELS.index(counts[0])
        return (
            None
            if index + 1 == len(pre.GLOBAL_SOURCE_LEVELS)
            else (pre.GLOBAL_SOURCE_LEVELS[index + 1],) * 16
        )
    result = list(counts)
    changed = False
    for cardinality in frontier:
        index = pre.TARGETED_SOURCE_LEVELS.index(result[cardinality - 1])
        if index + 1 < len(pre.TARGETED_SOURCE_LEVELS):
            result[cardinality - 1] = pre.TARGETED_SOURCE_LEVELS[index + 1]
            changed = True
    return tuple(result) if changed else None


def _route(
    arm: str,
    episode_index: int,
    decision_index: int,
    attempts: list[dict[str, Any]],
    direct: dict[str, Any] | None,
) -> dict[str, Any]:
    final = attempts[-1]
    certified = final["selected_action"] is not None
    payload = {
        "schema": "acfqp.standard_2048_targeted_route_decision.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "ordered_certificate_ids": [row["targeted_certificate_id"] for row in attempts],
        "final_certificate_id": final["targeted_certificate_id"],
        "route": "ABSTRACT" if certified else "COLD_GROUND_FALLBACK",
        "selected_action": final["selected_action"] if certified else direct["selected_action"],
        "fallback_plan_id": None if certified else direct["matched_direct_plan_id"],
        "fallback_after_nonrepairable_or_hard_cap_failure": not certified,
        "matched_direct_used_for_certificate_acquisition_or_route": False,
    }
    return {
        **payload,
        "targeted_route_decision_id": content_id(DOMAINS["route_decision"], payload),
    }


def _arm(arm: str) -> dict[str, Any]:
    counts = (8,) * 16
    validation_counts = (4,) * 16
    episodes: list[dict[str, Any]] = []
    totals = {key: 0 for key in (
        "abstract", "fallback", "rounds", "attempts", "support", "child",
        "operational_rows", "operational_outcomes", "evaluation_rows", "evaluation_outcomes"
    )}
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
            while True:
                certificate = _certificate(state, arm, counts, validation_counts)
                attempts.append(certificate)
                totals["attempts"] += 1
                totals["support"] += certificate["root_support_outcome_count"]
                totals["child"] += certificate["child_action_evaluation_count"]
                if certificate["selected_action"] is not None:
                    break
                upgraded = (
                    _upgrade(arm, counts, certificate["failed_pairwise_frontier_cardinalities"])
                    if arm == "GLOBAL_PREFIX_CONTROL"
                    or certificate["failure_is_sample_repairable"]
                    else None
                )
                if upgraded is None:
                    break
                upgraded_validation = tuple(_validation_count(value) for value in upgraded)
                if sum(upgraded) + sum(upgraded_validation) > pre.MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS:
                    break
                counts = upgraded
                validation_counts = upgraded_validation
                totals["rounds"] += 1
            exact = v5._direct(state.board, state.status.value)  # noqa: SLF001
            fallback = exact if attempts[-1]["selected_action"] is None else None
            route = _route(arm, episode_index, decision_index, attempts, fallback)
            if route["selected_action"] != exact["selected_action"]:
                _fail("selected action differs from independent exact control")
            if fallback is None:
                totals["abstract"] += 1
                episode_abstract += 1
                totals["evaluation_rows"] += exact["ground_state_action_row_count"]
                totals["evaluation_outcomes"] += exact["ground_outcome_count"]
                lane = "EVALUATION_ONLY"
            else:
                totals["fallback"] += 1
                episode_fallback += 1
                totals["operational_rows"] += exact["ground_state_action_row_count"]
                totals["operational_outcomes"] += exact["ground_outcome_count"]
                lane = "OPERATIONAL_FALLBACK"
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
                    "matched_direct_lane": lane,
                    "selected_action_exact_value_and_loss_equivalent": True,
                    "selected_action_label_identical": True,
                    "execution_tape_sha256": digest,
                    "executed_next_state": _state_document(outcome.next_state),
                    "online_target_transition_observation_count": 1,
                }
            )
            state = outcome.next_state
        episode_payload = {
            "schema": "acfqp.standard_2048_targeted_episode.v7",
            "schema_version": SCHEMA_VERSION,
            "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
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
                "targeted_episode_id": content_id(DOMAINS["episode"], episode_payload),
            }
        )
    return {
        "schema": "acfqp.standard_2048_targeted_arm_result.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(episodes) * pre.DECISIONS_PER_EPISODE,
        "final_source_counts_by_cardinality": list(counts),
        "final_validation_counts_by_cardinality": list(validation_counts),
        "unique_offline_transition_observation_count": sum(counts) + sum(validation_counts),
        "acquisition_round_count": totals["rounds"],
        "certificate_attempt_count": totals["attempts"],
        "abstract_route_count": totals["abstract"],
        "fallback_route_count": totals["fallback"],
        "operational_support_outcome_count": totals["support"],
        "operational_child_action_evaluation_count": totals["child"],
        "operational_fallback_ground_state_action_row_count": totals["operational_rows"],
        "operational_fallback_ground_outcome_count": totals["operational_outcomes"],
        "evaluation_cold_direct_ground_state_action_row_count": totals["evaluation_rows"],
        "evaluation_cold_direct_ground_outcome_count": totals["evaluation_outcomes"],
        "all_selected_actions_exact_value_and_loss_equivalent": True,
        "all_selected_action_labels_identical": True,
        "matched_direct_used_for_certificate_acquisition_or_route": False,
    }


@lru_cache(maxsize=1)
def _expected_bytes() -> bytes:
    preregistration = pre.freeze_standard_2048_targeted_acquisition_preregistration_v7()
    targeted = _arm("FRONTIER_CONDITIONED")
    control = _arm("GLOBAL_PREFIX_CONTROL")
    reduced = targeted["unique_offline_transition_observation_count"] < control[
        "unique_offline_transition_observation_count"
    ]
    payload = {
        "schema": "acfqp.standard_2048_targeted_acquisition_campaign.v7",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "targeted_acquisition_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "targeted_source_archive": _archive("SOURCE"),
        "targeted_validation_archive": _archive("VALIDATION"),
        "frontier_conditioned_arm": targeted,
        "global_prefix_control_arm": control,
        "decision_count_per_arm": 128,
        "total_matched_decision_count": 256,
        "targeted_unique_offline_transition_observation_count": targeted[
            "unique_offline_transition_observation_count"
        ],
        "global_control_unique_offline_transition_observation_count": control[
            "unique_offline_transition_observation_count"
        ],
        "targeted_offline_observation_saving": control[
            "unique_offline_transition_observation_count"
        ] - targeted["unique_offline_transition_observation_count"],
        "targeted_offline_sample_tax_reduced": reduced,
        "all_256_selected_actions_exact_value_and_loss_equivalent": True,
        "all_required_preregistered_conditions_passed": reduced,
        "matched_direct_has_acquisition_or_route_authority": False,
        "shared_archive_physical_observations_charged_once_at_campaign_level": True,
        "total_operational_work_saving_claimed": False,
        "conditional_family_only": True,
        "physical_iid_randomness_claimed": False,
        "formal_confirmatory_gate_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "sample_efficiency_gate_status": "LOCAL_PREREGISTERED_TARGETED_REDUCTION_PASSED",
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "targeted_acquisition_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class Standard2048TargetedAcquisitionIndependentVerificationV7:
    campaign_id: str

    @property
    def verification_id(self) -> str:
        return content_id(
            DOMAINS["verification"],
            {
                "campaign_id": self.campaign_id,
                "decision_count": 256,
                "targeted_observation_count": 55788,
                "global_control_observation_count": 147456,
                "exact_semantic_replay_passed": True,
                "broad_sample_efficiency_verified": False,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_targeted_independent_verification.v7",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "decision_count": 256,
            "targeted_observation_count": 55788,
            "global_control_observation_count": 147456,
            "exact_semantic_replay_passed": True,
            "producer_imported": False,
            "broad_sample_efficiency_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_targeted_acquisition_campaign_bytes_independently_v7(
    raw: bytes,
) -> Standard2048TargetedAcquisitionIndependentVerificationV7:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("campaign is not canonical JSON")
    if raw != _expected_bytes():
        _fail("campaign differs from producer-free semantic replay")
    return Standard2048TargetedAcquisitionIndependentVerificationV7(
        parse_content_id(document["targeted_acquisition_campaign_id"])
    )


__all__ = (
    "ConstructionK7Standard2048TargetedAcquisitionIndependentVerifierV7Error",
    "Standard2048TargetedAcquisitionIndependentVerificationV7",
    "verify_standard_2048_targeted_acquisition_campaign_bytes_independently_v7",
)
