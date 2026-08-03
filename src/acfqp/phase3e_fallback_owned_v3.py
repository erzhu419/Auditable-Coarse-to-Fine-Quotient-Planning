"""Exact ground fallback owned by the sealed-source V4 route runtime.

The mathematical search is a mechanical V3 copy of the exhaustive deterministic-Markov
algorithm in ``phase3e_fallback_v1``.  It does not call or wrap that V1 search.
The seven accounting calls live at the real ledger primitive sites.  Each
must receive the event acknowledgement of the one active, owner-bound V4
search before the corresponding ledger mutation is allowed.

This module still returns the legacy V1 result/work transport so exact parity
can be checked without changing historical schemas.  The V4 transcript is a
separate construction artifact; no V6 CounterRecord, WorkVector,
ComparisonVector, semantic terminal, or official Gate is issued here.
"""

from __future__ import annotations

import builtins
from fractions import Fraction
import hashlib
from itertools import product
from types import CodeType
from typing import Any, Hashable, Mapping, NamedTuple

from acfqp.accounting_v1 import (
    CounterRegistryV1,
    RouteKindEnum,
    WorkVectorV1,
    explicit_records_v1,
    official_counter_registry_v1,
)
from acfqp.construction_accounting_route_segment_v4 import (
    OWNED_ROUTE_EVENT_ACK_V4,
    bind_owned_fallback_search_v4,
    emit_owned_route_operation_v4,
    finish_owned_fallback_search_v4,
    seal_owned_fallback_engine_import_v4,
    verify_owned_fallback_engine_import_seal_v4,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackExecutionV1,
    GroundFallbackFrontierPointV1,
    GroundFallbackOutcome,
    GroundFallbackProtocolError,
    GroundFallbackResultV1,
    GroundFallbackV1Error,
    _policy_content_signature,
)
from acfqp.phase3e_ids import parse_content_id
from acfqp.planning.common import (
    as_fraction,
    deterministic_order,
    is_stopped,
    iter_outcomes,
    outcome_reward,
    query_horizon,
    query_initial_distribution,
    reward_weights,
    validate_query,
)
from acfqp.planning.ground import ParetoPoint, pareto_prune, select_constrained
from acfqp.planning.policy import FiniteHorizonPolicy


SCHEMA_VERSION = "3.0.0"
PROFILE_KEY = "phase3e_fallback_owned_v3"
RECORDER_ID = "phase3e_fallback_owned_v3"
CONSTRUCTION_ONLY = True
PRODUCTION_OWNER_SOURCE_INTEGRATED = True
PRODUCTION_CLOSURE_CLAIMED = False


def _normalized_code_component_v3(value: Any) -> Any:
    """Return a line/path-independent recursive code-object component."""

    if isinstance(value, CodeType):
        return _normalized_code_structure_v3(value)
    if value is None or type(value) in {bool, int, str, float, complex}:
        return (type(value).__name__, repr(value))
    if type(value) is bytes:
        return ("bytes", value.hex())
    if type(value) is tuple:
        return ("tuple", tuple(_normalized_code_component_v3(row) for row in value))
    if type(value) is frozenset:
        return (
            "frozenset",
            tuple(sorted(repr(_normalized_code_component_v3(row)) for row in value)),
        )
    return (type(value).__module__, type(value).__qualname__, repr(value))


def _normalized_code_structure_v3(code: CodeType) -> tuple[Any, ...]:
    """Fingerprint executable semantics while ignoring file/line metadata."""

    return (
        "code-v1",
        code.co_name,
        code.co_argcount,
        getattr(code, "co_posonlyargcount", 0),
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code.hex(),
        tuple(_normalized_code_component_v3(row) for row in code.co_consts),
        tuple(code.co_names),
        tuple(code.co_varnames),
        tuple(code.co_freevars),
        tuple(code.co_cellvars),
        getattr(code, "co_exceptiontable", b"").hex(),
    )


def _normalized_recursive_code_fingerprint_v3(code: CodeType) -> str:
    return hashlib.sha256(repr(_normalized_code_structure_v3(code)).encode("utf-8")).hexdigest()


class _OwnedCapExhaustedV3(RuntimeError):
    def __init__(self, cap_name: str) -> None:
        super().__init__(cap_name)
        self.cap_name = cap_name


class _OwnedFallbackLedgerV3:
    """Exact V1 counters plus literal source-owned V4 primitive events."""

    def __init__(self, cap: GroundFallbackCapProfileV1) -> None:
        self.cap = cap
        self.states_expanded = 0
        self.actions_evaluated = 0
        self.ground_steps = 0
        self.outcome_rows = 0
        self.bellman_backups = 0
        self.composed_candidates = 0
        self.cap_checks = 0
        self.cap_rejections = 0

    def _guard(self, *checks: tuple[str, int, int]) -> None:
        if self.cap_checks >= self.cap.max_solver_cap_checks:
            self._reject("max_cap_checks")
        if (
            emit_owned_route_operation_v4(
                "direct-fallback.control.cap-check", 1
            )
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned cap-check event was not durably recorded"
            )
        self.cap_checks += 1
        for cap_name, proposed, maximum in checks:
            if proposed > maximum:
                self._reject(cap_name)

    def _reject(self, cap_name: str) -> None:
        if (
            emit_owned_route_operation_v4(
                "direct-fallback.control.cap-rejection", 1
            )
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned cap-rejection event was not durably recorded"
            )
        self.cap_rejections = 1
        raise _OwnedCapExhaustedV3(cap_name)

    def expand_state(self) -> None:
        self._guard(
            (
                "max_states_expanded",
                self.states_expanded + 1,
                self.cap.max_states_expanded,
            )
        )
        if (
            emit_owned_route_operation_v4("direct-fallback.state.expanded", 1)
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned state-expansion event was not durably recorded"
            )
        self.states_expanded += 1

    def evaluate_action(self) -> None:
        self._guard(
            (
                "max_actions_evaluated",
                self.actions_evaluated + 1,
                self.cap.max_actions_evaluated,
            )
        )
        if (
            emit_owned_route_operation_v4("direct-fallback.action.evaluated", 1)
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned action-evaluation event was not durably recorded"
            )
        self.actions_evaluated += 1

    def reserve_transition(self) -> None:
        self._guard(
            (
                "max_ground_steps",
                self.ground_steps + 1,
                self.cap.max_ground_steps,
            ),
            (
                "max_outcome_rows",
                self.outcome_rows + self.cap.max_positive_outcomes_per_step,
                self.cap.max_outcome_rows,
            ),
        )
        if (
            emit_owned_route_operation_v4("direct-fallback.kernel.transition", 1)
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned ground-step event was not durably recorded"
            )
        self.ground_steps += 1

    def record_outcomes(self, count: int) -> None:
        if count <= 0:
            raise GroundFallbackProtocolError(
                "owned ground fallback kernel returned no positive-probability outcome"
            )
        for _ in range(count):
            if (
                emit_owned_route_operation_v4("direct-fallback.outcome.row", 1)
                is not OWNED_ROUTE_EVENT_ACK_V4
            ):
                raise GroundFallbackProtocolError(
                    "owned outcome-row event was not durably recorded"
                )
            self.outcome_rows += 1
        if count > self.cap.max_positive_outcomes_per_step:
            raise GroundFallbackProtocolError(
                "owned kernel outcome count exceeded max_positive_outcomes_per_step"
            )
        if self.outcome_rows > self.cap.max_outcome_rows:
            raise AssertionError("pre-reserved owned outcome cap was violated")

    def compose_candidate(self) -> None:
        self._guard(
            (
                "max_composed_candidates",
                self.composed_candidates + 1,
                self.cap.max_composed_candidates,
            ),
            (
                "max_bellman_backups",
                self.bellman_backups + 1,
                self.cap.max_bellman_backups,
            ),
        )
        if (
            emit_owned_route_operation_v4("direct-fallback.bellman.backup", 1)
            is not OWNED_ROUTE_EVENT_ACK_V4
        ):
            raise GroundFallbackProtocolError(
                "owned Bellman-backup event was not durably recorded"
            )
        self.composed_candidates += 1
        self.bellman_backups += 1


class FrozenOwnedFallbackSourceBindingV3(NamedTuple):
    """Import-time identities joining the archived source to live owner code."""

    owner_class: type
    owner_globals: Mapping[str, Any]
    method_bindings: tuple[tuple[str, Any, Any], ...]
    gateway: Any
    gateway_globals: Mapping[str, Any]
    gateway_code: Any
    event_ack: object
    search_bind: Any
    search_bind_globals: Mapping[str, Any]
    search_bind_code: Any
    search_finish: Any
    search_finish_globals: Mapping[str, Any]
    search_finish_code: Any


_FROZEN_OWNED_LEDGER_CLASS_V3 = _OwnedFallbackLedgerV3
_FROZEN_OWNED_LEDGER_GLOBALS_V3 = globals()
_FROZEN_OWNED_LEDGER_METHODS_V3 = tuple(
    (
        name,
        getattr(_OwnedFallbackLedgerV3, name),
        getattr(_OwnedFallbackLedgerV3, name).__code__,
    )
    for name in (
        "__init__",
        "_guard",
        "_reject",
        "expand_state",
        "evaluate_action",
        "reserve_transition",
        "record_outcomes",
        "compose_candidate",
    )
)
_FROZEN_OWNED_LEDGER_GATEWAY_V3 = emit_owned_route_operation_v4
_FROZEN_OWNED_LEDGER_GATEWAY_GLOBALS_V3 = emit_owned_route_operation_v4.__globals__
_FROZEN_OWNED_LEDGER_GATEWAY_CODE_V3 = emit_owned_route_operation_v4.__code__
_FROZEN_OWNED_LEDGER_EVENT_ACK_V3 = OWNED_ROUTE_EVENT_ACK_V4
_FROZEN_OWNED_LEDGER_SEARCH_BIND_V3 = bind_owned_fallback_search_v4
_FROZEN_OWNED_LEDGER_SEARCH_BIND_GLOBALS_V3 = bind_owned_fallback_search_v4.__globals__
_FROZEN_OWNED_LEDGER_SEARCH_BIND_CODE_V3 = bind_owned_fallback_search_v4.__code__
_FROZEN_OWNED_LEDGER_SEARCH_FINISH_V3 = finish_owned_fallback_search_v4
_FROZEN_OWNED_LEDGER_SEARCH_FINISH_GLOBALS_V3 = (
    finish_owned_fallback_search_v4.__globals__
)
_FROZEN_OWNED_LEDGER_SEARCH_FINISH_CODE_V3 = finish_owned_fallback_search_v4.__code__


def require_frozen_owned_fallback_source_binding_v3(
    _owner_class: type = _FROZEN_OWNED_LEDGER_CLASS_V3,
    _owner_globals: Mapping[str, Any] = _FROZEN_OWNED_LEDGER_GLOBALS_V3,
    _method_bindings: tuple[tuple[str, Any, Any], ...] = (
        _FROZEN_OWNED_LEDGER_METHODS_V3
    ),
    _gateway: Any = _FROZEN_OWNED_LEDGER_GATEWAY_V3,
    _gateway_globals: Mapping[str, Any] = (
        _FROZEN_OWNED_LEDGER_GATEWAY_GLOBALS_V3
    ),
    _gateway_code: Any = _FROZEN_OWNED_LEDGER_GATEWAY_CODE_V3,
    _event_ack: object = _FROZEN_OWNED_LEDGER_EVENT_ACK_V3,
    _search_bind: Any = _FROZEN_OWNED_LEDGER_SEARCH_BIND_V3,
    _search_bind_globals: Mapping[str, Any] = (
        _FROZEN_OWNED_LEDGER_SEARCH_BIND_GLOBALS_V3
    ),
    _search_bind_code: Any = _FROZEN_OWNED_LEDGER_SEARCH_BIND_CODE_V3,
    _search_finish: Any = _FROZEN_OWNED_LEDGER_SEARCH_FINISH_V3,
    _search_finish_globals: Mapping[str, Any] = (
        _FROZEN_OWNED_LEDGER_SEARCH_FINISH_GLOBALS_V3
    ),
    _search_finish_code: Any = _FROZEN_OWNED_LEDGER_SEARCH_FINISH_CODE_V3,
) -> FrozenOwnedFallbackSourceBindingV3:
    """Reject runtime class/method/gateway replacement against import-time IDs."""

    if (
        globals() is not _owner_globals
        or globals().get("_OwnedFallbackLedgerV3") is not _owner_class
        or globals().get("emit_owned_route_operation_v4") is not _gateway
        or getattr(_gateway, "__globals__", None) is not _gateway_globals
        or getattr(_gateway, "__code__", None) is not _gateway_code
        or globals().get("OWNED_ROUTE_EVENT_ACK_V4") is not _event_ack
        or globals().get("bind_owned_fallback_search_v4") is not _search_bind
        or getattr(_search_bind, "__globals__", None) is not _search_bind_globals
        or getattr(_search_bind, "__code__", None) is not _search_bind_code
        or globals().get("finish_owned_fallback_search_v4") is not _search_finish
        or getattr(_search_finish, "__globals__", None)
        is not _search_finish_globals
        or getattr(_search_finish, "__code__", None) is not _search_finish_code
        or _owner_class.__module__ != __name__
        or _owner_class.__qualname__ != "_OwnedFallbackLedgerV3"
    ):
        raise GroundFallbackV1Error(
            "owned fallback live class or gateway differs from its import-time binding"
        )
    for method_name, frozen_function, frozen_code in _method_bindings:
        current = getattr(_owner_class, method_name, None)
        if (
            current is not frozen_function
            or getattr(current, "__code__", None) is not frozen_code
            or getattr(current, "__globals__", None) is not _owner_globals
            or getattr(current, "__module__", None) != __name__
            or getattr(current, "__qualname__", None)
            != f"_OwnedFallbackLedgerV3.{method_name}"
        ):
            raise GroundFallbackV1Error(
                "owned fallback live method differs from its import-time binding"
            )
    return FrozenOwnedFallbackSourceBindingV3(
        _owner_class,
        _owner_globals,
        _method_bindings,
        _gateway,
        _gateway_globals,
        _gateway_code,
        _event_ack,
        _search_bind,
        _search_bind_globals,
        _search_bind_code,
        _search_finish,
        _search_finish_globals,
        _search_finish_code,
    )


_FROZEN_OWNER_BINDING_VALIDATOR_OBJECT_V3 = (
    require_frozen_owned_fallback_source_binding_v3
)
_FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3 = (
    require_frozen_owned_fallback_source_binding_v3.__globals__
)
_FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3 = (
    require_frozen_owned_fallback_source_binding_v3.__code__
)


def _legacy_work_vector_v3(
    ledger: _OwnedFallbackLedgerV3,
    *,
    route_attempt_id: str,
    outcome: GroundFallbackOutcome,
    registry: CounterRegistryV1,
    recorder_id: str,
) -> WorkVectorV1:
    values = {path: 0 for path in registry.required_paths}
    success = int(outcome is not GroundFallbackOutcome.CAP_EXHAUSTED)
    failure = 1 - success
    values.update(
        {
            "fallback.states_expanded": ledger.states_expanded,
            "fallback.actions_evaluated": ledger.actions_evaluated,
            "fallback.ground_steps": ledger.ground_steps,
            "fallback.outcome_rows": ledger.outcome_rows,
            "fallback.bellman_backups": ledger.bellman_backups,
            "control.cap_checks": ledger.cap_checks,
            "control.cap_rejections": ledger.cap_rejections,
            "route.attempts": 1,
            "route.successes": success,
            "route.failures": failure,
            "solver.attempts": 1,
            "solver.successes": success,
            "solver.failures": failure,
        }
    )
    return registry.materialize(
        subject_id=route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        records=explicit_records_v1(registry, values, recorder_id=recorder_id),
    )


def run_owned_ground_fallback_search_v3(
    kernel: Any,
    query: Any,
    *,
    route_decision_context_id: str,
    decision_point_id: str,
    route_decision_id: str,
    selected_upper_id: str,
    route_attempt_id: str,
    query_id: str,
    cap_profile: GroundFallbackCapProfileV1,
    registry: CounterRegistryV1 | None = None,
    recorder_id: str = RECORDER_ID,
) -> GroundFallbackExecutionV1:
    """Run the independently copied exact search with owned primitive sites."""

    require_frozen_owned_fallback_engine_binding_v3()
    for field_name, value in (
        ("route_decision_context_id", route_decision_context_id),
        ("decision_point_id", decision_point_id),
        ("route_decision_id", route_decision_id),
        ("selected_upper_id", selected_upper_id),
        ("route_attempt_id", route_attempt_id),
        ("query_id", query_id),
    ):
        try:
            parse_content_id(value)
        except (TypeError, ValueError) as error:
            raise GroundFallbackV1Error(
                f"{field_name} must be a full Phase-3E content ID"
            ) from error
    if type(recorder_id) is not str or not recorder_id:
        raise GroundFallbackV1Error("recorder_id must be a nonempty string")
    GroundFallbackCapProfileV1.from_dict(cap_profile.to_dict())
    trusted_registry = registry or official_counter_registry_v1()
    trusted_registry.validate_official_catalogue()
    ledger = _OwnedFallbackLedgerV3(cap_profile)
    bind_owned_fallback_search_v4(ledger)
    validate_query(kernel, query)

    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    horizon = query_horizon(kernel, query)
    Distribution = tuple[tuple[Hashable, Fraction], ...]
    memo: dict[tuple[int, Distribution], tuple[ParetoPoint, ...]] = {}
    transition_cache: dict[tuple[Hashable, Hashable], tuple[Any, ...]] = {}
    evaluated_state_actions: set[tuple[int, Hashable, Hashable]] = set()
    expanded_state_times: set[tuple[int, Hashable]] = set()
    zero = ParetoPoint(Fraction(0), Fraction(0), FiniteHorizonPolicy(()))

    def canonical_distribution(masses: Mapping[Hashable, Fraction]) -> Distribution:
        return tuple(
            sorted(
                ((state, mass) for state, mass in masses.items() if mass > 0),
                key=lambda item: repr(item[0]),
            )
        )

    def outcomes_for(
        state: Hashable, action: Hashable, remaining: int
    ) -> tuple[Any, ...]:
        action_key = (remaining, state, action)
        if action_key not in evaluated_state_actions:
            ledger.evaluate_action()
            evaluated_state_actions.add(action_key)
        transition_key = (state, action)
        cached = transition_cache.get(transition_key)
        if cached is not None:
            return cached
        ledger.reserve_transition()
        outcomes = iter_outcomes(kernel, state, action)
        ledger.record_outcomes(len(outcomes))
        transition_cache[transition_key] = outcomes
        return outcomes

    def occupancy_frontier(
        distribution: Distribution, remaining: int
    ) -> tuple[ParetoPoint, ...]:
        key = (remaining, distribution)
        if key in memo:
            return memo[key]
        if remaining <= 0 or not distribution:
            memo[key] = (zero,)
            return memo[key]

        decision_states: list[Hashable] = []
        action_sets: list[tuple[Hashable, ...]] = []
        state_mass = dict(distribution)
        for state, mass in distribution:
            if mass <= 0 or is_stopped(kernel, state, goal):
                continue
            state_time = (remaining, state)
            if state_time not in expanded_state_times:
                ledger.expand_state()
                expanded_state_times.add(state_time)
            actions = deterministic_order(kernel.actions(state))
            if actions:
                decision_states.append(state)
                action_sets.append(actions)
        if not decision_states:
            memo[key] = (zero,)
            return memo[key]

        if remaining == 1:
            partial_frontier: tuple[ParetoPoint, ...] = (zero,)
            for state, actions in zip(decision_states, action_sets):
                mass = state_mass[state]
                extended: list[ParetoPoint] = []
                for partial in partial_frontier:
                    for action in actions:
                        ledger.compose_candidate()
                        immediate_reward = Fraction(0)
                        immediate_failure = Fraction(0)
                        for branch in outcomes_for(state, action, remaining):
                            probability = mass * as_fraction(branch.probability)
                            immediate_reward += probability * outcome_reward(
                                branch, weights
                            )
                            if branch.failure:
                                immediate_failure += probability
                        mapping = partial.policy.as_dict()
                        mapping[(remaining, state)] = action
                        extended.append(
                            ParetoPoint(
                                partial.expected_reward + immediate_reward,
                                partial.failure_probability + immediate_failure,
                                FiniteHorizonPolicy.from_mapping(mapping),
                            )
                        )
                partial_frontier = pareto_prune(extended)
            memo[key] = partial_frontier
            return memo[key]

        candidates: list[ParetoPoint] = []
        for chosen_actions in product(*action_sets):
            ledger.compose_candidate()
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[Hashable, Fraction] = {}
            current_decisions: list[tuple[tuple[int, Hashable], Hashable]] = []
            for state, action in zip(decision_states, chosen_actions):
                mass = state_mass[state]
                current_decisions.append(((remaining, state), action))
                for branch in outcomes_for(state, action, remaining):
                    probability = mass * as_fraction(branch.probability)
                    immediate_reward += probability * outcome_reward(branch, weights)
                    if branch.failure:
                        immediate_failure += probability
                        continue
                    stopped = branch.terminal or is_stopped(
                        kernel, branch.next_state, goal
                    )
                    if not stopped:
                        successor_mass[branch.next_state] = (
                            successor_mass.get(branch.next_state, Fraction(0))
                            + probability
                        )
            continuation_frontier = occupancy_frontier(
                canonical_distribution(successor_mass), remaining - 1
            )
            for continuation in continuation_frontier:
                ledger.compose_candidate()
                mapping = continuation.policy.as_dict()
                conflict = False
                for decision_key, action in current_decisions:
                    incumbent = mapping.get(decision_key)
                    if incumbent is not None and incumbent != action:
                        conflict = True
                        break
                    mapping[decision_key] = action
                if conflict:
                    continue
                candidates.append(
                    ParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        FiniteHorizonPolicy.from_mapping(mapping),
                    )
                )
        memo[key] = pareto_prune(candidates)
        return memo[key]

    cap_exhausted_name: str | None = None
    frontier: tuple[ParetoPoint, ...] = ()
    selected: ParetoPoint | None = None
    try:
        initial_mass: dict[Hashable, Fraction] = {}
        for probability, state in query_initial_distribution(kernel, query):
            initial_mass[state] = initial_mass.get(state, Fraction(0)) + probability
        frontier = occupancy_frontier(canonical_distribution(initial_mass), horizon)
        selected = select_constrained(frontier, as_fraction(getattr(query, "delta")))
        fallback_outcome = (
            GroundFallbackOutcome.FEASIBLE_CERTIFIED
            if selected is not None
            else GroundFallbackOutcome.INFEASIBLE_CERTIFIED
        )
    except _OwnedCapExhaustedV3 as exhausted:
        cap_exhausted_name = exhausted.cap_name
        fallback_outcome = GroundFallbackOutcome.CAP_EXHAUSTED
        frontier = ()
        selected = None
    except GroundFallbackProtocolError as error:
        error.partial_work_vector = _legacy_work_vector_v3(
            ledger,
            route_attempt_id=route_attempt_id,
            outcome=GroundFallbackOutcome.CAP_EXHAUSTED,
            registry=trusted_registry,
            recorder_id=recorder_id,
        )
        raise

    work_vector = _legacy_work_vector_v3(
        ledger,
        route_attempt_id=route_attempt_id,
        outcome=fallback_outcome,
        registry=trusted_registry,
        recorder_id=recorder_id,
    )
    result_frontier = tuple(
        GroundFallbackFrontierPointV1(
            point.expected_reward,
            point.failure_probability,
            _policy_content_signature(point.policy),
        )
        for point in frontier
    )
    result = GroundFallbackResultV1(
        route_decision_context_id,
        decision_point_id,
        route_decision_id,
        selected_upper_id,
        route_attempt_id,
        query_id,
        cap_profile.ground_fallback_cap_profile_id,
        work_vector.work_vector_id,
        fallback_outcome,
        fallback_outcome is not GroundFallbackOutcome.CAP_EXHAUSTED,
        result_frontier,
        _policy_content_signature(selected.policy) if selected is not None else (),
        selected.expected_reward if selected is not None else None,
        selected.failure_probability if selected is not None else None,
        cap_exhausted_name,
        ledger.composed_candidates,
    )
    execution = GroundFallbackExecutionV1(
        result,
        work_vector,
        selected.policy if selected is not None else None,
    )
    finish_owned_fallback_search_v4(ledger, execution)
    return execution


_FROZEN_SEARCH_ENTRY_OBJECT_V3 = run_owned_ground_fallback_search_v3
_FROZEN_SEARCH_ENTRY_GLOBALS_V3 = run_owned_ground_fallback_search_v3.__globals__
_FROZEN_SEARCH_ENTRY_CODE_V3 = run_owned_ground_fallback_search_v3.__code__
_FROZEN_WORK_VECTOR_HELPER_OBJECT_V3 = _legacy_work_vector_v3
_FROZEN_WORK_VECTOR_HELPER_GLOBALS_V3 = _legacy_work_vector_v3.__globals__
_FROZEN_WORK_VECTOR_HELPER_CODE_V3 = _legacy_work_vector_v3.__code__


def _walk_code_tree_v3(code: CodeType) -> tuple[CodeType, ...]:
    found = [code]
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            found.extend(_walk_code_tree_v3(constant))
    return tuple(found)


def _direct_runtime_names_v3(roots: tuple[CodeType, ...]) -> frozenset[str]:
    names: set[str] = set()
    for root in roots:
        for code in _walk_code_tree_v3(root):
            names.update(code.co_names)
    return frozenset(names)


def _descriptor_code_v3(descriptor: Any) -> tuple[Any, ...]:
    if isinstance(descriptor, (classmethod, staticmethod)):
        return (descriptor.__func__, getattr(descriptor.__func__, "__code__", None))
    if isinstance(descriptor, property):
        return tuple(
            (function, getattr(function, "__code__", None))
            for function in (descriptor.fget, descriptor.fset, descriptor.fdel)
            if function is not None
        )
    return (descriptor, getattr(descriptor, "__code__", None))


_FROZEN_RUNTIME_CODE_ROOTS_V3 = (
    *(row[2] for row in _FROZEN_OWNED_LEDGER_METHODS_V3),
    _FROZEN_WORK_VECTOR_HELPER_CODE_V3,
    _FROZEN_SEARCH_ENTRY_CODE_V3,
    _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3,
)
_FROZEN_DIRECT_RUNTIME_NAMES_V3 = _direct_runtime_names_v3(
    _FROZEN_RUNTIME_CODE_ROOTS_V3
)
_FROZEN_RUNTIME_GLOBAL_BINDINGS_V3 = tuple(
    sorted(
        (
            name,
            globals()[name],
            getattr(globals()[name], "__code__", None),
        )
        for name in _FROZEN_DIRECT_RUNTIME_NAMES_V3
        if name in globals()
    )
)
_FROZEN_RUNTIME_BUILTIN_BINDINGS_V3 = tuple(
    sorted(
        (
            name,
            getattr(builtins, name),
            getattr(getattr(builtins, name), "__code__", None),
        )
        for name in _FROZEN_DIRECT_RUNTIME_NAMES_V3
        if name not in globals() and hasattr(builtins, name)
    )
)
_FROZEN_RUNTIME_CLASS_SURFACES_V3 = tuple(
    (
        owner,
        tuple(
            (name, vars(owner).get(name), _descriptor_code_v3(vars(owner).get(name)))
            for name in names
        ),
    )
    for owner, names in (
        (
            CounterRegistryV1,
            (
                "required_paths",
                "registry_id",
                "validate_official_catalogue",
                "materialize",
            ),
        ),
        (
            GroundFallbackCapProfileV1,
            (
                "to_dict",
                "from_dict",
                "max_solver_cap_checks",
                "ground_fallback_cap_profile_id",
            ),
        ),
        (GroundFallbackExecutionV1, ("__init__", "__post_init__")),
        (
            GroundFallbackFrontierPointV1,
            ("__init__", "__post_init__", "to_dict"),
        ),
        (
            GroundFallbackResultV1,
            (
                "__init__",
                "__post_init__",
                "ground_fallback_result_id",
                "to_dict",
            ),
        ),
        (ParetoPoint, ("__init__",)),
        (
            FiniteHorizonPolicy,
            ("__init__", "as_dict", "from_mapping"),
        ),
        (WorkVectorV1, ("values", "work_vector_id", "to_dict")),
    )
)
_FROZEN_LIVE_CODE_FINGERPRINTS_V3 = tuple(
    sorted(
        (
            (f"_OwnedFallbackLedgerV3.{name}", _normalized_recursive_code_fingerprint_v3(code))
            for name, _function, code in _FROZEN_OWNED_LEDGER_METHODS_V3
        ),
        key=lambda row: row[0],
    )
    + sorted(
        (
            (
                "_legacy_work_vector_v3",
                _normalized_recursive_code_fingerprint_v3(
                    _FROZEN_WORK_VECTOR_HELPER_CODE_V3
                ),
            ),
            (
                "run_owned_ground_fallback_search_v3",
                _normalized_recursive_code_fingerprint_v3(_FROZEN_SEARCH_ENTRY_CODE_V3),
            ),
            (
                "require_frozen_owned_fallback_source_binding_v3",
                _normalized_recursive_code_fingerprint_v3(
                    _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3
                ),
            ),
        ),
        key=lambda row: row[0],
    )
)


class FrozenOwnedFallbackEngineBindingV3(NamedTuple):
    """Import-time live objects joined to the sealed V3 engine source."""

    source_binding: FrozenOwnedFallbackSourceBindingV3
    search_entry: Any
    search_entry_globals: Mapping[str, Any]
    search_entry_code: Any
    work_vector_helper: Any
    work_vector_helper_globals: Mapping[str, Any]
    work_vector_helper_code: Any
    source_validator: Any
    source_validator_globals: Mapping[str, Any]
    source_validator_code: Any
    runtime_global_bindings: tuple[tuple[str, Any, Any], ...]
    runtime_builtin_bindings: tuple[tuple[str, Any, Any], ...]
    runtime_class_surfaces: tuple[tuple[Any, tuple[Any, ...]], ...]
    live_code_fingerprints: tuple[tuple[str, str], ...]
    engine_validator: Any


def require_frozen_owned_fallback_engine_binding_v3(
    _search_entry: Any = _FROZEN_SEARCH_ENTRY_OBJECT_V3,
    _search_globals: Mapping[str, Any] = _FROZEN_SEARCH_ENTRY_GLOBALS_V3,
    _search_code: Any = _FROZEN_SEARCH_ENTRY_CODE_V3,
    _work_helper: Any = _FROZEN_WORK_VECTOR_HELPER_OBJECT_V3,
    _work_globals: Mapping[str, Any] = _FROZEN_WORK_VECTOR_HELPER_GLOBALS_V3,
    _work_code: Any = _FROZEN_WORK_VECTOR_HELPER_CODE_V3,
    _source_validator: Any = _FROZEN_OWNER_BINDING_VALIDATOR_OBJECT_V3,
    _source_validator_globals: Mapping[str, Any] = (
        _FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3
    ),
    _source_validator_code: Any = _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3,
    _runtime_globals: tuple[tuple[str, Any, Any], ...] = (
        _FROZEN_RUNTIME_GLOBAL_BINDINGS_V3
    ),
    _runtime_builtins: tuple[tuple[str, Any, Any], ...] = (
        _FROZEN_RUNTIME_BUILTIN_BINDINGS_V3
    ),
    _runtime_class_surfaces: tuple[tuple[Any, tuple[Any, ...]], ...] = (
        _FROZEN_RUNTIME_CLASS_SURFACES_V3
    ),
    _live_code_fingerprints: tuple[tuple[str, str], ...] = (
        _FROZEN_LIVE_CODE_FINGERPRINTS_V3
    ),
    _code_fingerprint: Any = _normalized_recursive_code_fingerprint_v3,
) -> FrozenOwnedFallbackEngineBindingV3:
    """Reject live engine/helper replacement against import-time objects."""

    verify_owned_fallback_engine_import_seal_v4(
        require_frozen_owned_fallback_engine_binding_v3,
        globals(),
    )
    if (
        globals() is not _search_globals
        or globals().get("run_owned_ground_fallback_search_v3") is not _search_entry
        or getattr(_search_entry, "__globals__", None) is not _search_globals
        or getattr(_search_entry, "__code__", None) is not _search_code
        or globals().get("_legacy_work_vector_v3") is not _work_helper
        or getattr(_work_helper, "__globals__", None) is not _work_globals
        or getattr(_work_helper, "__code__", None) is not _work_code
        or globals().get("require_frozen_owned_fallback_source_binding_v3")
        is not _source_validator
        or getattr(_source_validator, "__globals__", None)
        is not _source_validator_globals
        or getattr(_source_validator, "__code__", None) is not _source_validator_code
    ):
        raise GroundFallbackV1Error(
            "owned fallback engine differs from its import-time binding"
        )
    for name, frozen_object, frozen_code in _runtime_globals:
        current = _search_globals.get(name)
        if (
            current is not frozen_object
            or getattr(current, "__code__", None) is not frozen_code
        ):
            raise GroundFallbackV1Error(
                f"owned fallback runtime dependency {name!r} changed"
            )
    for name, frozen_object, frozen_code in _runtime_builtins:
        current = getattr(builtins, name, None)
        if (
            current is not frozen_object
            or getattr(current, "__code__", None) is not frozen_code
        ):
            raise GroundFallbackV1Error(
                f"owned fallback builtin dependency {name!r} changed"
            )
    for owner, surfaces in _runtime_class_surfaces:
        for name, frozen_descriptor, frozen_code in surfaces:
            current = vars(owner).get(name)
            if current is not frozen_descriptor or _descriptor_code_v3(current) != frozen_code:
                raise GroundFallbackV1Error(
                    "owned fallback runtime class surface changed"
                )
    source = _source_validator()
    complete_live_code_fingerprints = tuple(
        sorted(
            (
                *_live_code_fingerprints,
                (
                    "require_frozen_owned_fallback_engine_binding_v3",
                    _code_fingerprint(
                        require_frozen_owned_fallback_engine_binding_v3.__code__
                    ),
                ),
            )
        )
    )
    return FrozenOwnedFallbackEngineBindingV3(
        source,
        _search_entry,
        _search_globals,
        _search_code,
        _work_helper,
        _work_globals,
        _work_code,
        _source_validator,
        _source_validator_globals,
        _source_validator_code,
        _runtime_globals,
        _runtime_builtins,
        _runtime_class_surfaces,
        complete_live_code_fingerprints,
        require_frozen_owned_fallback_engine_binding_v3,
    )


seal_owned_fallback_engine_import_v4(
    require_frozen_owned_fallback_engine_binding_v3,
    globals(),
    (
        _FROZEN_SEARCH_ENTRY_OBJECT_V3,
        _FROZEN_SEARCH_ENTRY_GLOBALS_V3,
        _FROZEN_SEARCH_ENTRY_CODE_V3,
        _FROZEN_WORK_VECTOR_HELPER_OBJECT_V3,
        _FROZEN_WORK_VECTOR_HELPER_GLOBALS_V3,
        _FROZEN_WORK_VECTOR_HELPER_CODE_V3,
        _FROZEN_OWNER_BINDING_VALIDATOR_OBJECT_V3,
        _FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3,
        _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3,
        _FROZEN_RUNTIME_GLOBAL_BINDINGS_V3,
        _FROZEN_RUNTIME_BUILTIN_BINDINGS_V3,
        _FROZEN_RUNTIME_CLASS_SURFACES_V3,
        _FROZEN_LIVE_CODE_FINGERPRINTS_V3,
        _normalized_recursive_code_fingerprint_v3,
    ),
    _FROZEN_RUNTIME_GLOBAL_BINDINGS_V3,
    _FROZEN_RUNTIME_BUILTIN_BINDINGS_V3,
    _FROZEN_RUNTIME_CLASS_SURFACES_V3,
)


__all__ = (
    "CONSTRUCTION_ONLY",
    "FrozenOwnedFallbackEngineBindingV3",
    "FrozenOwnedFallbackSourceBindingV3",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_OWNER_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "RECORDER_ID",
    "SCHEMA_VERSION",
    "require_frozen_owned_fallback_engine_binding_v3",
    "require_frozen_owned_fallback_source_binding_v3",
    "run_owned_ground_fallback_search_v3",
)
