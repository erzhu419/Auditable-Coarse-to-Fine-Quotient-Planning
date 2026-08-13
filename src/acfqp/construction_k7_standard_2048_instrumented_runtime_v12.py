"""Same-window native operation meters for the accounted 2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import (
    construction_k7_standard_2048_long_episode_independent_verifier_v11 as replay,
)
from acfqp import (
    construction_k7_standard_2048_fresh_board_support_independent_verifier_v2
    as support_v2,
)
from acfqp.domains.g2048 import inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
DOMAINS = pre.FUTURE_DOMAINS


class ConstructionK7Standard2048InstrumentedRuntimeV12Error(RuntimeError):
    """An operation meter, route order, or exact-rational result changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048InstrumentedRuntimeV12Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


class NativeCounterSetV12:
    """Mutable only while one owner executes one registered call window."""

    def __init__(self) -> None:
        registry = registry_v8.official_counter_registry_v8()
        self._values = {path: 0 for path in registry.by_path}

    def add(self, path: str, value: int = 1) -> None:
        if (
            path not in self._values
            or type(value) is not int
            or value < 0
        ):
            _fail("native counter increment changed")
        self._values[path] += value

    def maximum(self, path: str, value: int) -> None:
        if (
            path not in self._values
            or type(value) is not int
            or value < 0
        ):
            _fail("native peak counter input changed")
        self._values[path] = max(self._values[path], value)

    def value(self, path: str) -> int:
        try:
            return self._values[path]
        except KeyError as error:
            raise ConstructionK7Standard2048InstrumentedRuntimeV12Error(
                "unknown native counter path"
            ) from error

    def freeze(self) -> Mapping[str, int]:
        return MappingProxyType(dict(self._values))


class InstrumentedLazyRowsV12(replay._LazyRows):  # noqa: SLF001
    def __init__(
        self,
        bounds: dict[int, tuple[tuple[Fraction, Fraction], ...]],
        operator_id: str,
        counters: NativeCounterSetV12,
    ) -> None:
        super().__init__(bounds, operator_id)
        self._counters = counters

    def begin_counter_window(self, counters: NativeCounterSetV12) -> None:
        if type(counters) is not NativeCounterSetV12:
            _fail("factored row counter-window owner changed")
        self._counters = counters

    def get(self, key: tuple[tuple[int, ...], str, str]) -> replay._RowView:  # noqa: SLF001
        row = super().get(key)
        self._counters.add("common.abstract_bellman_backups")
        self._counters.add(
            "common.abstract_support_outcome_evaluations",
            row.support_outcome_count,
        )
        return row


class InstrumentedPersistentBellmanV12:
    def __init__(
        self,
        rank_lower: Fraction,
        rank_upper: Fraction,
        counters: NativeCounterSetV12,
    ) -> None:
        self._rank_lower = rank_lower
        self._rank_upper = rank_upper
        self._counters = counters
        self._cache: dict[
            tuple[tuple[int, ...], str, int], support_v2._RobustValueV1
        ] = {}

    def begin_counter_window(self, counters: NativeCounterSetV12) -> None:
        if type(counters) is not NativeCounterSetV12:
            _fail("Bellman counter-window owner changed")
        self._counters = counters

    def _state_value(
        self,
        rows: InstrumentedLazyRowsV12,
        board: tuple[int, ...],
        status_value: str,
        remaining: int,
    ) -> support_v2._RobustValueV1:
        self._counters.add("common.abstract_subproof_cache_lookups")
        state = Swipe2048State(board, Swipe2048Status(status_value))
        key = (board, status_value, remaining)
        cached = self._cache.get(key)
        if cached is not None:
            self._counters.add("common.abstract_subproof_cache_hits")
            return cached
        self._counters.add("common.abstract_subproof_cache_misses")
        if remaining == 0 or state.status is Swipe2048Status.WON:
            value = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(), None
            )
            self._cache[key] = value
            return value
        if state.status is Swipe2048Status.LOST:
            value = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
            self._cache[key] = value
            return value
        best = None
        for action, row_key in replay._action_row_keys(  # noqa: SLF001
            board, status_value
        ):
            candidate = self._action_value(rows, state, action, row_key, remaining)
            if support_v2._better_robust(candidate, best):  # noqa: SLF001
                best = candidate
        if best is None:
            best = support_v2._RobustValueV1(  # noqa: SLF001
                Fraction(), Fraction(), Fraction(1), None
            )
        self._cache[key] = best
        return best

    def _action_value(
        self,
        rows: InstrumentedLazyRowsV12,
        representative: Swipe2048State,
        action: Swipe2048Action,
        row_key: tuple[tuple[int, ...], str, str],
        remaining: int,
    ) -> support_v2._RobustValueV1:
        row = rows.get(row_key)
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
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(lower_values), lower_bounds, upper_bounds, maximize=False
                ),
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(upper_values), lower_bounds, upper_bounds, maximize=True
                ),
                support_v2._box_expectation_extreme(  # noqa: SLF001
                    tuple(loss_values), lower_bounds, upper_bounds, maximize=True
                ),
            )
        lower_endpoints = tuple(
            (1 - probability) * by_rank[1][0]
            + probability * by_rank[2][0]
            for probability in (self._rank_lower, self._rank_upper)
        )
        upper_endpoints = tuple(
            (1 - probability) * by_rank[1][1]
            + probability * by_rank[2][1]
            for probability in (self._rank_lower, self._rank_upper)
        )
        loss_endpoints = tuple(
            (1 - probability) * by_rank[1][2]
            + probability * by_rank[2][2]
            for probability in (self._rank_lower, self._rank_upper)
        )
        known_upper = max(upper_endpoints)
        unknown_score_upper = support_v2._unknown_spawn_score_upper(  # noqa: SLF001
            representative,
            merge_score=row.outcomes[0].merge_score,
            remaining=remaining,
        )
        return support_v2._RobustValueV1(  # noqa: SLF001
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
        self, rows: InstrumentedLazyRowsV12, root: Swipe2048State
    ) -> tuple[support_v2._RobustValueV1, ...]:
        representative, transform = canonicalize_state_v1(root)
        output = []
        for action, row_key in replay._action_row_keys(  # noqa: SLF001
            representative.board, representative.status.value
        ):
            value = self._action_value(
                rows, representative, action, row_key, pre.PLANNING_HORIZON
            )
            output.append(
                support_v2._RobustValueV1(  # noqa: SLF001
                    value.score_lower,
                    value.score_upper,
                    value.loss_upper,
                    transform_action_v1(action, inverse_d4(transform)),
                )
            )
        return tuple(
            sorted(
                output,
                key=lambda row: ACTION_ORDER.index(row.selected_action),
            )
        )


def _certificate(
    state: Swipe2048State,
    operator_id: str,
    rows: InstrumentedLazyRowsV12,
    bellman: InstrumentedPersistentBellmanV12,
    counters: NativeCounterSetV12,
) -> dict[str, Any]:
    before = counters.freeze()
    values = bellman.root_action_values(rows, state)
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
        _fail("strict dominance produced multiple actions")
    selected = None if not eligible else eligible[0].selected_action
    after = counters.freeze()
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
        "operation_deltas": {
            path: after[path] - before[path]
            for path in (
                "common.abstract_bellman_backups",
                "common.abstract_audit_obligations",
                "common.abstract_subproof_cache_lookups",
                "common.abstract_subproof_cache_hits",
                "common.abstract_subproof_cache_misses",
                "common.abstract_support_outcome_evaluations",
            )
        },
        "route_frozen_before_ground_access": True,
        "ground_transition_accessed": False,
        "target_observation_accessed": False,
    }
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
    counters: NativeCounterSetV12,
    *,
    lane: str,
    forced_action: Swipe2048Action | None = None,
) -> dict[str, Any]:
    if lane not in {"OPERATIONAL_FALLBACK", "EVALUATION_ONLY"}:
        _fail("exact-plan lane changed")
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
    else:
        paths = {
            "states_expanded": "evaluation.exact_states_expanded",
            "actions_evaluated": "evaluation.exact_actions_evaluated",
            "ground_steps": "evaluation.exact_ground_steps",
            "outcome_rows": "evaluation.exact_outcome_rows",
            "bellman_backups": "evaluation.exact_bellman_backups",
            "subproof_cache_lookups": (
                "evaluation.exact_subproof_cache_lookups"
            ),
            "subproof_cache_hits": "evaluation.exact_subproof_cache_hits",
            "subproof_cache_misses": "evaluation.exact_subproof_cache_misses",
        }
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
            _fail("exact active root produced no action")
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
        "forced_root_action": None if forced_action is None else forced_action.value,
        "selected_action": selected.value,
        "expected_merge_score": _fdoc(score),
        "loss_probability_within_horizon": _fdoc(loss),
        "exact_rational_arithmetic": True,
    }
    return {
        **payload,
        "accounted_exact_plan_id": content_id(DOMAINS["decision"], payload),
    }


@dataclass(frozen=True, slots=True)
class InstrumentedDecisionDraftV12:
    decision_index: int
    state_before: Swipe2048State
    certificate: Mapping[str, Any]
    route: str
    selected_action: Swipe2048Action
    exact_plan: Mapping[str, Any]
    forced_exact_plan: Mapping[str, Any] | None
    selected_action_exact_value_and_loss_equivalent: bool
    selected_action_label_identical: bool
    executed_target_transition: Mapping[str, Any]
    state_after: Swipe2048State
    common_counter_values: Mapping[str, int]
    fallback_counter_values: Mapping[str, int] | None
    evaluation_counter_values: Mapping[str, int] | None

    def to_document(self) -> dict[str, Any]:
        return {
            "decision_index": self.decision_index,
            "state_before_decision": _state_document(self.state_before),
            "certificate": dict(self.certificate),
            "route": self.route,
            "selected_action": self.selected_action.value,
            "exact_plan": dict(self.exact_plan),
            "forced_exact_plan": (
                None if self.forced_exact_plan is None else dict(self.forced_exact_plan)
            ),
            "selected_action_exact_value_and_loss_equivalent": (
                self.selected_action_exact_value_and_loss_equivalent
            ),
            "selected_action_label_identical": self.selected_action_label_identical,
            "executed_target_transition": dict(self.executed_target_transition),
            "state_after_decision": _state_document(self.state_after),
            "common_counter_values": dict(self.common_counter_values),
            "fallback_counter_values": (
                None
                if self.fallback_counter_values is None
                else dict(self.fallback_counter_values)
            ),
            "evaluation_counter_values": (
                None
                if self.evaluation_counter_values is None
                else dict(self.evaluation_counter_values)
            ),
        }


@dataclass(frozen=True, slots=True)
class OperationalAccountingChainV12:
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    projection_proof: ActualProjectionProofV1

    def to_document(self) -> dict[str, Any]:
        return {
            "work_vector": self.work_vector.to_dict(),
            "comparison_vector": self.comparison_vector.to_dict(),
            "actual_projection_proof": self.projection_proof.to_dict(),
        }


def _records(
    values: Mapping[str, int], *, recorder_id: str
) -> tuple[CounterRecordV1, ...]:
    registry = registry_v8.official_counter_registry_v8()
    if set(values) != set(registry.by_path):
        _fail("native counter values do not cover the full V8 registry")
    return tuple(
        CounterRecordV1.observe(
            registry, path, values[path], recorder_id=recorder_id
        )
        for path in sorted(values)
    )


def build_operational_accounting_chain_v12(
    *,
    subject_id: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    values: Mapping[str, int],
    recorder_id: str,
) -> OperationalAccountingChainV12:
    registry = registry_v8.official_counter_registry_v8()
    comparison_profile = registry_v8.official_comparison_profile_v8(registry)
    actual_profile = registry_v8.official_actual_projection_profile_v8(
        registry, comparison_profile
    )
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        route_kind,
        _records(values, recorder_id=recorder_id),
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=work_scope,
    )
    return OperationalAccountingChainV12(vector, comparison, proof)


def build_evaluation_work_vector_v12(
    *, subject_id: str, values: Mapping[str, int], recorder_id: str
) -> WorkVectorV1:
    registry = registry_v8.official_counter_registry_v8()
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        _records(values, recorder_id=recorder_id),
    )
    registry.validate_vector(vector)
    if any(
        vector.value(leaf.path)
        for leaf in registry.operational_leaves
    ):
        _fail("evaluation WorkVector contains operational route work")
    return vector


def execute_instrumented_decision_v12(
    *,
    state: Swipe2048State,
    decision_index: int,
    seed: str,
    operator_id: str,
    rows: InstrumentedLazyRowsV12,
    bellman: InstrumentedPersistentBellmanV12,
    common_counters: NativeCounterSetV12,
) -> InstrumentedDecisionDraftV12:
    if (
        type(state) is not Swipe2048State
        or state.status is not Swipe2048Status.ACTIVE
        or type(decision_index) is not int
        or decision_index < 0
        or type(seed) is not str
        or not seed
    ):
        _fail("instrumented decision input changed")
    rows.begin_counter_window(common_counters)
    bellman.begin_counter_window(common_counters)
    certificate = _certificate(
        state, operator_id, rows, bellman, common_counters
    )
    common_counters.add("route.attempts")
    evaluation = NativeCounterSetV12()
    fallback: NativeCounterSetV12 | None = None
    if certificate["selected_action"] is None:
        common_counters.add("route.failures")
        fallback = NativeCounterSetV12()
        exact = _exact_plan(
            state, fallback, lane="OPERATIONAL_FALLBACK"
        )
        selected = Swipe2048Action(exact["selected_action"])
        route = "COLD_EXACT_DIRECT_GROUND_FALLBACK"
        fallback.add("route.attempts")
        fallback.add("route.successes")
        forced = None
        equivalent = True
        evaluation_values = None
    else:
        common_counters.add("route.successes")
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
    selected_counters = common_counters if fallback is None else fallback
    selected_counters.add("target.execution_ground_steps")
    outcomes = step_v1(state, selected)
    selected_counters.add("target.execution_outcome_rows", len(outcomes))
    outcome, tape_digest = select_seeded_outcome_v1(
        outcomes, seed=seed, decision_index=decision_index
    )
    selected_counters.add("target.transition_observations")
    selected_counters.add("common.hash_invocations")
    transition = {
        "selected_action": selected.value,
        "spawn_tape_digest": tape_digest,
        "spawned_cell": outcome.spawned_cell,
        "spawned_rank": outcome.spawned_rank,
        "merge_score": outcome.merge_score,
        "successor_state": _state_document(outcome.next_state),
        "online_target_transition_observation_count": 1,
        "not_used_before_route_freeze": True,
    }
    return InstrumentedDecisionDraftV12(
        decision_index,
        state,
        MappingProxyType(dict(certificate)),
        route,
        selected,
        MappingProxyType(dict(exact)),
        None if forced is None else MappingProxyType(dict(forced)),
        equivalent,
        selected.value == exact["selected_action"],
        MappingProxyType(transition),
        outcome.next_state,
        common_counters.freeze(),
        None if fallback is None else fallback.freeze(),
        evaluation_values,
    )


@lru_cache(maxsize=1)
def smoke_first_registered_decision_v12() -> InstrumentedDecisionDraftV12:
    binding, bounds, rank_lower, rank_upper = replay._operator_binding()  # noqa: SLF001
    counters = NativeCounterSetV12()
    rows = InstrumentedLazyRowsV12(
        bounds, binding["long_operator_binding_id"], counters
    )
    bellman = InstrumentedPersistentBellmanV12(
        rank_lower, rank_upper, counters
    )
    return execute_instrumented_decision_v12(
        state=state_from_board_v1(pre.PREREGISTERED_INITIAL_BOARDS[0]),
        decision_index=0,
        seed=pre.PREREGISTERED_EPISODE_SEEDS[0],
        operator_id=binding["long_operator_binding_id"],
        rows=rows,
        bellman=bellman,
        common_counters=counters,
    )


__all__ = (
    "ConstructionK7Standard2048InstrumentedRuntimeV12Error",
    "InstrumentedDecisionDraftV12",
    "InstrumentedLazyRowsV12",
    "InstrumentedPersistentBellmanV12",
    "NativeCounterSetV12",
    "OperationalAccountingChainV12",
    "build_evaluation_work_vector_v12",
    "build_operational_accounting_chain_v12",
    "execute_instrumented_decision_v12",
    "smoke_first_registered_decision_v12",
)
