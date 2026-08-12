"""Execute the exactly preregistered V0-161 targeted-acquisition campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
from math import isqrt
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_exchangeability_campaign_v5 as v5
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
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROPOSED_CONTRACT_VERSION = pre.PROPOSED_CONTRACT_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = "f3bfb0b24fb13e32dfc1592140bf92dc05167f5cd8df1ceba7a80498dc408e82"
PREREGISTRATION_COMMIT = "49a2a50"
DOMAINS = pre.FUTURE_DOMAINS


class ConstructionK7Standard2048TargetedAcquisitionCampaignV7Error(ValueError):
    """A frozen stream, acquisition rule, certificate, route, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048TargetedAcquisitionCampaignV7Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _record_stream(
    domain: str, seed: str, records_per_cardinality: int
) -> tuple[tuple[int, int, int, bool], ...]:
    records: list[tuple[int, int, int, bool]] = []
    for empty_count in range(1, 17):
        for index in range(records_per_cardinality):
            prefix = (
                domain.encode("utf-8")
                + b"\x00"
                + seed.encode("utf-8")
                + b"\x00"
                + str(empty_count).encode("ascii")
                + b"\x00"
                + str(index).encode("ascii")
                + b"\x00"
            )
            position = hashlib.sha256(prefix + b"position").digest()
            ordinal = (int.from_bytes(position, "big") * empty_count) >> 256
            rank = hashlib.sha256(prefix + b"rank").digest()
            spawned_rank = (
                2 if int.from_bytes(rank, "big") * 10 < (1 << 256) else 1
            )
            records.append((empty_count, ordinal, spawned_rank, True))
    return tuple(records)


def _source_records() -> tuple[tuple[int, int, int, bool], ...]:
    return _record_stream(
        pre.SOURCE_STREAM_DOMAIN,
        pre.SOURCE_SEED,
        pre.SOURCE_RECORDS_PER_CARDINALITY,
    )


def _validation_records() -> tuple[tuple[int, int, int, bool], ...]:
    return _record_stream(
        pre.VALIDATION_STREAM_DOMAIN,
        pre.VALIDATION_SEED,
        pre.VALIDATION_RECORDS_PER_CARDINALITY,
    )


def _pack(records: tuple[tuple[int, int, int, bool], ...]) -> bytes:
    packed = bytearray()
    for empty_count, ordinal, rank, valid in records:
        if (
            not 1 <= empty_count <= 16
            or not 0 <= ordinal < empty_count
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("raw observation changed")
        packed.extend(
            (empty_count, ordinal | ((rank - 1) << 4) | (int(valid) << 5))
        )
    return bytes(packed)


def _archive_document(*, lane: str) -> dict[str, Any]:
    if lane == "SOURCE":
        records = _source_records()
        domain = pre.SOURCE_STREAM_DOMAIN
        seed = pre.SOURCE_SEED
        content_domain = DOMAINS["source_archive"]
        records_per_cardinality = pre.SOURCE_RECORDS_PER_CARDINALITY
    elif lane == "VALIDATION":
        records = _validation_records()
        domain = pre.VALIDATION_STREAM_DOMAIN
        seed = pre.VALIDATION_SEED
        content_domain = DOMAINS["validation_archive"]
        records_per_cardinality = pre.VALIDATION_RECORDS_PER_CARDINALITY
    else:  # pragma: no cover - internal exact call sites
        _fail("unknown raw archive lane")
    payload = {
        "schema": "acfqp.standard_2048_targeted_raw_archive.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "lane": lane,
        "stream_domain": domain,
        "seed": seed,
        "records_per_cardinality": records_per_cardinality,
        "record_count": len(records),
        "packed_byte_count": len(records) * 2,
        "packed_sha256": hashlib.sha256(_pack(records)).hexdigest(),
        "generator": (
            "SHA256_DOMAIN_NUL_SEED_NUL_CARDINALITY_NUL_INDEX_NUL_"
            "POSITION_OR_RANK_V1"
        ),
        "physical_iid_randomness_claimed": False,
    }
    id_field = (
        "targeted_source_archive_id"
        if lane == "SOURCE"
        else "targeted_validation_archive_id"
    )
    return {**payload, id_field: content_id(content_domain, payload)}


def _prefix_for_cardinality(
    records: tuple[tuple[int, int, int, bool], ...],
    empty_count: int,
    count: int,
) -> tuple[tuple[int, int, int, bool], ...]:
    block = tuple(row for row in records if row[0] == empty_count)
    if len(block) < count:
        _fail("raw archive is shorter than requested prefix")
    return block[:count]


def _ceil_sqrt_ratio(numerator: int, denominator: int) -> Fraction:
    grid = pre.RADIUS_GRID_DENOMINATOR
    scaled_squared_ceiling = (numerator * grid * grid + denominator - 1) // denominator
    root = isqrt(scaled_squared_ceiling)
    if root * root < scaled_squared_ceiling:
        root += 1
    return Fraction(root, grid)


def _candidate_covers(
    candidate: str, empty_count: int, ordinal: int, valid: bool
) -> bool:
    if not valid:
        return False
    if candidate == "ALL_SORTED_EMPTY_ORDINALS":
        return 0 <= ordinal < empty_count
    if candidate == "FIRST_EMPTY_ORDINAL_ONLY":
        return ordinal == 0
    if candidate == "LAST_EMPTY_ORDINAL_ONLY":
        return ordinal == empty_count - 1
    if candidate == "EVEN_EMPTY_ORDINALS_ONLY":
        return ordinal % 2 == 0
    _fail("support candidate changed")


def _snapshot(
    source_counts: tuple[int, ...], validation_counts: tuple[int, ...]
) -> tuple[
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
    dict[str, Any],
]:
    if (
        len(source_counts) != 16
        or len(validation_counts) != 16
        or any(type(value) is not int or value <= 0 for value in source_counts)
        or any(type(value) is not int or value <= 0 for value in validation_counts)
    ):
        _fail("acquisition count vector changed")
    source_records = _source_records()
    validation_records = _validation_records()
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]] = {}
    position_rows: list[dict[str, Any]] = []
    acquired_source: list[tuple[int, int, int, bool]] = []
    acquired_validation: list[tuple[int, int, int, bool]] = []
    heldout_passed = True
    for empty_count in range(1, 17):
        source_count = source_counts[empty_count - 1]
        validation_count = validation_counts[empty_count - 1]
        source = _prefix_for_cardinality(
            source_records, empty_count, source_count
        )
        validation = _prefix_for_cardinality(
            validation_records, empty_count, validation_count
        )
        acquired_source.extend(source)
        acquired_validation.extend(validation)
        radius = _ceil_sqrt_ratio(
            pre.RADIUS_SQUARED_NUMERATOR, source_count
        )
        categories: list[tuple[Fraction, Fraction]] = []
        category_documents: list[dict[str, Any]] = []
        for ordinal in range(empty_count):
            empirical = Fraction(
                sum(row[1] == ordinal for row in source), source_count
            )
            lower = max(Fraction(), empirical - radius)
            upper = min(Fraction(1), empirical + radius)
            validation_empirical = Fraction(
                sum(row[1] == ordinal for row in validation), validation_count
            )
            inside = lower <= validation_empirical <= upper
            heldout_passed &= inside
            categories.append((lower, upper))
            category_documents.append(
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
        heldout_passed &= feasible
        bounds[empty_count] = tuple(categories)
        position_rows.append(
            {
                "empty_cardinality": empty_count,
                "source_count": source_count,
                "validation_count": validation_count,
                "radius": _fdoc(radius),
                "categories": category_documents,
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
                not _candidate_covers(candidate, row[0], row[1], row[3])
                for row in acquired_source
            ),
            "validation_violation_count": sum(
                not _candidate_covers(candidate, row[0], row[1], row[3])
                for row in acquired_validation
            ),
        }
        for candidate in pre.SUPPORT_CANDIDATES
    ]
    support_unique = tuple(
        row["candidate"] for row in evaluations if row["source_violation_count"] == 0
    ) == (pre.SELECTED_SUPPORT_RULE,)
    support_valid = (
        support_unique
        and next(
            row for row in evaluations if row["candidate"] == pre.SELECTED_SUPPORT_RULE
        )["validation_violation_count"]
        == 0
    )
    rank_radius = _ceil_sqrt_ratio(
        pre.RADIUS_SQUARED_NUMERATOR, len(acquired_source)
    )
    rank_source = Fraction(
        sum(row[2] == 2 for row in acquired_source), len(acquired_source)
    )
    rank_validation = Fraction(
        sum(row[2] == 2 for row in acquired_validation),
        len(acquired_validation),
    )
    rank_lower = max(Fraction(), rank_source - rank_radius)
    rank_upper = min(Fraction(1), rank_source + rank_radius)
    rank_inside = rank_lower <= rank_validation <= rank_upper
    heldout_passed &= support_valid and rank_inside
    evidence = {
        "source_counts_by_cardinality": list(source_counts),
        "validation_counts_by_cardinality": list(validation_counts),
        "unique_source_transition_observation_count": len(acquired_source),
        "unique_validation_transition_observation_count": len(acquired_validation),
        "unique_offline_transition_observation_count": len(acquired_source)
        + len(acquired_validation),
        "acquired_source_identity_set_sha256": hashlib.sha256(
            _pack(tuple(acquired_source))
        ).hexdigest(),
        "acquired_validation_identity_set_sha256": hashlib.sha256(
            _pack(tuple(acquired_validation))
        ).hexdigest(),
        "support_candidate_evaluations": evaluations,
        "support_selected_uniquely_from_source": support_unique,
        "position_intervals": position_rows,
        "rank_two_source_empirical": _fdoc(rank_source),
        "rank_two_validation_empirical": _fdoc(rank_validation),
        "rank_two_radius": _fdoc(rank_radius),
        "rank_two_lower": _fdoc(rank_lower),
        "rank_two_upper": _fdoc(rank_upper),
        "heldout_support_and_intervals_passed": heldout_passed,
        "physical_iid_randomness_claimed": False,
    }
    return bounds, rank_lower, rank_upper, evidence


def _pairwise_analysis(
    state: Swipe2048State,
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_lower: Fraction,
    rank_upper: Fraction,
) -> tuple[
    list[v5._ActionSupportValueV5],  # noqa: SLF001
    list[dict[str, Any]],
    list[Swipe2048Action],
    v5._ActionSupportValueV5,  # noqa: SLF001
    v5._ActionSupportValueV5 | None,  # noqa: SLF001
    Fraction,
]:
    values = [v5._action_value(state, action) for action in legal_actions_v1(state.board)]  # noqa: SLF001
    all_safe = all(value.zero_loss_structural_witness for value in values)
    pairwise: list[dict[str, Any]] = []
    candidate_minima: dict[Swipe2048Action, Fraction] = {}
    candidate_pairs: dict[Swipe2048Action, list[tuple[Fraction, v5._ActionSupportValueV5]]] = {}  # noqa: SLF001
    eligible: list[Swipe2048Action] = []
    for candidate in values:
        pairs: list[tuple[Fraction, v5._ActionSupportValueV5]] = []  # noqa: SLF001
        passed_all = all_safe
        for challenger in values:
            if candidate.action is challenger.action:
                continue
            lower = v5._pair_margin(  # noqa: SLF001
                arm="STRUCTURAL_META_PRIOR",
                candidate=candidate,
                challenger=challenger,
                rank_probability=rank_lower,
                position_bounds=bounds,
            )
            upper = v5._pair_margin(  # noqa: SLF001
                arm="STRUCTURAL_META_PRIOR",
                candidate=candidate,
                challenger=challenger,
                rank_probability=rank_upper,
                position_bounds=bounds,
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
        minimum = min((row[0] for row in pairs), default=Fraction())
        candidate_minima[candidate.action] = minimum
        candidate_pairs[candidate.action] = pairs
        if passed_all:
            eligible.append(candidate.action)
    selected = next((action for action in ACTION_ORDER if action in eligible), None)
    frontier_candidate = max(
        values,
        key=lambda value: (
            candidate_minima[value.action],
            -ACTION_ORDER.index(value.action),
        ),
    )
    blocking_pair = min(
        candidate_pairs[frontier_candidate.action],
        key=lambda row: (row[0], ACTION_ORDER.index(row[1].action)),
        default=None,
    )
    blocker = None if blocking_pair is None else blocking_pair[1]
    return (
        values,
        pairwise,
        eligible,
        frontier_candidate,
        blocker,
        candidate_minima[frontier_candidate.action],
    )


def _certificate(
    *,
    state: Swipe2048State,
    arm: str,
    source_counts: tuple[int, ...],
    validation_counts: tuple[int, ...],
) -> dict[str, Any]:
    if arm not in ("FRONTIER_CONDITIONED", "GLOBAL_PREFIX_CONTROL"):
        _fail("unknown acquisition arm")
    bounds, rank_lower, rank_upper, evidence = _snapshot(
        source_counts, validation_counts
    )
    values, pairwise, eligible, candidate, blocker, closest_margin = (
        _pairwise_analysis(state, bounds, rank_lower, rank_upper)
    )
    all_safe = all(value.zero_loss_structural_witness for value in values)
    selected = next((action for action in ACTION_ORDER if action in eligible), None)
    evidence_valid = evidence["heldout_support_and_intervals_passed"]
    if not evidence_valid:
        selected = None
    sample_repairable = selected is None and all_safe and evidence_valid and blocker is not None
    frontier = (
        sorted({candidate.empty_count, blocker.empty_count})
        if sample_repairable and blocker is not None
        else []
    )
    payload = {
        "schema": "acfqp.standard_2048_targeted_certificate.v7",
        "schema_version": SCHEMA_VERSION,
        "targeted_acquisition_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "root_state": _state_document(state),
        "planning_horizon": pre.PLANNING_HORIZON,
        "acquisition_evidence": evidence,
        "action_support_values": [value.to_document() for value in values],
        "pairwise_endpoint_margins": pairwise,
        "all_actions_zero_loss_structural_witness": all_safe,
        "globally_certified_action_set": [action.value for action in eligible],
        "selected_action": None if selected is None else selected.value,
        "closest_candidate_action": candidate.action.value,
        "closest_candidate_minimum_margin": _fdoc(closest_margin),
        "blocking_challenger_action": None if blocker is None else blocker.action.value,
        "failed_pairwise_frontier_cardinalities": frontier,
        "failure_is_sample_repairable": sample_repairable,
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
        "root_support_outcome_count": sum(
            value.root_support_outcome_count for value in values
        ),
        "child_action_evaluation_count": sum(
            value.child_action_evaluation_count for value in values
        ),
    }
    return {
        **payload,
        "targeted_certificate_id": content_id(DOMAINS["certificate"], payload),
    }


def _next_validation_count(source_count: int) -> int:
    return min(source_count // 2, pre.VALIDATION_RECORDS_PER_CARDINALITY)


def _upgrade_targeted(
    source_counts: tuple[int, ...], frontier: list[int]
) -> tuple[int, ...] | None:
    output = list(source_counts)
    changed = False
    for empty_count in frontier:
        current = output[empty_count - 1]
        index = pre.TARGETED_SOURCE_LEVELS.index(current)
        if index + 1 < len(pre.TARGETED_SOURCE_LEVELS):
            output[empty_count - 1] = pre.TARGETED_SOURCE_LEVELS[index + 1]
            changed = True
    if not changed:
        return None
    return tuple(output)


def _upgrade_global(source_counts: tuple[int, ...]) -> tuple[int, ...] | None:
    if len(set(source_counts)) != 1:
        _fail("global control count vector is not uniform")
    current = source_counts[0]
    index = pre.GLOBAL_SOURCE_LEVELS.index(current)
    if index + 1 == len(pre.GLOBAL_SOURCE_LEVELS):
        return None
    return (pre.GLOBAL_SOURCE_LEVELS[index + 1],) * 16


def _route_decision(
    *,
    arm: str,
    episode_index: int,
    decision_index: int,
    attempts: list[dict[str, Any]],
    fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    final = attempts[-1]
    certified = final["selected_action"] is not None
    if certified != (fallback is None):
        _fail("route does not follow final certificate")
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
        "selected_action": (
            final["selected_action"] if certified else fallback["selected_action"]
        ),
        "fallback_plan_id": None if fallback is None else fallback["matched_direct_plan_id"],
        "fallback_after_nonrepairable_or_hard_cap_failure": fallback is not None,
        "matched_direct_used_for_certificate_acquisition_or_route": False,
    }
    return {
        **payload,
        "targeted_route_decision_id": content_id(DOMAINS["route_decision"], payload),
    }


def _run_arm(arm: str) -> dict[str, Any]:
    source_counts = (8,) * 16
    validation_counts = (4,) * 16
    episodes: list[dict[str, Any]] = []
    totals = {
        "abstract": 0,
        "fallback": 0,
        "rounds": 0,
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
            while True:
                certificate = _certificate(
                    state=state,
                    arm=arm,
                    source_counts=source_counts,
                    validation_counts=validation_counts,
                )
                attempts.append(certificate)
                totals["attempts"] += 1
                totals["support"] += certificate["root_support_outcome_count"]
                totals["child"] += certificate["child_action_evaluation_count"]
                if certificate["selected_action"] is not None:
                    break
                upgraded = None
                if arm == "GLOBAL_PREFIX_CONTROL":
                    # The frozen V0-159 control escalates every failed
                    # certificate, including failures that more sampling
                    # cannot repair.  Preserve that cost as the matched
                    # negative control rather than optimizing it post hoc.
                    upgraded = _upgrade_global(source_counts)
                elif certificate["failure_is_sample_repairable"]:
                    upgraded = _upgrade_targeted(
                        source_counts,
                        certificate["failed_pairwise_frontier_cardinalities"],
                    )
                if upgraded is None:
                    break
                upgraded_validation = tuple(
                    _next_validation_count(count) for count in upgraded
                )
                if sum(upgraded) + sum(upgraded_validation) > (
                    pre.MAXIMUM_UNIQUE_OFFLINE_OBSERVATIONS
                ):
                    break
                source_counts = upgraded
                validation_counts = upgraded_validation
                totals["rounds"] += 1
            fallback = None
            if attempts[-1]["selected_action"] is None:
                fallback = v5._direct_plan_cached(state.board, state.status.value)  # noqa: SLF001
            route = _route_decision(
                arm=arm,
                episode_index=episode_index,
                decision_index=decision_index,
                attempts=attempts,
                fallback=fallback,
            )
            exact = fallback
            if exact is None:
                exact = v5._direct_plan_cached(state.board, state.status.value)  # noqa: SLF001
            action = Swipe2048Action(route["selected_action"])
            label_identical = action.value == exact["selected_action"]
            value_equivalent = label_identical
            if not label_identical:
                forced = v5.world._direct_plan_forced_action(  # noqa: SLF001
                    state, pre.PLANNING_HORIZON, action
                )
                value_equivalent = (
                    Fraction(forced["expected_merge_score"])
                    == Fraction(exact["expected_merge_score"])
                    and Fraction(forced["loss_probability_within_horizon"])
                    == Fraction(exact["loss_probability_within_horizon"])
                )
            if not value_equivalent:
                _fail("selected action is not exact-value equivalent")
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
                    "selected_action_label_identical": label_identical,
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
            "all_selected_actions_exact_value_and_loss_equivalent": all(
                row["selected_action_exact_value_and_loss_equivalent"]
                for row in decisions
            ),
            "all_selected_action_labels_identical": all(
                row["selected_action_label_identical"] for row in decisions
            ),
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
        "final_source_counts_by_cardinality": list(source_counts),
        "final_validation_counts_by_cardinality": list(validation_counts),
        "unique_offline_transition_observation_count": sum(source_counts)
        + sum(validation_counts),
        "acquisition_round_count": totals["rounds"],
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
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            episode["all_selected_actions_exact_value_and_loss_equivalent"]
            for episode in episodes
        ),
        "all_selected_action_labels_identical": all(
            episode["all_selected_action_labels_identical"] for episode in episodes
        ),
        "matched_direct_used_for_certificate_acquisition_or_route": False,
    }


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_targeted_acquisition_preregistration_v7()
    if preregistration.preregistration_id != PREREGISTRATION_ID:
        _fail("preregistration identity changed")
    source_archive = _archive_document(lane="SOURCE")
    validation_archive = _archive_document(lane="VALIDATION")
    targeted = _run_arm("FRONTIER_CONDITIONED")
    global_control = _run_arm("GLOBAL_PREFIX_CONTROL")
    exact = (
        targeted["all_selected_actions_exact_value_and_loss_equivalent"]
        and global_control["all_selected_actions_exact_value_and_loss_equivalent"]
    )
    reduced = targeted["unique_offline_transition_observation_count"] < global_control[
        "unique_offline_transition_observation_count"
    ]
    required_passed = exact and reduced
    payload = {
        "schema": "acfqp.standard_2048_targeted_acquisition_campaign.v7",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "targeted_acquisition_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "targeted_source_archive": source_archive,
        "targeted_validation_archive": validation_archive,
        "frontier_conditioned_arm": targeted,
        "global_prefix_control_arm": global_control,
        "decision_count_per_arm": 128,
        "total_matched_decision_count": 256,
        "targeted_unique_offline_transition_observation_count": targeted[
            "unique_offline_transition_observation_count"
        ],
        "global_control_unique_offline_transition_observation_count": global_control[
            "unique_offline_transition_observation_count"
        ],
        "targeted_offline_observation_saving": global_control[
            "unique_offline_transition_observation_count"
        ]
        - targeted["unique_offline_transition_observation_count"],
        "targeted_offline_sample_tax_reduced": reduced,
        "all_256_selected_actions_exact_value_and_loss_equivalent": exact,
        "all_required_preregistered_conditions_passed": required_passed,
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
        "sample_efficiency_gate_status": (
            "LOCAL_PREREGISTERED_TARGETED_REDUCTION_PASSED"
            if required_passed
            else "LOCAL_PREREGISTERED_TARGETED_REDUCTION_FAILED"
        ),
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "targeted_acquisition_campaign_id": content_id(DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048TargetedAcquisitionCampaignV7:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "targeted_acquisition_campaign_id"
        }
        if (
            document.get("targeted_acquisition_campaign_id") != self.campaign_id
            or content_id(DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("targeted campaign root is not an object")
        return document


def run_standard_2048_targeted_acquisition_campaign_v7(
) -> Standard2048TargetedAcquisitionCampaignV7:
    document = _campaign_document()
    return Standard2048TargetedAcquisitionCampaignV7(
        _ISSUER,
        canonical_json_bytes(document),
        document["targeted_acquisition_campaign_id"],
    )


def verify_standard_2048_targeted_acquisition_campaign_v7(
    campaign: Standard2048TargetedAcquisitionCampaignV7,
) -> Standard2048TargetedAcquisitionCampaignV7:
    if type(campaign) is not Standard2048TargetedAcquisitionCampaignV7:
        _fail("verifier rejects foreign values")
    campaign.__post_init__()
    if campaign.canonical_bytes != canonical_json_bytes(_campaign_document()):
        _fail("campaign differs from exact semantic replay")
    return campaign


__all__ = (
    "ConstructionK7Standard2048TargetedAcquisitionCampaignV7Error",
    "DOMAINS",
    "PREREGISTRATION_COMMIT",
    "PREREGISTRATION_ID",
    "PROFILE_KEY",
    "Standard2048TargetedAcquisitionCampaignV7",
    "run_standard_2048_targeted_acquisition_campaign_v7",
    "verify_standard_2048_targeted_acquisition_campaign_v7",
)
