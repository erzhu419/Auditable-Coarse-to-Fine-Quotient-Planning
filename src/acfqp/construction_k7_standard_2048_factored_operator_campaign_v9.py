"""Fresh H3 campaign for a reusable, lazily evaluated spawn operator."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_factored_operator_preregistration_v9 as pre
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as model
from acfqp import construction_k7_standard_2048_h3_reuse_campaign_v8 as v163
from acfqp import construction_k7_standard_2048_targeted_acquisition_campaign_v7 as v161
from acfqp.domains.standard_2048 import (
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    swipe_board_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROPOSED_CONTRACT_VERSION = pre.PROPOSED_CONTRACT_VERSION
PROFILE_KEY = pre.PROFILE_KEY
PREREGISTRATION_ID = pre.PREREGISTRATION_ID
PREREGISTRATION_COMMIT = "2f6ec86"
DOMAINS = pre.FUTURE_DOMAINS
CONTROL_PROCESS_COUNT = 16
EXPECTED_CAMPAIGN_ID = (
    "48c920ec560529c433b81cb24c784f52b67e6ce2acf9ad746edda8b5635e40d8"
)
EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT = 105434
EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_EVALUATION_COUNT = 2359184
EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT = 2192777
EXPECTED_EXPLICIT_MATERIALIZED_ROW_COUNT = 178268
EXPECTED_EXPLICIT_MATERIALIZED_SUPPORT_OUTCOME_COUNT = 4031972
EXPECTED_EXACT_LABEL_IDENTICAL_DECISION_COUNT = 21
EXPECTED_EXACT_VALUE_EQUIVALENT_DECISION_COUNT = 31
EXPECTED_EXACT_QUALITY_MISMATCH_COUNT = 1


class ConstructionK7Standard2048FactoredOperatorCampaignV9Error(ValueError):
    """A factored operator, matched control, target tape, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FactoredOperatorCampaignV9Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
    ):
        _fail("rational document changed")
    return Fraction(value["numerator"], value["denominator"])


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@dataclass(frozen=True, slots=True)
class _FactoredRowView:
    outcomes: tuple[Any, ...]
    support_outcome_count: int
    unknown_support_mass_upper: Fraction
    row_id: str


@lru_cache(maxsize=None)
def _canonical_spawn_state(board: tuple[int, ...]) -> Swipe2048State:
    return canonicalize_state_v1(state_from_board_v1(board))[0]


@lru_cache(maxsize=None)
def _swipe(
    board: tuple[int, ...], action: Swipe2048Action
) -> tuple[tuple[int, ...], int, bool]:
    return swipe_board_v1(board, action)


class _LazyOperatorRows:
    """Generate one virtual transition row and immediately discard it."""

    def __init__(
        self,
        interval_id: str,
        proposal_id: str,
        bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
        operator_id: str,
    ) -> None:
        self._interval_id = interval_id
        self._proposal_id = proposal_id
        self._bounds = bounds
        self._operator_id = operator_id
        self.invocation_count = 0
        self.support_outcome_evaluation_count = 0

    def get(self, key: tuple[tuple[int, ...], str, str]):
        self.invocation_count += 1
        board, status_value, action_value = key
        state = Swipe2048State(board, Swipe2048Status(status_value))
        action = Swipe2048Action(action_value)
        moved, merge_score, changed = _swipe(state.board, action)
        if not changed:
            _fail("factored operator received a nonchanging action")
        empty_cells = tuple(index for index, rank in enumerate(moved) if rank == 0)
        ordinals = model.support_ordinals_from_proposal_v2(
            support_proposal_id=self._proposal_id,
            selected_support_rule=model.SELECTED_SUPPORT_RULE,
            empty_count=len(empty_cells),
        )
        position_bounds = self._bounds.get(len(empty_cells))
        if position_bounds is None or len(position_bounds) != len(empty_cells):
            _fail("factored operator interval cardinality changed")
        grouped = {}
        for ordinal in ordinals:
            for rank in (1, 2):
                spawned = list(moved)
                spawned[empty_cells[ordinal]] = rank
                representative = _canonical_spawn_state(tuple(spawned))
                lower, upper = position_bounds[ordinal]
                group_key = (
                    rank,
                    ordinal,
                    representative.board,
                    representative.status.value,
                    merge_score,
                    lower,
                    upper,
                )
                grouped[group_key] = grouped.get(group_key, 0) + 1
        outcomes = tuple(
            model.Standard2048SupportPartialOutcomeV2(
                rank,
                ordinal,
                lower,
                upper,
                Swipe2048State(next_board, Swipe2048Status(next_status)),
                outcome_merge_score,
                count,
            )
            for (
                rank,
                ordinal,
                next_board,
                next_status,
                outcome_merge_score,
                lower,
                upper,
            ), count in sorted(grouped.items())
        )
        support_count = 2 * len(ordinals)
        self.support_outcome_evaluation_count += support_count
        return _FactoredRowView(
            outcomes,
            support_count,
            Fraction(),
            self._operator_id,
        )


def _operator_document(
    source_archive_id: str,
    validation_archive_id: str,
    proposal: dict[str, Any],
    interval: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_factored_spawn_operator.v9",
        "schema_version": SCHEMA_VERSION,
        "factored_operator_preregistration_id": PREREGISTRATION_ID,
        "targeted_source_archive_id": source_archive_id,
        "targeted_validation_archive_id": validation_archive_id,
        "support_proposal_id": proposal["support_proposal_id"],
        "partial_dynamics_interval_id": interval["partial_dynamics_interval_id"],
        "semantics": (
            "SWIPE_THEN_ALL_SORTED_EMPTY_ORDINALS_CROSS_RANKS_WITH_"
            "OBSERVATION_DERIVED_INTERVALS_V1"
        ),
        "deterministic_swipe_known": True,
        "spawn_support_program_observation_derived": True,
        "position_and_rank_intervals_observation_derived": True,
        "unknown_support_mass_within_registered_family": _fdoc(Fraction()),
        "state_action_rows_serialized_or_persisted": False,
        "successors_generated_lazily_inside_bellman_backup": True,
        "conditional_on_registered_support_candidate_family": True,
        "open_ended_operator_invention_claimed": False,
    }
    return {
        **payload,
        "factored_spawn_operator_id": content_id(DOMAINS["operator"], payload),
    }


def _factored_plan(
    rows: _LazyOperatorRows,
    subproofs: v163._PersistentRobustSubproofs,  # noqa: SLF001
    state: Swipe2048State,
    operator_id: str,
) -> dict[str, Any]:
    before_invocations = rows.invocation_count
    before_outcomes = rows.support_outcome_evaluation_count
    before_hits = subproofs.cache_hits
    value, dependencies = subproofs.solve(rows, state)
    if value.selected_action is None:
        _fail("active factored root produced no action")
    payload = {
        "schema": "acfqp.standard_2048_factored_h3_plan.v9",
        "schema_version": SCHEMA_VERSION,
        "factored_spawn_operator_id": operator_id,
        "root_state": _state_document(state),
        "horizon": pre.PLANNING_HORIZON,
        "objective": "MAX_INTERVAL_ROBUST_SCORE_THEN_MIN_LOSS_V2",
        "selected_action": value.selected_action.value,
        "robust_score_lower": _fdoc(value.score_lower),
        "robust_score_upper": _fdoc(value.score_upper),
        "robust_loss_probability_upper": _fdoc(value.loss_upper),
        "virtual_row_invocation_count": rows.invocation_count - before_invocations,
        "virtual_support_outcome_evaluation_count": (
            rows.support_outcome_evaluation_count - before_outcomes
        ),
        "closed_subproof_cache_hit_count": subproofs.cache_hits - before_hits,
        "serialized_state_action_row_count": 0,
        "persistent_state_action_row_count": 0,
        "ephemeral_dependency_row_id_count": len(dependencies),
        "ground_transition_kernel_accessed": False,
        "target_observation_accessed_before_plan_freeze": False,
    }
    return payload


def _explicit_control(
    state: Swipe2048State,
    interval_id: str,
    proposal_id: str,
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_lower: Fraction,
    rank_upper: Fraction,
) -> dict[str, Any]:
    rows: dict = {}
    for _ in range(pre.PLANNING_HORIZON + 1):
        frontier = v163._missing_frontier(rows, state)  # noqa: SLF001
        if not frontier:
            break
        for key in frontier:
            rows[key] = v163._materialize_row(  # noqa: SLF001
                key, interval_id, proposal_id, bounds
            )
    if v163._missing_frontier(rows, state):  # noqa: SLF001
        _fail("explicit H3 control frontier did not close")
    value, _ = model._solve_robust(  # noqa: SLF001
        rows,
        state,
        pre.PLANNING_HORIZON,
        rank_lower,
        rank_upper,
    )
    if value.selected_action is None:
        _fail("explicit H3 control produced no action")
    return {
        "selected_action": value.selected_action.value,
        "robust_score_lower": _fdoc(value.score_lower),
        "robust_score_upper": _fdoc(value.score_upper),
        "robust_loss_probability_upper": _fdoc(value.loss_upper),
        "materialized_state_action_row_count": len(rows),
        "materialized_support_outcome_count": sum(
            row.support_outcome_count for row in rows.values()
        ),
        "evaluation_control_only": True,
        "route_or_target_authority": False,
    }


def _control_task(
    task: tuple[
        int,
        int,
        tuple[int, ...],
        str,
        str,
        str,
        dict[int, tuple[tuple[Fraction, Fraction], ...]],
        Fraction,
        Fraction,
        str,
    ],
) -> tuple[int, int, dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    (
        episode_index,
        decision_index,
        board,
        status,
        interval_id,
        proposal_id,
        bounds,
        rank_lower,
        rank_upper,
        factored_action,
    ) = task
    state = Swipe2048State(board, Swipe2048Status(status))
    explicit = _explicit_control(
        state,
        interval_id,
        proposal_id,
        bounds,
        rank_lower,
        rank_upper,
    )
    exact = model._direct_plan(state, pre.PLANNING_HORIZON)  # noqa: SLF001
    forced = None
    if exact["selected_action"] != factored_action:
        forced = model._direct_plan_forced_action(  # noqa: SLF001
            state,
            pre.PLANNING_HORIZON,
            Swipe2048Action(factored_action),
        )
    return episode_index, decision_index, explicit, exact, forced


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_factored_operator_preregistration_v9()
    v161_result = v161.run_standard_2048_targeted_acquisition_campaign_v7()
    v161_document = v161_result.to_document()
    source_archive = v161_document["targeted_source_archive"]
    validation_archive = v161_document["targeted_validation_archive"]
    source_id = source_archive["targeted_source_archive_id"]
    validation_id = validation_archive["targeted_validation_archive_id"]
    proposal = v163._support_proposal(source_id, validation_id)  # noqa: SLF001
    interval, bounds, rank_lower, rank_upper = v163._interval_binding(  # noqa: SLF001
        source_id, validation_id, proposal["support_proposal_id"]
    )
    operator = _operator_document(
        source_id, validation_id, proposal, interval
    )
    lazy_rows = _LazyOperatorRows(
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
        operator["factored_spawn_operator_id"],
    )
    subproofs = v163._PersistentRobustSubproofs(  # noqa: SLF001
        rank_lower, rank_upper
    )
    episode_drafts: list[dict[str, Any]] = []
    control_tasks = []
    for episode_index, (board, seed) in enumerate(
        zip(
            pre.PREREGISTERED_INITIAL_BOARDS,
            pre.PREREGISTERED_EPISODE_SEEDS,
            strict=True,
        )
    ):
        state = state_from_board_v1(board)
        initial_state = _state_document(state)
        decisions = []
        for decision_index in range(pre.DECISIONS_PER_EPISODE):
            plan = _factored_plan(
                lazy_rows,
                subproofs,
                state,
                operator["factored_spawn_operator_id"],
            )
            selected = Swipe2048Action(plan["selected_action"])
            control_tasks.append(
                (
                    episode_index,
                    decision_index,
                    state.board,
                    state.status.value,
                    interval["partial_dynamics_interval_id"],
                    proposal["support_proposal_id"],
                    bounds,
                    rank_lower,
                    rank_upper,
                    selected.value,
                )
            )
            outcome, tape_digest = select_seeded_outcome_v1(
                step_v1(state, selected),
                seed=seed,
                decision_index=decision_index,
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "state_before_decision": _state_document(state),
                    "factored_plan": plan,
                    "executed_target_transition": {
                        "selected_action": selected.value,
                        "spawn_tape_digest": tape_digest,
                        "spawned_cell": outcome.spawned_cell,
                        "spawned_rank": outcome.spawned_rank,
                        "merge_score": outcome.merge_score,
                        "successor_state": _state_document(outcome.next_state),
                        "target_observation_not_used_before_plan_freeze": True,
                    },
                }
            )
            state = outcome.next_state
        episode_drafts.append(
            {
                "schema": "acfqp.standard_2048_factored_episode.v9",
                "schema_version": SCHEMA_VERSION,
                "factored_operator_preregistration_id": PREREGISTRATION_ID,
                "episode_index": episode_index,
                "execution_seed": seed,
                "initial_state": initial_state,
                "decisions": decisions,
                "decision_count": len(decisions),
                "final_state": _state_document(state),
            }
        )

    controls = {}
    with ProcessPoolExecutor(max_workers=CONTROL_PROCESS_COUNT) as executor:
        for episode_index, decision_index, explicit, exact, forced in executor.map(
            _control_task, control_tasks, chunksize=1
        ):
            controls[(episode_index, decision_index)] = (
                explicit,
                exact,
                forced,
            )
    if len(controls) != len(control_tasks):
        _fail("matched control cardinality changed")

    episodes = []
    factored_explicit_mismatches = []
    exact_quality_mismatches = []
    exact_label_identical_count = 0
    exact_value_equivalent_count = 0
    total_explicit_rows = 0
    total_explicit_outcomes = 0
    total_exact_rows = 0
    total_exact_outcomes = 0
    for episode in episode_drafts:
        episode_index = episode["episode_index"]
        for decision in episode["decisions"]:
            decision_index = decision["decision_index"]
            explicit, exact, forced = controls[(episode_index, decision_index)]
            plan = decision["factored_plan"]
            factored_explicit_equal = (
                plan["selected_action"] == explicit["selected_action"]
                and plan["robust_score_lower"] == explicit["robust_score_lower"]
                and plan["robust_score_upper"] == explicit["robust_score_upper"]
                and plan["robust_loss_probability_upper"]
                == explicit["robust_loss_probability_upper"]
            )
            if not factored_explicit_equal:
                factored_explicit_mismatches.append(
                    {
                        "episode_index": episode_index,
                        "decision_index": decision_index,
                        "factored_plan": plan,
                        "explicit_control": explicit,
                    }
                )
            label_identical = plan["selected_action"] == exact["selected_action"]
            value_equivalent = label_identical
            if not label_identical:
                if forced is None:
                    _fail("forced exact quality control is missing")
                value_equivalent = (
                    _fraction(forced["expected_merge_score"])
                    == _fraction(exact["expected_merge_score"])
                    and _fraction(forced["loss_probability_within_horizon"])
                    == _fraction(exact["loss_probability_within_horizon"])
                )
            if label_identical:
                exact_label_identical_count += 1
            if value_equivalent:
                exact_value_equivalent_count += 1
            else:
                exact_quality_mismatches.append(
                    {
                        "episode_index": episode_index,
                        "decision_index": decision_index,
                        "factored_action": plan["selected_action"],
                        "exact_action": exact["selected_action"],
                        "forced_factored_action_exact_evaluation": forced,
                    }
                )
            decision["matched_explicit_row_control"] = explicit
            decision["matched_cold_direct"] = exact
            decision["forced_factored_action_exact_evaluation"] = forced
            decision["factored_and_explicit_semantics_identical"] = (
                factored_explicit_equal
            )
            decision["factored_action_exact_value_and_loss_equivalent"] = (
                value_equivalent
            )
            decision["factored_action_label_identical_to_exact"] = label_identical
            total_explicit_rows += explicit["materialized_state_action_row_count"]
            total_explicit_outcomes += explicit[
                "materialized_support_outcome_count"
            ]
            total_exact_rows += exact["ground_state_action_row_count"]
            total_exact_outcomes += exact["ground_outcome_count"]
        episodes.append(
            {
                **episode,
                "factored_episode_id": content_id(DOMAINS["episode"], episode),
            }
        )

    required_passed = (
        not factored_explicit_mismatches
        and lazy_rows.invocation_count >= 1
    )
    payload = {
        "schema": "acfqp.standard_2048_factored_operator_campaign.v9",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "factored_operator_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "predecessor_v161_campaign_id": v161_result.campaign_id,
        "reused_targeted_source_archive": source_archive,
        "reused_targeted_validation_archive": validation_archive,
        "targeted_support_proposal": proposal,
        "targeted_interval_binding": interval,
        "factored_spawn_operator": operator,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(control_tasks),
        "reused_offline_observation_count": interval[
            "unique_offline_transition_observation_count"
        ],
        "additional_offline_observation_count": 0,
        "factored_operational_serialized_state_action_row_count": 0,
        "factored_operational_persistent_state_action_row_count": 0,
        "factored_virtual_row_invocation_count": lazy_rows.invocation_count,
        "factored_virtual_support_outcome_evaluation_count": (
            lazy_rows.support_outcome_evaluation_count
        ),
        "closed_bellman_subproof_cache_hit_count": subproofs.cache_hits,
        "explicit_control_materialized_state_action_row_count": total_explicit_rows,
        "explicit_control_materialized_support_outcome_count": (
            total_explicit_outcomes
        ),
        "exact_control_ground_state_action_row_count": total_exact_rows,
        "exact_control_ground_outcome_count": total_exact_outcomes,
        "factored_explicit_mismatch_records": factored_explicit_mismatches,
        "factored_explicit_mismatch_count": len(factored_explicit_mismatches),
        "all_factored_and_explicit_semantics_identical": (
            not factored_explicit_mismatches
        ),
        "exact_label_identical_decision_count": exact_label_identical_count,
        "exact_value_and_loss_equivalent_decision_count": (
            exact_value_equivalent_count
        ),
        "exact_quality_mismatch_records": exact_quality_mismatches,
        "exact_quality_mismatch_count": len(exact_quality_mismatches),
        "required_positive_conditions_passed": required_passed,
        "registered_representation_tax_outcome": (
            "POSITIVE_REGISTERED_LOCAL_RESULT"
            if required_passed
            else "NEGATIVE_REGISTERED_LOCAL_RESULT"
        ),
        "quality_outcome_reported_separately": True,
        "cold_ground_fallback_preserved": True,
        "operator_reused_across_all_decisions": True,
        "physical_iid_randomness_claimed": False,
        "conditional_registered_support_family_only": True,
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
        "factored_operator_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    expected_fields = {
        "factored_virtual_row_invocation_count": (
            EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT
        ),
        "factored_virtual_support_outcome_evaluation_count": (
            EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_EVALUATION_COUNT
        ),
        "closed_bellman_subproof_cache_hit_count": (
            EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT
        ),
        "explicit_control_materialized_state_action_row_count": (
            EXPECTED_EXPLICIT_MATERIALIZED_ROW_COUNT
        ),
        "explicit_control_materialized_support_outcome_count": (
            EXPECTED_EXPLICIT_MATERIALIZED_SUPPORT_OUTCOME_COUNT
        ),
        "exact_label_identical_decision_count": (
            EXPECTED_EXACT_LABEL_IDENTICAL_DECISION_COUNT
        ),
        "exact_value_and_loss_equivalent_decision_count": (
            EXPECTED_EXACT_VALUE_EQUIVALENT_DECISION_COUNT
        ),
        "exact_quality_mismatch_count": EXPECTED_EXACT_QUALITY_MISMATCH_COUNT,
    }
    if document["factored_operator_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("registered factored campaign identity changed")
    if any(document[key] != value for key, value in expected_fields.items()):
        _fail("registered factored campaign result changed")
    return document


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FactoredOperatorCampaignV9:
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
            if key != "factored_operator_campaign_id"
        }
        if (
            document.get("factored_operator_campaign_id") != self.campaign_id
            or content_id(DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("factored campaign root is not an object")
        return document


def run_standard_2048_factored_operator_campaign_v9(
) -> Standard2048FactoredOperatorCampaignV9:
    document = _campaign_document()
    return Standard2048FactoredOperatorCampaignV9(
        _ISSUER,
        canonical_json_bytes(document),
        document["factored_operator_campaign_id"],
    )


__all__ = (
    "ConstructionK7Standard2048FactoredOperatorCampaignV9Error",
    "CONTROL_PROCESS_COUNT",
    "DOMAINS",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT",
    "EXPECTED_EXACT_LABEL_IDENTICAL_DECISION_COUNT",
    "EXPECTED_EXACT_QUALITY_MISMATCH_COUNT",
    "EXPECTED_EXACT_VALUE_EQUIVALENT_DECISION_COUNT",
    "EXPECTED_EXPLICIT_MATERIALIZED_ROW_COUNT",
    "EXPECTED_EXPLICIT_MATERIALIZED_SUPPORT_OUTCOME_COUNT",
    "EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT",
    "EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_EVALUATION_COUNT",
    "PREREGISTRATION_ID",
    "Standard2048FactoredOperatorCampaignV9",
    "run_standard_2048_factored_operator_campaign_v9",
)
