"""Execute the preregistered H3 meta-prior sample-tax route comparison."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_factored_operator_campaign_v9 as v164
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as model
from acfqp import construction_k7_standard_2048_h3_reuse_campaign_v8 as v163
from acfqp import construction_k7_standard_2048_meta_prior_route_preregistration_v10 as pre
from acfqp import construction_k7_standard_2048_targeted_acquisition_campaign_v7 as v161
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROPOSED_CONTRACT_VERSION = pre.PROPOSED_CONTRACT_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = pre.PREREGISTRATION_ID
PREREGISTRATION_COMMIT = "133248e"
DOMAINS = pre.FUTURE_DOMAINS
EPISODE_PROCESS_COUNT = 8
EXPECTED_CAMPAIGN_ID = (
    "6838c6ed5764d1f514247eee98f2d6d7a3992e3a29c0a4ac85ba8182b0afdcd0"
)
EXPECTED_META_ABSTRACT_ROUTE_COUNT = 24
EXPECTED_META_FALLBACK_ROUTE_COUNT = 40
EXPECTED_OBSERVATION_ABSTRACT_ROUTE_COUNT = 21
EXPECTED_OBSERVATION_FALLBACK_ROUTE_COUNT = 43
EXPECTED_OFFLINE_OBSERVATION_SAVING = 55596
EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT_PER_ARM = 355761
EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT_PER_ARM = 7376658
EXPECTED_META_OPERATIONAL_FALLBACK_ROW_COUNT = 289451
EXPECTED_OBSERVATION_OPERATIONAL_FALLBACK_ROW_COUNT = 315755


class ConstructionK7Standard2048MetaPriorRouteCampaignV10Error(ValueError):
    """A prior, operator, certificate, route, target tape, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048MetaPriorRouteCampaignV10Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        _fail("rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _observation_evidence(
    arm: str,
) -> tuple[
    dict[str, Any],
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
]:
    source_archive = v161._archive_document(lane="SOURCE")  # noqa: SLF001
    validation_archive = v161._archive_document(lane="VALIDATION")  # noqa: SLF001
    if arm == "STRUCTURAL_META_PRIOR":
        source_counts = (pre.META_PRIOR_SOURCE_PREFIX_PER_CARDINALITY,) * 16
        validation_counts = (
            pre.META_PRIOR_VALIDATION_PREFIX_PER_CARDINALITY,
        ) * 16
        _, lower, upper, raw = v161._snapshot(  # noqa: SLF001
            source_counts, validation_counts
        )
        bounds = {
            empty_count: tuple(
                (Fraction(1, empty_count), Fraction(1, empty_count))
                for _ in range(empty_count)
            )
            for empty_count in range(1, 17)
        }
        if (
            raw["unique_offline_transition_observation_count"]
            != pre.META_PRIOR_OFFLINE_OBSERVATION_COUNT
            or not raw["heldout_support_and_intervals_passed"]
        ):
            _fail("meta-prior prefix evidence changed")
        evidence = {
            "arm": arm,
            "targeted_source_archive_id": source_archive[
                "targeted_source_archive_id"
            ],
            "targeted_validation_archive_id": validation_archive[
                "targeted_validation_archive_id"
            ],
            "source_counts_by_cardinality": list(source_counts),
            "validation_counts_by_cardinality": list(validation_counts),
            "unique_offline_transition_observation_count": (
                pre.META_PRIOR_OFFLINE_OBSERVATION_COUNT
            ),
            "position_probability_semantics": (
                "REGISTERED_EXACT_UNIFORM_EXCHANGEABILITY_GIVEN_EMPTY_COUNT"
            ),
            "rank_two_probability_lower": _fdoc(lower),
            "rank_two_probability_upper": _fdoc(upper),
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
        return evidence, bounds, lower, upper
    if arm != "STRICT_OBSERVATION_ONLY":
        _fail("unknown sample-tax arm")
    source_counts = (
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        256,
        8192,
        8192,
        8192,
        8192,
        8192,
        8192,
        8,
    )
    validation_counts = (
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        128,
        1024,
        1024,
        1024,
        1024,
        1024,
        1024,
        4,
    )
    bounds, lower, upper, raw = v161._snapshot(  # noqa: SLF001
        source_counts, validation_counts
    )
    if (
        raw["unique_offline_transition_observation_count"]
        != pre.OBSERVATION_ONLY_OFFLINE_OBSERVATION_COUNT
        or not raw["heldout_support_and_intervals_passed"]
    ):
        _fail("observation-only evidence changed")
    evidence = {
        "arm": arm,
        "targeted_source_archive_id": source_archive[
            "targeted_source_archive_id"
        ],
        "targeted_validation_archive_id": validation_archive[
            "targeted_validation_archive_id"
        ],
        "source_counts_by_cardinality": list(source_counts),
        "validation_counts_by_cardinality": list(validation_counts),
        "unique_offline_transition_observation_count": (
            pre.OBSERVATION_ONLY_OFFLINE_OBSERVATION_COUNT
        ),
        "position_probability_semantics": (
            "V161_CARDINALITY_SPECIFIC_OBSERVATION_INTERVALS"
        ),
        "rank_two_probability_lower": _fdoc(lower),
        "rank_two_probability_upper": _fdoc(upper),
        "rank_two_source_empirical": raw["rank_two_source_empirical"],
        "rank_two_validation_empirical": raw["rank_two_validation_empirical"],
        "rank_two_radius": raw["rank_two_radius"],
        "heldout_support_and_intervals_passed": True,
        "structural_uniform_position_prior_used": False,
        "conditional_on_registered_iid_shared_law": True,
    }
    return evidence, bounds, lower, upper


def _operator_document(arm: str, evidence: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_meta_prior_factored_operator.v10",
        "schema_version": SCHEMA_VERSION,
        "meta_prior_route_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "v164_factored_campaign_id": pre.V164_FACTORED_CAMPAIGN_ID,
        "targeted_source_archive_id": evidence["targeted_source_archive_id"],
        "targeted_validation_archive_id": evidence[
            "targeted_validation_archive_id"
        ],
        "offline_evidence": evidence,
        "support_rule": "ALL_SORTED_EMPTY_ORDINALS",
        "deterministic_swipe_known": True,
        "successors_generated_lazily_inside_bellman_backup": True,
        "state_action_rows_serialized_or_persisted": False,
        "exact_rational_arithmetic": True,
        "unknown_support_mass_within_registered_family": _fdoc(Fraction()),
        "ground_transition_kernel_accessed": False,
        "open_ended_operator_invention_claimed": False,
    }
    return {
        **payload,
        "meta_prior_factored_operator_id": content_id(
            DOMAINS["operator"], payload
        ),
    }


class _PersistentFactoredBellmanV10:
    """Exact-rational H3 interval Bellman values with persistent subproofs."""

    def __init__(self, rank_two_lower: Fraction, rank_two_upper: Fraction) -> None:
        self._rank_two_lower = rank_two_lower
        self._rank_two_upper = rank_two_upper
        self._cache: dict[tuple[tuple[int, ...], str, int], Any] = {}
        self.cache_hits = 0

    def _state_value(
        self,
        rows: v164._LazyOperatorRows,  # noqa: SLF001
        board: tuple[int, ...],
        status_value: str,
        remaining: int,
    ) -> Any:
        representative = Swipe2048State(board, Swipe2048Status(status_value))
        key = (board, status_value, remaining)
        cached = self._cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            value = model._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(), None
            )
            self._cache[key] = value
            return value
        if representative.status is Swipe2048Status.LOST:
            value = model._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
            self._cache[key] = value
            return value
        best = None
        for action, row_key in v163._action_row_keys(  # noqa: SLF001
            representative.board, representative.status.value
        ):
            candidate = self._action_value(
                rows, representative, action, row_key, remaining
            )
            if model._better_robust(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            best = model._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
        self._cache[key] = best
        return best

    def _action_value(
        self,
        rows: v164._LazyOperatorRows,  # noqa: SLF001
        representative: Swipe2048State,
        action: Swipe2048Action,
        row_key: tuple[tuple[int, ...], str, str],
        remaining: int,
    ) -> Any:
        row = rows.get(row_key)
        if row is None:
            _fail("factored operator returned no row")
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
                model._box_expectation_extreme(  # noqa: SLF001
                    tuple(lower_values), lower_bounds, upper_bounds, maximize=False
                ),
                model._box_expectation_extreme(  # noqa: SLF001
                    tuple(upper_values), lower_bounds, upper_bounds, maximize=True
                ),
                model._box_expectation_extreme(  # noqa: SLF001
                    tuple(loss_values), lower_bounds, upper_bounds, maximize=True
                ),
            )
        lower_endpoints = tuple(
            (1 - probability) * by_rank[1][0]
            + probability * by_rank[2][0]
            for probability in (self._rank_two_lower, self._rank_two_upper)
        )
        upper_endpoints = tuple(
            (1 - probability) * by_rank[1][1]
            + probability * by_rank[2][1]
            for probability in (self._rank_two_lower, self._rank_two_upper)
        )
        loss_endpoints = tuple(
            (1 - probability) * by_rank[1][2]
            + probability * by_rank[2][2]
            for probability in (self._rank_two_lower, self._rank_two_upper)
        )
        known_upper = max(upper_endpoints)
        unknown_score_upper = model._unknown_spawn_score_upper(  # noqa: SLF001
            representative,
            merge_score=row.outcomes[0].merge_score,
            remaining=remaining,
        )
        return model._RobustValueV1(  # noqa: SLF001
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
        self, rows: v164._LazyOperatorRows, root: Swipe2048State  # noqa: SLF001
    ) -> tuple[Any, ...]:
        representative, transform = model.canonicalize_state_v1(root)
        output = []
        for action, row_key in v163._action_row_keys(  # noqa: SLF001
            representative.board, representative.status.value
        ):
            value = self._action_value(
                rows, representative, action, row_key, pre.PLANNING_HORIZON
            )
            lifted = model.transform_action_v1(
                action, model.inverse_d4(transform)
            )
            output.append(
                model._RobustValueV1(  # noqa: SLF001
                    value.score_lower,
                    value.score_upper,
                    value.loss_upper,
                    lifted,
                )
            )
        return tuple(
            sorted(output, key=lambda row: ACTION_ORDER.index(row.selected_action))
        )


def _certificate_document(
    arm: str,
    operator_id: str,
    state: Swipe2048State,
    rows: v164._LazyOperatorRows,  # noqa: SLF001
    bellman: _PersistentFactoredBellmanV10,
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
        _fail("strict interval dominance produced multiple actions")
    selected = None if not eligible else eligible[0].selected_action
    payload = {
        "schema": "acfqp.standard_2048_meta_prior_route_certificate.v10",
        "schema_version": SCHEMA_VERSION,
        "meta_prior_route_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "meta_prior_factored_operator_id": operator_id,
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
        "ground_transition_kernel_accessed": False,
        "cold_direct_accessed": False,
        "target_observation_accessed": False,
    }
    return {
        **payload,
        "meta_prior_route_certificate_id": content_id(
            DOMAINS["certificate"], payload
        ),
    }


def _exact_equivalence(
    action: Swipe2048Action, exact: dict[str, Any], state: Swipe2048State
) -> tuple[bool, dict[str, Any] | None]:
    if action.value == exact["selected_action"]:
        return True, None
    forced = model._direct_plan_forced_action(  # noqa: SLF001
        state, pre.PLANNING_HORIZON, action
    )
    equivalent = (
        _fraction(forced["expected_merge_score"])
        == _fraction(exact["expected_merge_score"])
        and _fraction(forced["loss_probability_within_horizon"])
        == _fraction(exact["loss_probability_within_horizon"])
    )
    return equivalent, forced


def _episode_task(
    task: tuple[
        str,
        int,
        tuple[int, ...],
        str,
        dict[str, Any],
        dict[int, tuple[tuple[Fraction, Fraction], ...]],
        Fraction,
        Fraction,
    ],
) -> dict[str, Any]:
    arm, episode_index, board, seed, operator, bounds, rank_lower, rank_upper = task
    state = state_from_board_v1(board)
    initial_state = _state_document(state)
    rows = v164._LazyOperatorRows(  # noqa: SLF001
        operator["meta_prior_factored_operator_id"],
        operator["meta_prior_factored_operator_id"],
        bounds,
        operator["meta_prior_factored_operator_id"],
    )
    bellman = _PersistentFactoredBellmanV10(rank_lower, rank_upper)
    decisions = []
    for decision_index in range(pre.DECISIONS_PER_EPISODE):
        certificate = _certificate_document(
            arm,
            operator["meta_prior_factored_operator_id"],
            state,
            rows,
            bellman,
        )
        route_frozen_before_ground = True
        exact = model._direct_plan(state, pre.PLANNING_HORIZON)  # noqa: SLF001
        if certificate["selected_action"] is None:
            selected = Swipe2048Action(exact["selected_action"])
            route = "COLD_EXACT_DIRECT_GROUND_FALLBACK"
            matched_lane = "OPERATIONAL_FALLBACK"
        else:
            selected = Swipe2048Action(certificate["selected_action"])
            route = "ABSTRACT_CERTIFIED"
            matched_lane = "EVALUATION_ONLY"
        equivalent, forced = _exact_equivalence(selected, exact, state)
        outcomes = step_v1(state, selected)
        outcome, tape_digest = select_seeded_outcome_v1(
            outcomes, seed=seed, decision_index=decision_index
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
                        "meta_prior_route_certificate_id"
                    ],
                    "route_frozen_before_ground_access": route_frozen_before_ground,
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
    fallback_count = len(decisions) - abstract_count
    payload = {
        "schema": "acfqp.standard_2048_meta_prior_route_episode.v10",
        "schema_version": SCHEMA_VERSION,
        "meta_prior_route_preregistration_id": PREREGISTRATION_ID,
        "arm": arm,
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "decisions": decisions,
        "decision_count": len(decisions),
        "abstract_route_count": abstract_count,
        "fallback_route_count": fallback_count,
        "virtual_row_invocation_count": rows.invocation_count,
        "virtual_support_outcome_evaluation_count": (
            rows.support_outcome_evaluation_count
        ),
        "closed_subproof_cache_hit_count": bellman.cache_hits,
        "serialized_state_action_row_count": 0,
        "persistent_state_action_row_count": 0,
        "final_state": _state_document(state),
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
    }
    return {
        **payload,
        "meta_prior_route_episode_id": content_id(DOMAINS["episode"], payload),
    }


def _arm_document(
    arm: str,
    operator: dict[str, Any],
    episodes: list[dict[str, Any]],
) -> dict[str, Any]:
    decisions = [row for episode in episodes for row in episode["decisions"]]
    abstract_count = sum(
        row["route_decision"]["route"] == "ABSTRACT_CERTIFIED"
        for row in decisions
    )
    fallback_count = len(decisions) - abstract_count
    operational_fallback_rows = sum(
        row["matched_cold_direct"]["ground_state_action_row_count"]
        for row in decisions
        if row["matched_direct_lane"] == "OPERATIONAL_FALLBACK"
    )
    operational_fallback_outcomes = sum(
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
    return {
        "arm": arm,
        "factored_operator": operator,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "offline_transition_observation_count": operator["offline_evidence"][
            "unique_offline_transition_observation_count"
        ],
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
        "operational_fallback_ground_state_action_row_count": (
            operational_fallback_rows
        ),
        "operational_fallback_ground_outcome_count": (
            operational_fallback_outcomes
        ),
        "evaluation_cold_direct_ground_state_action_row_count": evaluation_rows,
        "evaluation_cold_direct_ground_outcome_count": evaluation_outcomes,
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["selected_action_exact_value_and_loss_equivalent"]
            for row in decisions
        ),
        "all_abstract_routes_have_strict_root_dominance_certificate": all(
            row["route_decision"]["route"] != "ABSTRACT_CERTIFIED"
            or row["certificate"]["status"]
            == "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE"
            for row in decisions
        ),
        "fallback_only_after_certificate_failure": all(
            row["route_decision"]["fallback_only_after_certificate_failure"]
            for row in decisions
        ),
    }


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    preregistration = (
        pre.freeze_standard_2048_meta_prior_route_preregistration_v10()
    )
    arm_inputs = {}
    tasks = []
    for arm in ("STRUCTURAL_META_PRIOR", "STRICT_OBSERVATION_ONLY"):
        evidence, bounds, rank_lower, rank_upper = _observation_evidence(arm)
        operator = _operator_document(arm, evidence)
        arm_inputs[arm] = operator, bounds, rank_lower, rank_upper
        for episode_index, (board, seed) in enumerate(
            zip(
                pre.PREREGISTERED_INITIAL_BOARDS,
                pre.PREREGISTERED_EPISODE_SEEDS,
                strict=True,
            )
        ):
            tasks.append(
                (
                    arm,
                    episode_index,
                    board,
                    seed,
                    operator,
                    bounds,
                    rank_lower,
                    rank_upper,
                )
            )
    episode_results = {}
    with ProcessPoolExecutor(max_workers=EPISODE_PROCESS_COUNT) as executor:
        for episode in executor.map(_episode_task, tasks, chunksize=1):
            episode_results[(episode["arm"], episode["episode_index"])] = episode
    arms = {}
    for arm in ("STRUCTURAL_META_PRIOR", "STRICT_OBSERVATION_ONLY"):
        operator = arm_inputs[arm][0]
        episodes = [
            episode_results[(arm, index)]
            for index in range(len(pre.PREREGISTERED_INITIAL_BOARDS))
        ]
        arms[arm] = _arm_document(arm, operator, episodes)
    meta = arms["STRUCTURAL_META_PRIOR"]
    observed = arms["STRICT_OBSERVATION_ONLY"]
    sample_saving = (
        observed["offline_transition_observation_count"]
        - meta["offline_transition_observation_count"]
    )
    required_passed = (
        sample_saving > 0
        and meta["all_selected_actions_exact_value_and_loss_equivalent"]
        and observed["all_selected_actions_exact_value_and_loss_equivalent"]
        and meta[
            "all_abstract_routes_have_strict_root_dominance_certificate"
        ]
        and observed[
            "all_abstract_routes_have_strict_root_dominance_certificate"
        ]
        and meta["fallback_only_after_certificate_failure"]
        and observed["fallback_only_after_certificate_failure"]
    )
    payload = {
        "schema": "acfqp.standard_2048_meta_prior_route_campaign.v10",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "meta_prior_route_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "structural_meta_prior_arm": meta,
        "strict_observation_only_arm": observed,
        "arm_attributed_offline_transition_observation_count": {
            "structural_meta_prior": meta[
                "offline_transition_observation_count"
            ],
            "strict_observation_only": observed[
                "offline_transition_observation_count"
            ],
        },
        "shared_unique_offline_transition_observation_count": observed[
            "offline_transition_observation_count"
        ],
        "meta_prior_offline_observation_saving": sample_saving,
        "meta_prior_offline_sample_tax_reduced": sample_saving > 0,
        "all_required_preregistered_conditions_passed": required_passed,
        "registered_sample_tax_outcome": (
            "POSITIVE_REGISTERED_CONDITIONAL_SAMPLE_TAX_RESULT"
            if required_passed
            else "NEGATIVE_REGISTERED_CONDITIONAL_SAMPLE_TAX_RESULT"
        ),
        "fallback_and_factored_compute_axes_reported_separately": True,
        "uniform_exchangeability_proven_by_finite_samples": False,
        "conditional_registered_shared_law_family_only": True,
        "physical_iid_randomness_claimed": False,
        "total_operational_work_saving_claimed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "meta_prior_route_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    if document["meta_prior_route_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("registered meta-prior route campaign identity changed")
    expected_fields = (
        (meta["abstract_route_count"], EXPECTED_META_ABSTRACT_ROUTE_COUNT),
        (meta["fallback_route_count"], EXPECTED_META_FALLBACK_ROUTE_COUNT),
        (observed["abstract_route_count"], EXPECTED_OBSERVATION_ABSTRACT_ROUTE_COUNT),
        (observed["fallback_route_count"], EXPECTED_OBSERVATION_FALLBACK_ROUTE_COUNT),
        (sample_saving, EXPECTED_OFFLINE_OBSERVATION_SAVING),
        (
            meta["factored_virtual_row_invocation_count"],
            EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT_PER_ARM,
        ),
        (
            observed["factored_virtual_row_invocation_count"],
            EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT_PER_ARM,
        ),
        (
            meta["factored_virtual_support_outcome_evaluation_count"],
            EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT_PER_ARM,
        ),
        (
            observed["factored_virtual_support_outcome_evaluation_count"],
            EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT_PER_ARM,
        ),
        (
            meta["operational_fallback_ground_state_action_row_count"],
            EXPECTED_META_OPERATIONAL_FALLBACK_ROW_COUNT,
        ),
        (
            observed["operational_fallback_ground_state_action_row_count"],
            EXPECTED_OBSERVATION_OPERATIONAL_FALLBACK_ROW_COUNT,
        ),
    )
    if any(actual != expected for actual, expected in expected_fields):
        _fail("registered meta-prior route campaign result changed")
    return document


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048MetaPriorRouteCampaignV10:
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
        ):
            _fail("campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "meta_prior_route_campaign_id"
        }
        if (
            document.get("meta_prior_route_campaign_id") != self.campaign_id
            or content_id(DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("meta-prior route campaign is not an object")
        return document


def run_standard_2048_meta_prior_route_campaign_v10(
) -> Standard2048MetaPriorRouteCampaignV10:
    document = _campaign_document()
    return Standard2048MetaPriorRouteCampaignV10(
        _ISSUER,
        canonical_json_bytes(document),
        document["meta_prior_route_campaign_id"],
    )


__all__ = (
    "ConstructionK7Standard2048MetaPriorRouteCampaignV10Error",
    "DOMAINS",
    "EPISODE_PROCESS_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT_PER_ARM",
    "EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT_PER_ARM",
    "EXPECTED_META_ABSTRACT_ROUTE_COUNT",
    "EXPECTED_META_FALLBACK_ROUTE_COUNT",
    "EXPECTED_META_OPERATIONAL_FALLBACK_ROW_COUNT",
    "EXPECTED_OBSERVATION_ABSTRACT_ROUTE_COUNT",
    "EXPECTED_OBSERVATION_FALLBACK_ROUTE_COUNT",
    "EXPECTED_OBSERVATION_OPERATIONAL_FALLBACK_ROW_COUNT",
    "EXPECTED_OFFLINE_OBSERVATION_SAVING",
    "PREREGISTRATION_ID",
    "Standard2048MetaPriorRouteCampaignV10",
    "run_standard_2048_meta_prior_route_campaign_v10",
)
