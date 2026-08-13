"""Run preregistered long real-start 2048 reuse with identity no-transfer."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_factored_operator_campaign_v9 as v164
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as model
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as pre
from acfqp import construction_k7_standard_2048_meta_prior_route_campaign_v10 as v167
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
PREREGISTRATION_COMMIT = "c953c98"
DOMAINS = pre.FUTURE_DOMAINS
EPISODE_PROCESS_COUNT = 4
EXPECTED_CAMPAIGN_ID = (
    "158dfab7d25c70d46aabc98620d4bccd55ff5f2a39c354aa6ca918346e191fdd"
)
EXPECTED_DECISION_COUNT = 128
EXPECTED_ABSTRACT_ROUTE_COUNT = 49
EXPECTED_FALLBACK_ROUTE_COUNT = 79
EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT = 719879
EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT = 14840614
EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT = 12855414
EXPECTED_OPERATIONAL_FALLBACK_ROW_COUNT = 607858
EXPECTED_OPERATIONAL_FALLBACK_OUTCOME_COUNT = 13268726
EXPECTED_EVALUATION_DIRECT_ROW_COUNT = 349125
EXPECTED_EVALUATION_DIRECT_OUTCOME_COUNT = 7055406
EXPECTED_MAXIMUM_FINAL_BOARD_TILE_RANK = 6


class ConstructionK7Standard2048LongEpisodeCampaignV11Error(ValueError):
    """A dynamics identity, operator, route, target tape, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048LongEpisodeCampaignV11Error(message)


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


def _operator_binding_document() -> tuple[
    dict[str, Any],
    dict[int, tuple[tuple[Fraction, Fraction], ...]],
    Fraction,
    Fraction,
]:
    accepted = pre._dynamics_identity_document("STANDARD_UNIFORM")  # noqa: SLF001
    evidence, bounds, rank_lower, rank_upper = v167._observation_evidence(  # noqa: SLF001
        "STRUCTURAL_META_PRIOR"
    )
    if evidence["unique_offline_transition_observation_count"] != 192:
        _fail("long-episode offline evidence changed")
    payload = {
        "schema": "acfqp.standard_2048_long_operator_binding.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "v167_meta_route_campaign_id": pre.V167_META_ROUTE_CAMPAIGN_ID,
        "accepted_dynamics_identity": accepted,
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


def _ood_no_transfer_document() -> dict[str, Any]:
    accepted = pre._dynamics_identity_document("STANDARD_UNIFORM")  # noqa: SLF001
    candidate = pre._dynamics_identity_document(  # noqa: SLF001
        "OOD_FIRST_EMPTY_BIASED"
    )
    if candidate["dynamics_identity_id"] == accepted["dynamics_identity_id"]:
        _fail("OOD and accepted dynamics identities collapsed")
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


def _certificate_document(
    state: Swipe2048State,
    operator_binding_id: str,
    rows: v164._LazyOperatorRows,  # noqa: SLF001
    bellman: v167._PersistentFactoredBellmanV10,  # noqa: SLF001
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
        _fail("strict dominance produced multiple long-episode actions")
    selected = None if not eligible else eligible[0].selected_action
    payload = {
        "schema": "acfqp.standard_2048_long_route_certificate.v11",
        "schema_version": SCHEMA_VERSION,
        "long_episode_preregistration_id": PREREGISTRATION_ID,
        "long_operator_binding_id": operator_binding_id,
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
    rows = v164._LazyOperatorRows(  # noqa: SLF001
        binding["long_operator_binding_id"],
        binding["long_operator_binding_id"],
        bounds,
        binding["long_operator_binding_id"],
    )
    bellman = v167._PersistentFactoredBellmanV10(  # noqa: SLF001
        rank_lower, rank_upper
    )
    decisions = []
    for decision_index in range(pre.MAXIMUM_DECISIONS_PER_EPISODE):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        certificate = _certificate_document(
            state, binding["long_operator_binding_id"], rows, bellman
        )
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
                    "certificate_id": certificate["long_route_certificate_id"],
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
    fallback_count = len(decisions) - abstract_count
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
        "fallback_route_count": fallback_count,
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
def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_long_episode_preregistration_v11()
    no_transfer = _ood_no_transfer_document()
    if not (
        no_transfer["status"] == "NO_TRANSFER_DYNAMICS_IDENTITY_MISMATCH"
        and no_transfer["operator_accessed"] is False
        and no_transfer["target_execution_performed"] is False
    ):
        _fail("OOD no-transfer state changed")
    binding, bounds, rank_lower, rank_upper = _operator_binding_document()
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
        and all(episode["serialized_state_action_row_count"] == 0 for episode in episodes)
        and all(episode["persistent_state_action_row_count"] == 0 for episode in episodes)
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
        "operational_fallback_ground_state_action_row_count": (
            operational_fallback_rows
        ),
        "operational_fallback_ground_outcome_count": (
            operational_fallback_outcomes
        ),
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
            episode["closure_reason"] == "TERMINAL_STATE" for episode in episodes
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
        _fail("registered long-episode campaign identity changed")
    expected_fields = {
        "decision_count": EXPECTED_DECISION_COUNT,
        "abstract_route_count": EXPECTED_ABSTRACT_ROUTE_COUNT,
        "fallback_route_count": EXPECTED_FALLBACK_ROUTE_COUNT,
        "factored_virtual_row_invocation_count": (
            EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT
        ),
        "factored_virtual_support_outcome_evaluation_count": (
            EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT
        ),
        "closed_subproof_cache_hit_count": (
            EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT
        ),
        "operational_fallback_ground_state_action_row_count": (
            EXPECTED_OPERATIONAL_FALLBACK_ROW_COUNT
        ),
        "operational_fallback_ground_outcome_count": (
            EXPECTED_OPERATIONAL_FALLBACK_OUTCOME_COUNT
        ),
        "evaluation_cold_direct_ground_state_action_row_count": (
            EXPECTED_EVALUATION_DIRECT_ROW_COUNT
        ),
        "evaluation_cold_direct_ground_outcome_count": (
            EXPECTED_EVALUATION_DIRECT_OUTCOME_COUNT
        ),
        "maximum_final_board_tile_rank": EXPECTED_MAXIMUM_FINAL_BOARD_TILE_RANK,
    }
    if any(document[key] != value for key, value in expected_fields.items()):
        _fail("registered long-episode campaign result changed")
    return document


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048LongEpisodeCampaignV11:
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
            if key != "long_episode_campaign_id"
        }
        if (
            document.get("long_episode_campaign_id") != self.campaign_id
            or content_id(DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("long-episode campaign is not an object")
        return document


def run_standard_2048_long_episode_campaign_v11(
) -> Standard2048LongEpisodeCampaignV11:
    document = _campaign_document()
    return Standard2048LongEpisodeCampaignV11(
        _ISSUER,
        canonical_json_bytes(document),
        document["long_episode_campaign_id"],
    )


__all__ = (
    "ConstructionK7Standard2048LongEpisodeCampaignV11Error",
    "DOMAINS",
    "EPISODE_PROCESS_COUNT",
    "EXPECTED_ABSTRACT_ROUTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT",
    "EXPECTED_DECISION_COUNT",
    "EXPECTED_EVALUATION_DIRECT_OUTCOME_COUNT",
    "EXPECTED_EVALUATION_DIRECT_ROW_COUNT",
    "EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT",
    "EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT",
    "EXPECTED_FALLBACK_ROUTE_COUNT",
    "EXPECTED_MAXIMUM_FINAL_BOARD_TILE_RANK",
    "EXPECTED_OPERATIONAL_FALLBACK_OUTCOME_COUNT",
    "EXPECTED_OPERATIONAL_FALLBACK_ROW_COUNT",
    "PREREGISTRATION_ID",
    "Standard2048LongEpisodeCampaignV11",
    "run_standard_2048_long_episode_campaign_v11",
)
