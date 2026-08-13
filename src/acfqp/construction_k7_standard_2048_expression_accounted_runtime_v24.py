"""Native counter windows for the V24 synthesized-model accounting run."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
)
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
)


class ConstructionK7Standard2048ExpressionAccountedRuntimeV24Error(RuntimeError):
    """A native event, exact evaluator, or projection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedRuntimeV24Error(message)


class NativeCounterSetV24:
    """One full native-zero-initialized V9 recorder window."""

    def __init__(self) -> None:
        registry = registry_v9.official_counter_registry_v9()
        self._values = {path: 0 for path in registry.by_path}

    def add(self, path: str, value: int = 1) -> None:
        if path not in self._values or type(value) is not int or value < 0:
            _fail("native counter increment changed")
        self._values[path] += value

    def maximum(self, path: str, value: int) -> None:
        if path not in self._values or type(value) is not int or value < 0:
            _fail("native peak input changed")
        self._values[path] = max(self._values[path], value)

    def value(self, path: str) -> int:
        if path not in self._values:
            _fail("unknown native counter path")
        return self._values[path]

    def freeze(self) -> Mapping[str, int]:
        return MappingProxyType(dict(self._values))


@dataclass(frozen=True, slots=True)
class OperationalAccountingChainV24:
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    projection_proof: ActualProjectionProofV1
    native_zero_attestation: NativeZeroAttestationV1


def _records(
    values: Mapping[str, int], *, recorder_id: str
) -> tuple[CounterRecordV1, ...]:
    registry = registry_v9.official_counter_registry_v9()
    if set(values) != set(registry.by_path):
        _fail("native counter values do not cover the full V9 registry")
    return tuple(
        CounterRecordV1.observe(
            registry, path, values[path], recorder_id=recorder_id
        )
        for path in sorted(values)
    )


def build_operational_accounting_chain_v24(
    *,
    subject_id: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    values: Mapping[str, int],
    recorder_id: str,
) -> OperationalAccountingChainV24:
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
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
    return OperationalAccountingChainV24(
        vector,
        comparison,
        proof,
        NativeZeroAttestationV1.derive(vector, registry),
    )


def build_evaluation_work_vector_v24(
    *, subject_id: str, values: Mapping[str, int], recorder_id: str
) -> tuple[WorkVectorV1, NativeZeroAttestationV1]:
    registry = registry_v9.official_counter_registry_v9()
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        _records(values, recorder_id=recorder_id),
    )
    registry.validate_vector(vector)
    if any(vector.value(leaf.path) for leaf in registry.operational_leaves):
        _fail("evaluation vector contains operational work")
    return vector, NativeZeroAttestationV1.derive(vector, registry)


@dataclass(frozen=True, slots=True)
class _ExactValueV24:
    score: Fraction
    loss: Fraction
    action: Swipe2048Action | None


def _better(
    candidate: _ExactValueV24, current: _ExactValueV24 | None
) -> bool:
    if current is None:
        return True
    if candidate.action is None or current.action is None:
        _fail("terminal exact value entered action comparison")
    return (
        candidate.score,
        -candidate.loss,
        -ACTION_ORDER.index(candidate.action),
    ) > (
        current.score,
        -current.loss,
        -ACTION_ORDER.index(current.action),
    )


def evaluate_ground_root_with_native_counters_v24(
    state: Swipe2048State,
    *,
    outcome_provider: Any,
    horizon: int,
) -> tuple[dict[str, Any], Mapping[str, int]]:
    """Independently replay one exact root while incrementing at call sites."""

    if (
        type(state) is not Swipe2048State
        or not callable(outcome_provider)
        or type(horizon) is not int
        or horizon <= 0
    ):
        _fail("evaluation input changed")
    counters = NativeCounterSetV24()
    cache: dict[tuple[tuple[int, ...], str, int], _ExactValueV24] = {}

    def solve(board: tuple[int, ...], status: str, remaining: int) -> _ExactValueV24:
        canonical = planner._canonical(board)  # noqa: SLF001
        key = (canonical, status, remaining)
        counters.add("evaluation.exact_subproof_cache_lookups")
        cached = cache.get(key)
        if cached is not None:
            counters.add("evaluation.exact_subproof_cache_hits")
            return cached
        counters.add("evaluation.exact_subproof_cache_misses")
        current = Swipe2048State(canonical, Swipe2048Status(status))
        if remaining == 0 or current.status is Swipe2048Status.WON:
            value = _ExactValueV24(Fraction(), Fraction(), None)
        elif current.status is Swipe2048Status.LOST:
            value = _ExactValueV24(Fraction(), Fraction(1), None)
        else:
            counters.add("evaluation.exact_states_expanded")
            best = None
            for action in legal_actions_v1(current.board):
                candidate = action_value(current, action, remaining)
                if _better(candidate, best):
                    best = candidate
            value = best or _ExactValueV24(Fraction(), Fraction(1), None)
        cache[key] = value
        return value

    def action_value(
        current: Swipe2048State,
        action: Swipe2048Action,
        remaining: int,
    ) -> _ExactValueV24:
        counters.add("evaluation.exact_actions_evaluated")
        counters.add("evaluation.exact_ground_steps")
        outcomes: tuple[Swipe2048Outcome, ...] = outcome_provider(current, action)
        counters.add("evaluation.exact_outcome_rows", len(outcomes))
        score = Fraction()
        loss = Fraction()
        for outcome in outcomes:
            child = solve(
                outcome.next_state.board,
                outcome.next_state.status.value,
                remaining - 1,
            )
            score += outcome.probability * (outcome.merge_score + child.score)
            loss += outcome.probability * child.loss
        counters.add("evaluation.exact_bellman_backups")
        return _ExactValueV24(score, loss, action)

    counters.add("evaluation.exact_states_expanded")
    values = tuple(
        action_value(state, action, horizon)
        for action in legal_actions_v1(state.board)
    )
    best = None
    for candidate in values:
        if _better(candidate, best):
            best = candidate
    if best is None or best.action is None:
        _fail("active exact root has no selected action")
    document = {
        "root_action_exact_values": [
            {
                "action": value.action.value,
                "expected_merge_score": value.score,
                "loss_probability_within_horizon": value.loss,
            }
            for value in values
        ],
        "selected_action": best.action.value,
        "selected_expected_merge_score": best.score,
        "selected_loss_probability_within_horizon": best.loss,
        "ground_state_action_row_count": counters.value(
            "evaluation.exact_ground_steps"
        ),
        "ground_outcome_count": counters.value("evaluation.exact_outcome_rows"),
        "lane": "STANDALONE_EVALUATION_ONLY",
        "route_or_certificate_authority": False,
    }
    counters.add("evaluation.semantic_integrity_checks")
    counters.add("evaluation.semantic_protocol_checks")
    return document, counters.freeze()


def operational_decision_counter_values_v24(
    *,
    model: Mapping[str, Any],
    target_outcome_count: int,
) -> Mapping[str, int]:
    """Bind same-window planner deltas and one selected target transition."""

    counters = NativeCounterSetV24()
    required = {
        "factored_action_row_evaluation_count",
        "factored_support_outcome_evaluation_count",
        "subproof_cache_hit_count",
        "subproof_cache_miss_count",
        "cross_decision_subproof_cache_hit_count",
    }
    if not required.issubset(model) or type(target_outcome_count) is not int or target_outcome_count <= 0:
        _fail("operational decision evidence changed")
    rows = model["factored_action_row_evaluation_count"]
    outcomes = model["factored_support_outcome_evaluation_count"]
    hits = model["subproof_cache_hit_count"]
    misses = model["subproof_cache_miss_count"]
    cross_hits = model["cross_decision_subproof_cache_hit_count"]
    if any(type(value) is not int or value < 0 for value in (rows, outcomes, hits, misses, cross_hits)):
        _fail("planner native delta changed")
    counters.add("common.abstract_bellman_backups", rows)
    counters.add("common.abstract_support_outcome_evaluations", outcomes)
    counters.add("common.abstract_subproof_cache_lookups", hits + misses)
    counters.add("common.abstract_subproof_cache_hits", hits)
    counters.add("common.abstract_subproof_cache_misses", misses)
    counters.add("common.protocol_checks", 2)
    counters.add("common.integrity_checks", 2)
    counters.add("common.hash_invocations", 2)
    counters.add("route.attempts")
    counters.add("route.successes")
    counters.add("target.execution_ground_steps")
    counters.add("target.execution_outcome_rows", target_outcome_count)
    counters.add("target.transition_observations")
    return counters.freeze()


__all__ = (
    "NativeCounterSetV24",
    "OperationalAccountingChainV24",
    "build_evaluation_work_vector_v24",
    "build_operational_accounting_chain_v24",
    "evaluate_ground_root_with_native_counters_v24",
    "operational_decision_counter_values_v24",
)
