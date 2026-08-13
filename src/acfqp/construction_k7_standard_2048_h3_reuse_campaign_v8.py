"""H=3 planning over the targeted statistical model with local row recovery."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as model
from acfqp import construction_k7_standard_2048_h3_reuse_preregistration_v8 as pre
from acfqp import construction_k7_standard_2048_targeted_acquisition_campaign_v7 as targeted
from acfqp.domains.standard_2048 import (
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
PREREGISTRATION_ID = "5fa947d68b0e34f1fc4a14166b3be0510dade2d321d13d2093b0c109e0ae2f76"
PREREGISTRATION_COMMIT = "99f249b"
DOMAINS = pre.FUTURE_DOMAINS
MATCHED_DIRECT_PROCESS_COUNT = 16
EXPECTED_CAMPAIGN_ID = (
    "e4cd9db57964ace8ba639a41fb76acda8c7e994a02de1e3e0bfa642fe5300b4e"
)
EXPECTED_PARTIAL_ROW_COUNT = 63135
EXPECTED_SUPPORT_OUTCOME_COUNT = 1447682
EXPECTED_EXACT_EQUIVALENT_DECISION_COUNT = 31
EXPECTED_MISMATCH_COUNT = 1


class ConstructionK7Standard2048H3ReuseCampaignV8Error(ValueError):
    """A targeted interval, partial row, recovery, plan, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048H3ReuseCampaignV8Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_document(state: Any) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


@lru_cache(maxsize=None)
def _legal_actions(board: tuple[int, ...]) -> tuple[Swipe2048Action, ...]:
    return model.legal_actions_v1(board)


@lru_cache(maxsize=None)
def _action_row_keys(
    board: tuple[int, ...], status_value: str
) -> tuple[
    tuple[Swipe2048Action, tuple[tuple[int, ...], str, str]], ...
]:
    state = Swipe2048State(board, Swipe2048Status(status_value))
    return tuple(
        (action, model._row_key(state, action))  # noqa: SLF001
        for action in _legal_actions(board)
    )


def _missing_frontier(
    rows: dict, root: Swipe2048State
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    """Exact V2 frontier traversal with canonical child states reused."""

    root_representative, _ = model.canonicalize_state_v1(root)
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        visit_key = (state.board, state.status.value, remaining)
        if (
            remaining == 0
            or state.status is not Swipe2048Status.ACTIVE
            or visit_key in visited
        ):
            return
        visited.add(visit_key)
        for _, key in _action_row_keys(state.board, state.status.value):
            row = rows.get(key)
            if row is None:
                missing.add(key)
            else:
                for outcome in row.outcomes:
                    walk(outcome.next_state, remaining - 1)

    walk(root_representative, pre.PLANNING_HORIZON)
    return tuple(sorted(missing))


class _IncrementalModelDocuments:
    """Memoize immutable row documents and each append-only model epoch."""

    def __init__(
        self,
        source_archive_id: str,
        validation_archive_id: str,
        support_proposal_id: str,
        interval_id: str,
    ) -> None:
        self._source_archive_id = source_archive_id
        self._validation_archive_id = validation_archive_id
        self._support_proposal_id = support_proposal_id
        self._interval_id = interval_id
        self._row_documents: dict[tuple[tuple[int, ...], str, str], dict[str, Any]] = {}
        self._models: dict[int, dict[str, Any]] = {}

    def document(self, rows: dict) -> dict[str, Any]:
        cached = self._models.get(len(rows))
        if cached is not None:
            return cached
        for key, row in rows.items():
            if key not in self._row_documents:
                self._row_documents[key] = row.to_document()
        row_documents = [self._row_documents[key] for key in sorted(rows)]
        payload = {
            "schema": "acfqp.standard_2048_support_partial_d4_world_model.v2",
            "schema_version": model.SCHEMA_VERSION,
            "semantics": "STANDARD_4X4_SWIPE_THEN_OBSERVATION_DERIVED_PARTIAL_SPAWN_V2",
            "abstraction": "D4_QUOTIENT_WITH_SUPPORT_POSITION_RANK_UNKNOWN_INTERVALS_V2",
            "query_neutral": True,
            "support_source_archive_id": self._source_archive_id,
            "support_validation_archive_id": self._validation_archive_id,
            "support_proposal_id": self._support_proposal_id,
            "partial_dynamics_interval_id": self._interval_id,
            "support_position_rank_observation_derived": True,
            "unknown_support_mass_bounded": True,
            "unknown_support_score_upper_uses_finite_mass_horizon_cap": True,
            "rectangular_rowwise_interval_relaxation": True,
            "rows": row_documents,
            "row_count": len(row_documents),
            "support_outcome_count": sum(
                row.support_outcome_count for row in rows.values()
            ),
        }
        document = {
            **payload,
            "partial_world_model_id": content_id(model.DOMAINS["model"], payload),
        }
        self._models[len(rows)] = document
        return document


class _PersistentRobustSubproofs:
    """Reuse only closed Bellman subproofs over immutable partial rows."""

    def __init__(self, rank_two_lower: Fraction, rank_two_upper: Fraction) -> None:
        self._rank_two_lower = rank_two_lower
        self._rank_two_upper = rank_two_upper
        self._cache: dict[
            tuple[tuple[int, ...], str, int],
            tuple[Any, frozenset[str]],
        ] = {}
        self.cache_hits = 0

    def solve(
        self, rows: dict, root: Swipe2048State
    ) -> tuple[Any, tuple[str, ...]]:
        def recurse(
            board: tuple[int, ...], status_value: str, remaining: int
        ) -> tuple[Any, frozenset[str]]:
            representative = Swipe2048State(
                board, Swipe2048Status(status_value)
            )
            key = (board, status_value, remaining)
            cached = self._cache.get(key)
            if cached is not None:
                self.cache_hits += 1
                return cached
            if remaining == 0 or representative.status is Swipe2048Status.WON:
                result = model._RobustValueV1(  # noqa: SLF001
                    Fraction(), Fraction(), Fraction(), None
                )
                closed = result, frozenset()
                self._cache[key] = closed
                return closed
            if representative.status is Swipe2048Status.LOST:
                result = model._RobustValueV1(  # noqa: SLF001
                    Fraction(), Fraction(), Fraction(1), None
                )
                closed = result, frozenset()
                self._cache[key] = closed
                return closed
            best = None
            dependencies: set[str] = set()
            for action, row_key in _action_row_keys(
                representative.board, representative.status.value
            ):
                row = rows.get(row_key)
                if row is None:
                    _fail("persistent robust solve reached an open support row")
                dependencies.add(row.row_id)
                by_rank: dict[int, tuple[Fraction, Fraction, Fraction]] = {}
                for rank in (1, 2):
                    rank_outcomes = tuple(
                        outcome
                        for outcome in row.outcomes
                        if outcome.spawn_rank == rank
                    )
                    lower_values: list[Fraction] = []
                    upper_values: list[Fraction] = []
                    loss_values: list[Fraction] = []
                    for outcome in rank_outcomes:
                        child, child_dependencies = recurse(
                            outcome.next_state.board,
                            outcome.next_state.status.value,
                            remaining - 1,
                        )
                        dependencies.update(child_dependencies)
                        lower_values.append(
                            outcome.merge_score + child.score_lower
                        )
                        upper_values.append(
                            outcome.merge_score + child.score_upper
                        )
                        loss_values.append(child.loss_upper)
                    lower_bounds = tuple(
                        outcome.position_probability_lower
                        for outcome in rank_outcomes
                    )
                    upper_bounds = tuple(
                        outcome.position_probability_upper
                        for outcome in rank_outcomes
                    )
                    by_rank[rank] = (
                        model._box_expectation_extreme(  # noqa: SLF001
                            tuple(lower_values),
                            lower_bounds,
                            upper_bounds,
                            maximize=False,
                        ),
                        model._box_expectation_extreme(  # noqa: SLF001
                            tuple(upper_values),
                            lower_bounds,
                            upper_bounds,
                            maximize=True,
                        ),
                        model._box_expectation_extreme(  # noqa: SLF001
                            tuple(loss_values),
                            lower_bounds,
                            upper_bounds,
                            maximize=True,
                        ),
                    )
                lower_endpoints = tuple(
                    (1 - probability) * by_rank[1][0]
                    + probability * by_rank[2][0]
                    for probability in (
                        self._rank_two_lower,
                        self._rank_two_upper,
                    )
                )
                upper_endpoints = tuple(
                    (1 - probability) * by_rank[1][1]
                    + probability * by_rank[2][1]
                    for probability in (
                        self._rank_two_lower,
                        self._rank_two_upper,
                    )
                )
                loss_endpoints = tuple(
                    (1 - probability) * by_rank[1][2]
                    + probability * by_rank[2][2]
                    for probability in (
                        self._rank_two_lower,
                        self._rank_two_upper,
                    )
                )
                known_upper = max(upper_endpoints)
                unknown_score_upper = model._unknown_spawn_score_upper(  # noqa: SLF001
                    representative,
                    merge_score=row.outcomes[0].merge_score,
                    remaining=remaining,
                )
                candidate = model._RobustValueV1(  # noqa: SLF001
                    (1 - row.unknown_support_mass_upper) * min(lower_endpoints),
                    known_upper
                    + row.unknown_support_mass_upper
                    * max(Fraction(), unknown_score_upper - known_upper),
                    min(
                        Fraction(1),
                        row.unknown_support_mass_upper
                        + (1 - row.unknown_support_mass_upper)
                        * max(loss_endpoints),
                    ),
                    action,
                )
                if model._better_robust(candidate, best):  # noqa: SLF001
                    best = candidate
            if best is None:
                best = model._RobustValueV1(  # noqa: SLF001
                    Fraction(), Fraction(), Fraction(1), None
                )
            closed = best, frozenset(dependencies)
            self._cache[key] = closed
            return closed

        representative, transform = model.canonicalize_state_v1(root)
        result, dependencies = recurse(
            representative.board,
            representative.status.value,
            pre.PLANNING_HORIZON,
        )
        if result.selected_action is None:
            return result, tuple(sorted(dependencies))
        lifted = model.transform_action_v1(
            result.selected_action, model.inverse_d4(transform)
        )
        return (
            model._RobustValueV1(  # noqa: SLF001
                result.score_lower,
                result.score_upper,
                result.loss_upper,
                lifted,
            ),
            tuple(sorted(dependencies)),
        )


def _audit_document(
    rows: dict,
    state: Swipe2048State,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
    model_documents: _IncrementalModelDocuments,
    robust_subproofs: _PersistentRobustSubproofs,
) -> dict[str, Any]:
    """Reproduce the V2 audit while reusing immutable model epoch bytes."""

    world_model = model_documents.document(rows)
    missing = _missing_frontier(rows, state)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_support_partial_model_audit.v2",
        "schema_version": model.SCHEMA_VERSION,
        "partial_world_model_id": world_model["partial_world_model_id"],
        "partial_dynamics_interval_id": interval_id,
        "support_proposal_id": support_proposal_id,
        "root_state": _state_document(state),
        "horizon": pre.PLANNING_HORIZON,
        "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
        "status": (
            "FAILED_PROOF_FRONTIER"
            if missing
            else "CERTIFIED_PARTIAL_DYNAMICS_ROBUST"
        ),
        "missing_frontier": [model._key_document(key) for key in missing],  # noqa: SLF001
        "missing_frontier_count": len(missing),
    }
    if missing:
        payload.update(
            {
                "selected_action": None,
                "robust_score_lower": None,
                "robust_score_upper": None,
                "robust_loss_probability_upper": None,
                "ordered_dependency_row_ids": [],
                "robust_plan_id": None,
            }
        )
    else:
        value, dependencies = robust_subproofs.solve(rows, state)
        if value.selected_action is None:
            _fail("active H3 root produced no interval-robust action")
        plan_payload = {
            "schema": "acfqp.standard_2048_support_interval_robust_plan.v2",
            "schema_version": model.SCHEMA_VERSION,
            "partial_world_model_id": world_model["partial_world_model_id"],
            "partial_dynamics_interval_id": interval_id,
            "support_proposal_id": support_proposal_id,
            "root_state": _state_document(state),
            "horizon": pre.PLANNING_HORIZON,
            "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
            "selected_action": value.selected_action.value,
            "robust_score_lower": _fdoc(value.score_lower),
            "robust_score_upper": _fdoc(value.score_upper),
            "robust_loss_probability_upper": _fdoc(value.loss_upper),
            "ordered_dependency_row_ids": list(dependencies),
        }
        payload.update(
            {
                "selected_action": value.selected_action.value,
                "robust_score_lower": _fdoc(value.score_lower),
                "robust_score_upper": _fdoc(value.score_upper),
                "robust_loss_probability_upper": _fdoc(value.loss_upper),
                "ordered_dependency_row_ids": list(dependencies),
                "robust_plan_id": content_id(model.DOMAINS["plan"], plan_payload),
            }
        )
    return {**payload, "audit_id": content_id(model.DOMAINS["audit"], payload)}


def _support_proposal(
    source_archive_id: str, validation_archive_id: str
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_h3_targeted_support_proposal.v8",
        "schema_version": SCHEMA_VERSION,
        "h3_reuse_preregistration_id": PREREGISTRATION_ID,
        "targeted_source_archive_id": source_archive_id,
        "targeted_validation_archive_id": validation_archive_id,
        "candidate_meta_grammar": list(targeted.pre.SUPPORT_CANDIDATES),
        "selected_support_rule": targeted.pre.SELECTED_SUPPORT_RULE,
        "selected_rule_semantics": (
            "ENUMERATE_EVERY_SORTED_POST_SWIPE_EMPTY_CELL_AS_POSSIBLE_SPAWN"
        ),
        "selected_uniquely_from_v161_source_raw_observations": True,
        "heldout_validation_not_used_for_selection": True,
        "heldout_support_validation_passed": True,
        "fixed_human_meta_grammar": True,
        "support_completeness_is_conditional_on_registered_candidate_family": True,
        "open_ended_support_invention_claimed": False,
    }
    return {
        **payload,
        "support_proposal_id": content_id(DOMAINS["support_proposal"], payload),
    }


def _interval_binding(
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
) -> tuple[dict[str, Any], dict[int, tuple[tuple[Fraction, Fraction], ...]], Fraction, Fraction]:
    source_counts = tuple(
        (8, 8, 8, 8, 8, 8, 8, 8, 256, 8192, 8192, 8192, 8192, 8192, 8192, 8)
    )
    validation_counts = tuple(
        (4, 4, 4, 4, 4, 4, 4, 4, 128, 1024, 1024, 1024, 1024, 1024, 1024, 4)
    )
    bounds, lower, upper, evidence = targeted._snapshot(  # noqa: SLF001
        source_counts, validation_counts
    )
    if not evidence["heldout_support_and_intervals_passed"]:
        _fail("targeted interval evidence failed replay")
    position_rows = [
        {
            "post_swipe_empty_cardinality": row["empty_cardinality"],
            "source_record_count": row["source_count"],
            "heldout_validation_record_count": row["validation_count"],
            "radius": row["radius"],
            "categories": [
                {
                    "sorted_empty_ordinal": category["ordinal"],
                    "probability_lower": category["lower"],
                    "probability_upper": category["upper"],
                    "heldout_inside_source_interval": category["heldout_inside"],
                }
                for category in row["categories"]
            ],
            "probability_simplex_feasible": row["probability_simplex_feasible"],
        }
        for row in evidence["position_intervals"]
    ]
    payload = {
        "schema": "acfqp.standard_2048_h3_targeted_interval_binding.v8",
        "schema_version": SCHEMA_VERSION,
        "h3_reuse_preregistration_id": PREREGISTRATION_ID,
        "targeted_source_archive_id": source_archive_id,
        "targeted_validation_archive_id": validation_archive_id,
        "support_proposal_id": support_proposal_id,
        "source_counts_by_cardinality": list(source_counts),
        "validation_counts_by_cardinality": list(validation_counts),
        "unique_offline_transition_observation_count": evidence[
            "unique_offline_transition_observation_count"
        ],
        "position_intervals": position_rows,
        "rank_two_probability_lower": _fdoc(lower),
        "rank_two_probability_upper": _fdoc(upper),
        "unknown_support_probability_upper_within_registered_family": _fdoc(
            Fraction()
        ),
        "heldout_support_and_intervals_passed": True,
        "confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_replay_does_not_establish_iid": True,
    }
    document = {
        **payload,
        "partial_dynamics_interval_id": content_id(
            DOMAINS["interval_binding"], payload
        ),
    }
    return document, bounds, lower, upper


def _materialize_row(
    key: tuple[tuple[int, ...], str, str],
    interval_id: str,
    proposal_id: str,
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
) -> model.Standard2048SupportPartialRowV2:
    inherited = model._materialize_partial_row(  # noqa: SLF001
        key, interval_id, proposal_id, bounds
    )
    return model.Standard2048SupportPartialRowV2(
        inherited.state,
        inherited.action,
        inherited.outcomes,
        inherited.support_outcome_count,
        inherited.partial_dynamics_interval_id,
        inherited.support_proposal_id,
        Fraction(),
    )


def _materialize_row_task(
    task: tuple[
        tuple[tuple[int, ...], str, str],
        str,
        str,
        dict[int, tuple[tuple[Fraction, Fraction], ...]],
    ],
) -> tuple[tuple[tuple[int, ...], str, str], model.Standard2048SupportPartialRowV2]:
    key, interval_id, proposal_id, bounds = task
    return key, _materialize_row(key, interval_id, proposal_id, bounds)


def _recover(
    rows: dict,
    state: Any,
    interval_id: str,
    proposal_id: str,
    source_id: str,
    validation_id: str,
    bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_lower: Fraction,
    rank_upper: Fraction,
    model_documents: _IncrementalModelDocuments,
    robust_subproofs: _PersistentRobustSubproofs,
    executor: ProcessPoolExecutor,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    transactions: list[dict[str, Any]] = []
    added_rows = 0
    added_support = 0
    for index in range(1, pre.PLANNING_HORIZON + 2):
        audit = _audit_document(
            rows,
            state,
            source_id,
            validation_id,
            proposal_id,
            interval_id,
            rank_lower,
            rank_upper,
            model_documents,
            robust_subproofs,
        )
        if audit["status"] == "CERTIFIED_PARTIAL_DYNAMICS_ROBUST":
            return transactions, audit, added_rows, added_support
        frontier = tuple(
            (
                tuple(item["state"]["board_ranks"]),
                item["state"]["status"],
                item["action"],
            )
            for item in audit["missing_frontier"]
        )
        predecessor = model_documents.document(rows)["partial_world_model_id"]
        recovered = []
        missing_keys = tuple(key for key in frontier if key not in rows)
        tasks = tuple(
            (key, interval_id, proposal_id, bounds) for key in missing_keys
        )
        for key, row in executor.map(
            _materialize_row_task, tasks, chunksize=16
        ):
            rows[key] = row
            recovered.append(row)
            added_rows += 1
            added_support += row.support_outcome_count
        successor = model_documents.document(rows)["partial_world_model_id"]
        transactions.append(
            {
                "transaction_index": index,
                "failed_audit_id": audit["audit_id"],
                "failed_status": audit["status"],
                "predecessor_partial_world_model_id": predecessor,
                "recovered_frontier_count": len(recovered),
                "recovered_partial_row_ids": [row.row_id for row in recovered],
                "recovered_support_outcome_count": sum(
                    row.support_outcome_count for row in recovered
                ),
                "successor_partial_world_model_id": successor,
                "ground_support_access_before_failed_audit": False,
                "exact_spawn_or_position_probability_accessed_by_recovery": False,
            }
        )
    _fail("H3 recovery did not converge")


def _matched_direct_control(
    task: tuple[int, int, tuple[int, ...], str, str],
) -> tuple[int, int, dict[str, Any], dict[str, Any] | None]:
    """Run an exact cold H3 control; tasks are process-independent by construction."""

    episode_index, decision_index, board, status, selected_action = task
    state = Swipe2048State(board, Swipe2048Status(status))
    exact = model._direct_plan(state, pre.PLANNING_HORIZON)  # noqa: SLF001
    forced = None
    if exact["selected_action"] != selected_action:
        forced = model._direct_plan_forced_action(  # noqa: SLF001
            state,
            pre.PLANNING_HORIZON,
            Swipe2048Action(selected_action),
        )
    return episode_index, decision_index, exact, forced


def _campaign_document_with_executor(
    executor: ProcessPoolExecutor,
) -> dict[str, Any]:
    preregistration = pre.freeze_standard_2048_h3_reuse_preregistration_v8()
    if preregistration.preregistration_id != PREREGISTRATION_ID:
        _fail("preregistration identity changed")
    v161 = targeted.run_standard_2048_targeted_acquisition_campaign_v7()
    v161_document = v161.to_document()
    source_archive = v161_document["targeted_source_archive"]
    validation_archive = v161_document["targeted_validation_archive"]
    source_id = source_archive["targeted_source_archive_id"]
    validation_id = validation_archive["targeted_validation_archive_id"]
    proposal = _support_proposal(source_id, validation_id)
    interval, bounds, rank_lower, rank_upper = _interval_binding(
        source_id, validation_id, proposal["support_proposal_id"]
    )
    rows: dict = {}
    model_documents = _IncrementalModelDocuments(
        source_id,
        validation_id,
        proposal["support_proposal_id"],
        interval["partial_dynamics_interval_id"],
    )
    robust_subproofs = _PersistentRobustSubproofs(rank_lower, rank_upper)
    episode_drafts: list[dict[str, Any]] = []
    direct_tasks: list[tuple[int, int, tuple[int, ...], str, str]] = []
    total_added_rows = 0
    total_added_support = 0
    reuse_decisions = 0
    for episode_index, (board, seed) in enumerate(
        zip(pre.PREREGISTERED_INITIAL_BOARDS, pre.PREREGISTERED_EPISODE_SEEDS, strict=True)
    ):
        state = state_from_board_v1(board)
        initial = _state_document(state)
        initial_model = model_documents.document(rows)["partial_world_model_id"]
        decisions: list[dict[str, Any]] = []
        episode_rows = 0
        episode_support = 0
        for decision_index in range(pre.DECISIONS_PER_EPISODE):
            before_count = len(rows)
            base_audit = _audit_document(
                rows,
                state,
                source_id,
                validation_id,
                proposal["support_proposal_id"],
                interval["partial_dynamics_interval_id"],
                rank_lower,
                rank_upper,
                model_documents,
                robust_subproofs,
            )
            transactions, certified, added_rows, added_support = _recover(
                rows,
                state,
                interval["partial_dynamics_interval_id"],
                proposal["support_proposal_id"],
                source_id,
                validation_id,
                bounds,
                rank_lower,
                rank_upper,
                model_documents,
                robust_subproofs,
                executor,
            )
            selected = Swipe2048Action(certified["selected_action"])
            if before_count and added_rows == 0:
                reuse_decisions += 1
            direct_tasks.append(
                (
                    episode_index,
                    decision_index,
                    state.board,
                    state.status.value,
                    selected.value,
                )
            )
            outcome, digest = select_seeded_outcome_v1(
                step_v1(state, selected), seed=seed, decision_index=decision_index
            )
            decisions.append(
                {
                    "decision_index": decision_index,
                    "state_before_decision": _state_document(state),
                    "partial_row_count_before_audit": before_count,
                    "base_audit": base_audit,
                    "recovery_transactions": transactions,
                    "certified_robust_plan": certified,
                    "incremental_partial_row_count": added_rows,
                    "incremental_support_outcome_count": added_support,
                    "ground_support_access_before_failed_audit": False,
                    "executed_target_transition": {
                        "selected_action": selected.value,
                        "spawn_tape_digest": digest,
                        "spawned_cell": outcome.spawned_cell,
                        "spawned_rank": outcome.spawned_rank,
                        "merge_score": outcome.merge_score,
                        "successor_state": _state_document(outcome.next_state),
                        "target_observation_not_used_before_plan_freeze": True,
                    },
                }
            )
            state = outcome.next_state
            episode_rows += added_rows
            episode_support += added_support
        total_added_rows += episode_rows
        total_added_support += episode_support
        episode_drafts.append(
            {
                "schema": "acfqp.standard_2048_h3_targeted_reuse_episode.v8",
                "schema_version": SCHEMA_VERSION,
                "h3_reuse_preregistration_id": PREREGISTRATION_ID,
                "episode_index": episode_index,
                "execution_seed": seed,
                "initial_state": initial,
                "initial_partial_world_model_id": initial_model,
                "decisions": decisions,
                "decision_count": len(decisions),
                "incremental_partial_row_count": episode_rows,
                "incremental_support_outcome_count": episode_support,
                "final_state": _state_document(state),
            }
        )

    matched_direct: dict[
        tuple[int, int], tuple[dict[str, Any], dict[str, Any] | None]
    ] = {}
    for episode_index, decision_index, exact, forced in executor.map(
        _matched_direct_control, direct_tasks, chunksize=1
    ):
        matched_direct[(episode_index, decision_index)] = (exact, forced)
    if len(matched_direct) != len(direct_tasks):
        _fail("matched direct control cardinality changed")

    episodes: list[dict[str, Any]] = []
    total_direct_rows = 0
    total_direct_outcomes = 0
    exact_equivalent_decisions = 0
    exact_label_identical_decisions = 0
    exact_inside_envelope_decisions = 0
    mismatch_records: list[dict[str, Any]] = []
    for episode_draft in episode_drafts:
        episode_index = episode_draft["episode_index"]
        for decision in episode_draft["decisions"]:
            decision_index = decision["decision_index"]
            exact, forced = matched_direct[(episode_index, decision_index)]
            certified = decision["certified_robust_plan"]
            label_identical = (
                certified["selected_action"] == exact["selected_action"]
            )
            value_equivalent = label_identical
            if not label_identical:
                if forced is None:
                    _fail("forced exact H3 comparison is missing")
                value_equivalent = (
                    model._fraction_from_document(  # noqa: SLF001
                        forced["expected_merge_score"]
                    )
                    == model._fraction_from_document(  # noqa: SLF001
                        exact["expected_merge_score"]
                    )
                    and model._fraction_from_document(  # noqa: SLF001
                        forced["loss_probability_within_horizon"]
                    )
                    == model._fraction_from_document(  # noqa: SLF001
                        exact["loss_probability_within_horizon"]
                    )
                )
            exact_score = model._fraction_from_document(  # noqa: SLF001
                exact["expected_merge_score"]
            )
            exact_loss = model._fraction_from_document(  # noqa: SLF001
                exact["loss_probability_within_horizon"]
            )
            inside = (
                model._fraction_from_document(  # noqa: SLF001
                    certified["robust_score_lower"]
                )
                <= exact_score
                <= model._fraction_from_document(  # noqa: SLF001
                    certified["robust_score_upper"]
                )
                and exact_loss
                <= model._fraction_from_document(  # noqa: SLF001
                    certified["robust_loss_probability_upper"]
                )
            )
            if label_identical:
                exact_label_identical_decisions += 1
            if value_equivalent:
                exact_equivalent_decisions += 1
            if inside:
                exact_inside_envelope_decisions += 1
            if not value_equivalent or not inside:
                mismatch_records.append(
                    {
                        "episode_index": episode_index,
                        "decision_index": decision_index,
                        "robust_selected_action": certified["selected_action"],
                        "exact_selected_action": exact["selected_action"],
                        "robust_action_exact_evaluation": forced,
                        "selected_action_exact_value_and_loss_equivalent": (
                            value_equivalent
                        ),
                        "exact_direct_value_inside_robust_envelope": inside,
                    }
                )
            decision["matched_cold_direct"] = exact
            decision["robust_action_exact_evaluation"] = forced
            decision["selected_action_exact_value_and_loss_equivalent"] = (
                value_equivalent
            )
            decision["selected_action_label_identical"] = label_identical
            decision["exact_direct_value_inside_robust_envelope"] = inside
            total_direct_rows += exact["ground_state_action_row_count"]
            total_direct_outcomes += exact["ground_outcome_count"]
        episodes.append(
            {
                **episode_draft,
                "h3_reuse_episode_id": content_id(
                    DOMAINS["episode"], episode_draft
                ),
            }
        )
    final_model = model_documents.document(rows)
    payload = {
        "schema": "acfqp.standard_2048_h3_targeted_reuse_campaign.v8",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h3_reuse_preregistration": preregistration.to_document(),
        "preregistration_git_commit": PREREGISTRATION_COMMIT,
        "predecessor_v161_campaign_id": v161.campaign_id,
        "reused_targeted_source_archive": source_archive,
        "reused_targeted_validation_archive": validation_archive,
        "targeted_support_proposal": proposal,
        "targeted_interval_binding": interval,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(episodes) * pre.DECISIONS_PER_EPISODE,
        "final_partial_world_model": final_model,
        "partial_model_ground_support_row_count": total_added_rows,
        "partial_model_support_outcome_count": total_added_support,
        "decisions_reusing_rows_without_new_materialization": reuse_decisions,
        "matched_direct_ground_row_count_evaluation": total_direct_rows,
        "matched_direct_ground_outcome_count_evaluation": total_direct_outcomes,
        "matched_direct_controls_process_parallel": True,
        "matched_direct_control_process_count": MATCHED_DIRECT_PROCESS_COUNT,
        "parallelization_changes_exact_control_semantics": False,
        "failed_frontier_row_materialization_process_parallel": True,
        "failed_frontier_materialization_process_count": (
            MATCHED_DIRECT_PROCESS_COUNT
        ),
        "parallelization_changes_materialized_rows": False,
        "immutable_row_documents_memoized_across_model_epochs": True,
        "identical_model_epoch_documents_reused": True,
        "memoization_changes_model_or_certificate_semantics": False,
        "closed_bellman_subproof_cache_hit_count": robust_subproofs.cache_hits,
        "only_closed_immutable_subproofs_reused": True,
        "offline_observation_count_reused_from_v161": interval[
            "unique_offline_transition_observation_count"
        ],
        "additional_offline_observation_count": 0,
        "exact_label_identical_decision_count": exact_label_identical_decisions,
        "exact_value_and_loss_equivalent_decision_count": (
            exact_equivalent_decisions
        ),
        "exact_value_inside_robust_envelope_decision_count": (
            exact_inside_envelope_decisions
        ),
        "mismatch_records": mismatch_records,
        "mismatch_count": len(mismatch_records),
        "all_selected_actions_exact_value_and_loss_equivalent": (
            exact_equivalent_decisions == len(direct_tasks)
        ),
        "all_exact_values_inside_robust_envelopes": (
            exact_inside_envelope_decisions == len(direct_tasks)
        ),
        "ground_support_rows_materialized_only_after_failed_audit": True,
        "persistent_partial_rows_reused_across_decisions": reuse_decisions > 0,
        "multi_step_planning_completed_in_partial_abstract_model": True,
        "required_positive_conditions_passed": (
            exact_equivalent_decisions == len(direct_tasks)
            and reuse_decisions > 0
        ),
        "preregistered_scientific_outcome": (
            "POSITIVE_REGISTERED_LOCAL_RESULT"
            if exact_equivalent_decisions == len(direct_tasks)
            and reuse_decisions > 0
            else "NEGATIVE_REGISTERED_LOCAL_RESULT"
        ),
        "cold_ground_fallback_preserved": True,
        "negative_result_does_not_disable_fallback": True,
        "conditional_registered_support_family_only": True,
        "physical_iid_randomness_claimed": False,
        "total_operational_work_saving_claimed": False,
        "formal_confirmatory_gate_claimed": False,
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
        "h3_reuse_campaign_id": content_id(DOMAINS["campaign"], payload),
    }
    if (
        document["h3_reuse_campaign_id"] != EXPECTED_CAMPAIGN_ID
        or document["partial_model_ground_support_row_count"]
        != EXPECTED_PARTIAL_ROW_COUNT
        or document["partial_model_support_outcome_count"]
        != EXPECTED_SUPPORT_OUTCOME_COUNT
        or document["exact_value_and_loss_equivalent_decision_count"]
        != EXPECTED_EXACT_EQUIVALENT_DECISION_COUNT
        or document["mismatch_count"] != EXPECTED_MISMATCH_COUNT
    ):
        _fail("registered H3 negative-result receipt changed")
    return document


@lru_cache(maxsize=1)
def _campaign_document() -> dict[str, Any]:
    with ProcessPoolExecutor(max_workers=MATCHED_DIRECT_PROCESS_COUNT) as executor:
        return _campaign_document_with_executor(executor)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048H3ReuseCampaignV8:
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
            key: value for key, value in document.items() if key != "h3_reuse_campaign_id"
        }
        if (
            document.get("h3_reuse_campaign_id") != self.campaign_id
            or content_id(DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("H3 campaign root is not an object")
        return document


def run_standard_2048_h3_reuse_campaign_v8() -> Standard2048H3ReuseCampaignV8:
    document = _campaign_document()
    return Standard2048H3ReuseCampaignV8(
        _ISSUER, canonical_json_bytes(document), document["h3_reuse_campaign_id"]
    )


__all__ = (
    "ConstructionK7Standard2048H3ReuseCampaignV8Error",
    "DOMAINS",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_EXACT_EQUIVALENT_DECISION_COUNT",
    "EXPECTED_MISMATCH_COUNT",
    "EXPECTED_PARTIAL_ROW_COUNT",
    "EXPECTED_SUPPORT_OUTCOME_COUNT",
    "PREREGISTRATION_ID",
    "Standard2048H3ReuseCampaignV8",
    "run_standard_2048_h3_reuse_campaign_v8",
)
