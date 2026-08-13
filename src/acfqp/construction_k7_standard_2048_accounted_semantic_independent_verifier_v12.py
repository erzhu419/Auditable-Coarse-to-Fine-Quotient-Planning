"""Producer-free semantic replay of the fresh native-accounted 2048 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import (
    construction_k7_standard_2048_accounted_independent_verifier_v12 as accounting,
)
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import (
    construction_k7_standard_2048_long_episode_independent_verifier_v11 as math_v11,
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
)
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
DOMAINS = pre.FUTURE_DOMAINS
MAXIMUM_REPLAY_PROCESSES = 4


class ConstructionK7Standard2048AccountedSemanticIndependentVerifierV12Error(
    ValueError
):
    """The fresh campaign differs from independent dynamics and counter replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AccountedSemanticIndependentVerifierV12Error(
        message
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


class _CounterSet:
    def __init__(self) -> None:
        self.values = {
            path: 0 for path in registry_v8.official_counter_registry_v8().by_path
        }

    def add(self, path: str, value: int = 1) -> None:
        if path not in self.values or type(value) is not int or value < 0:
            _fail("independent counter increment changed")
        self.values[path] += value

    def freeze(self) -> dict[str, int]:
        return dict(self.values)


def _certificate(
    state: Swipe2048State,
    operator_id: str,
    rows: math_v11._LazyRows,  # noqa: SLF001
    bellman: math_v11._PersistentBellman,  # noqa: SLF001
    counters: _CounterSet,
) -> dict[str, Any]:
    rows_before = rows.invocation_count
    support_before = rows.support_outcome_evaluation_count
    hits_before = bellman.cache_hits
    cache_before = len(bellman._cache)  # noqa: SLF001
    values = bellman.root_action_values(rows, state)
    row_delta = rows.invocation_count - rows_before
    support_delta = rows.support_outcome_evaluation_count - support_before
    hit_delta = bellman.cache_hits - hits_before
    miss_delta = len(bellman._cache) - cache_before  # noqa: SLF001
    counters.add("common.abstract_bellman_backups", row_delta)
    counters.add("common.abstract_support_outcome_evaluations", support_delta)
    counters.add("common.abstract_subproof_cache_lookups", hit_delta + miss_delta)
    counters.add("common.abstract_subproof_cache_hits", hit_delta)
    counters.add("common.abstract_subproof_cache_misses", miss_delta)
    eligible = []
    for candidate in values:
        passed = True
        for challenger in values:
            if candidate is challenger:
                continue
            counters.add("common.abstract_audit_obligations")
            if candidate.score_lower <= challenger.score_upper:
                passed = False
        if passed:
            eligible.append(candidate)
    if len(eligible) > 1:
        _fail("independent strict dominance produced multiple actions")
    selected = None if not eligible else eligible[0].selected_action
    operation_paths = (
        "common.abstract_bellman_backups",
        "common.abstract_audit_obligations",
        "common.abstract_subproof_cache_lookups",
        "common.abstract_subproof_cache_hits",
        "common.abstract_subproof_cache_misses",
        "common.abstract_support_outcome_evaluations",
    )
    operation_deltas = {path: counters.values[path] for path in operation_paths}
    payload = {
        "schema": "acfqp.standard_2048_accounted_route_certificate.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "operator_identity_id": operator_id,
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
        "selected_action": None if selected is None else selected.value,
        "status": (
            "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE"
            if selected is not None
            else "FAILED_STRICT_ROOT_INTERVAL_DOMINANCE"
        ),
        "operation_deltas": operation_deltas,
        "route_frozen_before_ground_access": True,
        "ground_transition_accessed": False,
        "target_observation_accessed": False,
    }
    counters.add("common.hash_invocations")
    return {
        **payload,
        "accounted_route_certificate_id": content_id(
            DOMAINS["decision"], payload
        ),
    }


@dataclass(frozen=True, slots=True)
class _ExactValue:
    expected_score: Fraction
    loss_probability: Fraction
    selected_action: Swipe2048Action | None


def _better_exact(candidate: _ExactValue, current: _ExactValue | None) -> bool:
    if current is None:
        return True
    return (
        candidate.expected_score,
        -candidate.loss_probability,
        -ACTION_ORDER.index(candidate.selected_action),
    ) > (
        current.expected_score,
        -current.loss_probability,
        -ACTION_ORDER.index(current.selected_action),
    )


def _exact_plan(
    root: Swipe2048State,
    counters: _CounterSet,
    *,
    lane: str,
    forced_action: Swipe2048Action | None = None,
) -> dict[str, Any]:
    if lane == "OPERATIONAL_FALLBACK":
        paths = {
            name: f"fallback.{name}"
            for name in (
                "states_expanded",
                "actions_evaluated",
                "ground_steps",
                "outcome_rows",
                "bellman_backups",
                "subproof_cache_lookups",
                "subproof_cache_hits",
                "subproof_cache_misses",
            )
        }
    elif lane == "EVALUATION_ONLY":
        paths = {
            "states_expanded": "evaluation.exact_states_expanded",
            "actions_evaluated": "evaluation.exact_actions_evaluated",
            "ground_steps": "evaluation.exact_ground_steps",
            "outcome_rows": "evaluation.exact_outcome_rows",
            "bellman_backups": "evaluation.exact_bellman_backups",
            "subproof_cache_lookups": "evaluation.exact_subproof_cache_lookups",
            "subproof_cache_hits": "evaluation.exact_subproof_cache_hits",
            "subproof_cache_misses": "evaluation.exact_subproof_cache_misses",
        }
    else:
        _fail("independent exact-plan lane changed")
    cache: dict[tuple[tuple[int, ...], str, int], _ExactValue] = {}

    def add(name: str, value: int = 1) -> None:
        counters.add(paths[name], value)

    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ExactValue:
        key = (board, status_value, remaining)
        add("subproof_cache_lookups")
        cached = cache.get(key)
        if cached is not None:
            add("subproof_cache_hits")
            return cached
        add("subproof_cache_misses")
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            value = _ExactValue(Fraction(), Fraction(), None)
            cache[key] = value
            return value
        if state.status is Swipe2048Status.LOST:
            value = _ExactValue(Fraction(), Fraction(1), None)
            cache[key] = value
            return value
        add("states_expanded")
        best = None
        for action in legal_actions_v1(state.board):
            add("actions_evaluated")
            add("ground_steps")
            outcomes = step_v1(state, action)
            add("outcome_rows", len(outcomes))
            score = Fraction()
            loss = Fraction()
            for outcome in outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            add("bellman_backups")
            candidate = _ExactValue(score, loss, action)
            if _better_exact(candidate, best):
                best = candidate
        if best is None:
            best = _ExactValue(Fraction(), Fraction(1), None)
        cache[key] = best
        return best

    if forced_action is None:
        value = solve(root.board, root.status.value, pre.PLANNING_HORIZON)
        if value.selected_action is None:
            _fail("independent exact active root produced no action")
        selected = value.selected_action
        score = value.expected_score
        loss = value.loss_probability
    else:
        selected = forced_action
        score = Fraction()
        loss = Fraction()
        add("actions_evaluated")
        add("ground_steps")
        outcomes = step_v1(root, forced_action)
        add("outcome_rows", len(outcomes))
        for outcome in outcomes:
            child = solve(
                outcome.next_state.board,
                outcome.next_state.status.value,
                pre.PLANNING_HORIZON - 1,
            )
            score += outcome.probability * (
                outcome.merge_score + child.expected_score
            )
            loss += outcome.probability * child.loss_probability
        add("bellman_backups")
    payload = {
        "schema": "acfqp.standard_2048_accounted_exact_plan.v12",
        "schema_version": SCHEMA_VERSION,
        "root_state": _state_document(root),
        "planning_horizon": pre.PLANNING_HORIZON,
        "execution_lane": lane,
        "forced_root_action": (
            None if forced_action is None else forced_action.value
        ),
        "selected_action": selected.value,
        "expected_merge_score": _fdoc(score),
        "loss_probability_within_horizon": _fdoc(loss),
        "exact_rational_arithmetic": True,
    }
    counters.add(
        "common.hash_invocations"
        if lane == "OPERATIONAL_FALLBACK"
        else "evaluation.hash_invocations"
    )
    return {
        **payload,
        "accounted_exact_plan_id": content_id(DOMAINS["decision"], payload),
    }


def _decision(
    *,
    state: Swipe2048State,
    episode_index: int,
    decision_index: int,
    seed: str,
    operator_id: str,
    rows: math_v11._LazyRows,  # noqa: SLF001
    bellman: math_v11._PersistentBellman,  # noqa: SLF001
) -> tuple[dict[str, Any], dict[str, Any] | None, Swipe2048State]:
    common = _CounterSet()
    common.add("common.protocol_checks")
    certificate = _certificate(state, operator_id, rows, bellman, common)
    common.add("route.attempts")
    evaluation = _CounterSet()
    fallback: _CounterSet | None = None
    if certificate["selected_action"] is None:
        common.add("route.failures")
        fallback = _CounterSet()
        exact = _exact_plan(state, fallback, lane="OPERATIONAL_FALLBACK")
        selected = Swipe2048Action(exact["selected_action"])
        route = "COLD_EXACT_DIRECT_GROUND_FALLBACK"
        fallback.add("route.attempts")
        fallback.add("route.successes")
        forced = None
        equivalent = True
        evaluation_values = None
    else:
        common.add("route.successes")
        exact = _exact_plan(state, evaluation, lane="EVALUATION_ONLY")
        selected = Swipe2048Action(certificate["selected_action"])
        route = "ABSTRACT_CERTIFIED"
        if selected.value == exact["selected_action"]:
            forced = None
            equivalent = True
        else:
            forced = _exact_plan(
                state,
                evaluation,
                lane="EVALUATION_ONLY",
                forced_action=selected,
            )
            equivalent = (
                forced["expected_merge_score"] == exact["expected_merge_score"]
                and forced["loss_probability_within_horizon"]
                == exact["loss_probability_within_horizon"]
            )
        evaluation.add("evaluation.semantic_integrity_checks")
        evaluation.add("evaluation.semantic_protocol_checks")
        evaluation_values = evaluation.freeze()
    selected_counters = common if fallback is None else fallback
    if selected not in legal_actions_v1(state.board):
        _fail("independent route selected an illegal action")
    selected_counters.add("common.protocol_checks")
    selected_counters.add("target.execution_ground_steps")
    outcomes = step_v1(state, selected)
    selected_counters.add("target.execution_outcome_rows", len(outcomes))
    outcome, tape_digest = select_seeded_outcome_v1(
        outcomes, seed=seed, decision_index=decision_index
    )
    selected_counters.add("target.transition_observations")
    selected_counters.add("common.hash_invocations")
    selected_counters.add("common.integrity_checks")
    draft = {
        "decision_index": decision_index,
        "state_before_decision": _state_document(state),
        "certificate": certificate,
        "route": route,
        "selected_action": selected.value,
        "exact_plan": exact,
        "forced_exact_plan": forced,
        "selected_action_exact_value_and_loss_equivalent": equivalent,
        "selected_action_label_identical": selected.value
        == exact["selected_action"],
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
        "state_after_decision": _state_document(outcome.next_state),
        "common_counter_values": common.freeze(),
        "fallback_counter_values": (
            None if fallback is None else fallback.freeze()
        ),
        "evaluation_counter_values": evaluation_values,
    }
    evaluation_transport = None
    if route == "ABSTRACT_CERTIFIED":
        transport_values = dict(draft["evaluation_counter_values"])
        transport_values["evaluation.hash_invocations"] += 1
        transport_payload = {
            "schema": "acfqp.standard_2048_accounted_evaluation_transport.v12",
            "schema_version": SCHEMA_VERSION,
            "accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "episode_index": episode_index,
            "decision_index": decision_index,
            "state_before_decision": draft["state_before_decision"],
            "selected_action": draft["selected_action"],
            "exact_plan": draft["exact_plan"],
            "forced_selected_action_exact_evaluation": draft[
                "forced_exact_plan"
            ],
            "selected_action_exact_value_and_loss_equivalent": draft[
                "selected_action_exact_value_and_loss_equivalent"
            ],
            "selected_action_label_identical": draft[
                "selected_action_label_identical"
            ],
            "evaluation_counter_values": transport_values,
            "operational_route_work_present": False,
        }
        evaluation_transport = {
            **transport_payload,
            "accounted_counter_bundle_id": content_id(
                DOMAINS["counter_bundle"], transport_payload
            ),
        }
        draft["exact_plan"] = None
        draft["forced_exact_plan"] = None
        draft["evaluation_counter_values"] = None
    selected_values_key = (
        "common_counter_values"
        if route == "ABSTRACT_CERTIFIED"
        else "fallback_counter_values"
    )
    selected_values = dict(draft[selected_values_key])
    selected_values["common.hash_invocations"] += 1
    draft[selected_values_key] = selected_values
    decision_payload = {
        "schema": "acfqp.standard_2048_accounted_business_decision.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "operational_draft": draft,
        "matched_evaluation_transport_id": (
            None
            if evaluation_transport is None
            else evaluation_transport["accounted_counter_bundle_id"]
        ),
        "evaluation_not_used_for_route_selection": True,
    }
    decision = {
        **decision_payload,
        "accounted_decision_id": content_id(DOMAINS["decision"], decision_payload),
    }
    return decision, evaluation_transport, outcome.next_state


def _episode_replay(
    task: tuple[
        int,
        tuple[int, ...],
        str,
        int,
        str,
        dict[int, tuple[tuple[Fraction, Fraction], ...]],
        Fraction,
        Fraction,
    ]
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    (
        episode_index,
        board,
        seed,
        decision_limit,
        operator_id,
        bounds,
        rank_lower,
        rank_upper,
    ) = task
    state = state_from_board_v1(board)
    initial_state = _state_document(state)
    rows = math_v11._LazyRows(bounds, operator_id)  # noqa: SLF001
    bellman = math_v11._PersistentBellman(rank_lower, rank_upper)  # noqa: SLF001
    decisions = []
    evaluations = []
    for decision_index in range(decision_limit):
        if state.status is not Swipe2048Status.ACTIVE:
            break
        decision, evaluation, state = _decision(
            state=state,
            episode_index=episode_index,
            decision_index=decision_index,
            seed=seed,
            operator_id=operator_id,
            rows=rows,
            bellman=bellman,
        )
        decisions.append(decision)
        if evaluation is not None:
            evaluations.append(evaluation)
    payload = {
        "schema": "acfqp.standard_2048_accounted_business_episode.v12",
        "schema_version": SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": episode_index,
        "execution_seed": seed,
        "initial_state": initial_state,
        "operator_binding_id": operator_id,
        "decisions": decisions,
        "evaluation_transport_ids": [
            row["accounted_counter_bundle_id"] for row in evaluations
        ],
        "decision_count": len(decisions),
        "abstract_route_count": sum(
            row["operational_draft"]["route"] == "ABSTRACT_CERTIFIED"
            for row in decisions
        ),
        "fallback_route_count": sum(
            row["operational_draft"]["route"]
            == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
            for row in decisions
        ),
        "closure_reason": (
            "TERMINAL_STATE"
            if state.status is not Swipe2048Status.ACTIVE
            else "REGISTERED_DECISION_LIMIT"
        ),
        "final_state": _state_document(state),
        "maximum_final_board_tile_rank": max(state.board),
        "tile_2048_reached": max(state.board) >= 11,
        "all_selected_actions_exact_value_and_loss_equivalent": all(
            row["operational_draft"][
                "selected_action_exact_value_and_loss_equivalent"
            ]
            for row in decisions
        ),
    }
    return (
        {
            **payload,
            "accounted_episode_id": content_id(DOMAINS["episode"], payload),
        },
        tuple(evaluations),
    )


@dataclass(frozen=True, slots=True)
class Standard2048AccountedSemanticIndependentVerificationV12:
    campaign_id: str
    accounting_verification_id: str
    episode_count: int
    decision_count: int
    abstract_route_count: int
    fallback_route_count: int

    @property
    def verification_id(self) -> str:
        payload = {
            "campaign_id": self.campaign_id,
            "accounting_verification_id": self.accounting_verification_id,
            "episode_count": self.episode_count,
            "decision_count": self.decision_count,
            "abstract_route_count": self.abstract_route_count,
            "fallback_route_count": self.fallback_route_count,
            "fresh_dynamics_semantic_replay_passed": True,
            "native_counter_semantic_replay_passed": True,
            "producer_imported": False,
            "official_execution_allowed": False,
        }
        return content_id(DOMAINS["verification"], payload)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.standard_2048_accounted_semantic_independent_"
                "verification.v12"
            ),
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "accounting_verification_id": self.accounting_verification_id,
            "episode_count": self.episode_count,
            "decision_count": self.decision_count,
            "abstract_route_count": self.abstract_route_count,
            "fallback_route_count": self.fallback_route_count,
            "fresh_dynamics_semantic_replay_passed": True,
            "native_counter_semantic_replay_passed": True,
            "factored_bellman_replayed": True,
            "cold_direct_controls_replayed": True,
            "seeded_target_tapes_replayed": True,
            "evaluation_transport_ids_replayed": True,
            "producer_imported": False,
            "full_standard_2048_game_verified": False,
            "broad_sample_efficiency_verified": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_standard_2048_accounted_campaign_semantically_independently_v12(
    *, campaign_bytes: bytes, output_root: str | Path
) -> Standard2048AccountedSemanticIndependentVerificationV12:
    try:
        accounting_result = (
            accounting.verify_standard_2048_accounted_campaign_bundle_independently_v12(
                campaign_bytes=campaign_bytes,
                output_root=output_root,
            )
        )
    except accounting.ConstructionK7Standard2048AccountedIndependentVerifierV12Error as error:
        raise ConstructionK7Standard2048AccountedSemanticIndependentVerifierV12Error(
            "accounting predecessor replay failed"
        ) from error
    try:
        document = loads_canonical_json(campaign_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AccountedSemanticIndependentVerifierV12Error(
            "accounted campaign is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != campaign_bytes:
        _fail("accounted campaign is not canonical JSON")
    binding, bounds, rank_lower, rank_upper = math_v11._operator_binding()  # noqa: SLF001
    operator_id = binding["long_operator_binding_id"]
    tasks = []
    for episode in document["episodes"]:
        task = episode["worker_task"]
        tasks.append(
            (
                episode["episode_index"],
                tuple(task["initial_board_ranks"]),
                task["execution_seed"],
                task["decision_limit"],
                operator_id,
                bounds,
                rank_lower,
                rank_upper,
            )
        )
    if len(tasks) == 1:
        expected = [_episode_replay(tasks[0])]
    else:
        with ProcessPoolExecutor(
            max_workers=min(MAXIMUM_REPLAY_PROCESSES, len(tasks))
        ) as executor:
            expected = list(executor.map(_episode_replay, tasks, chunksize=1))
    expected.sort(key=lambda row: row[0]["episode_index"])
    expected_episodes = [row[0] for row in expected]
    actual_episodes = [row["business_episode"] for row in document["episodes"]]
    if [canonical_json_bytes(row) for row in expected_episodes] != [
        canonical_json_bytes(row) for row in actual_episodes
    ]:
        _fail("fresh business episodes differ from producer-free semantic replay")
    expected_evaluation_ids = [
        transport["accounted_counter_bundle_id"]
        for _, transports in expected
        for transport in transports
    ]
    actual_evaluation_ids = [
        identity
        for episode in actual_episodes
        for identity in episode["evaluation_transport_ids"]
    ]
    if expected_evaluation_ids != actual_evaluation_ids:
        _fail("evaluation transport identity order differs from semantic replay")
    result = Standard2048AccountedSemanticIndependentVerificationV12(
        campaign_id=document["accounted_campaign_id"],
        accounting_verification_id=accounting_result.verification_id,
        episode_count=len(expected_episodes),
        decision_count=sum(row["decision_count"] for row in expected_episodes),
        abstract_route_count=sum(
            row["abstract_route_count"] for row in expected_episodes
        ),
        fallback_route_count=sum(
            row["fallback_route_count"] for row in expected_episodes
        ),
    )
    return result


__all__ = (
    "ConstructionK7Standard2048AccountedSemanticIndependentVerifierV12Error",
    "Standard2048AccountedSemanticIndependentVerificationV12",
    "verify_standard_2048_accounted_campaign_semantically_independently_v12",
)
