"""Exact direct-ground fallback after query-local recovery is exhausted.

This construction-only boundary consumes the exact result of the second and
final query-local transaction.  It opens no third local transaction.  Instead
it binds a fresh MATCHED_DIRECT_GROUND occurrence to the same committed
private environment, enumerates the complete registered H=2 ground model,
and solves the constrained ground problem with exact rational arithmetic.

The returned terminal is either a feasible full-ground plan certificate or a
complete exact-ground infeasibility certificate.  The construction fixture is
not official execution and carries no scientific endpoint credit.  Native
fallback work is retained separately from the two already-paid local
transactions; formal CounterRecord/WorkVector projection remains a later
accounting boundary.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp import construction_k7_query_bound_final_local_replanning_v1 as final_v1
from acfqp import construction_k7_query_bound_ground_transaction_v1 as ground_v1
from acfqp import v075_batch_native_statistical_backend_v1 as backend_v1
from acfqp import v075_k7_causal_promotion_construction_fixture_v1 as fixture_v1
from acfqp import v075_public_campaign_authority_v1 as public_v1
from acfqp import v075_public_graph_semantics_v1 as graph_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.h2_graph_transition_engine_v1 import (
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphTransitionAtomV1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_INVENTORY_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_POLICY_DECISION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_WORK_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.93"
PROFILE_KEY = "construction_k7_query_bound_direct_ground_fallback_v1"

ROW_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_ROW_V1_DOMAIN
INVENTORY_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_INVENTORY_V1_DOMAIN
POLICY_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_POLICY_DECISION_V1_DOMAIN
)
WORK_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_WORK_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_RESULT_V1_DOMAIN
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {
        ROW_DOMAIN,
        INVENTORY_DOMAIN,
        POLICY_DOMAIN,
        WORK_DOMAIN,
        RESULT_DOMAIN,
        VERIFICATION_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 6 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound direct-fallback domains are not central")

MAX_FALLBACK_STATES = 128
MAX_FALLBACK_ACTIONS = 1_024
MAX_FALLBACK_OUTCOME_ROWS = 16_384
MAX_FALLBACK_BELLMAN_BACKUPS = 65_536

_ROW_ISSUER = object()
_POLICY_ISSUER = object()
_WORK_ISSUER = object()
_RESULT_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7QueryBoundDirectGroundFallbackV1Error(ValueError):
    """The final-local predecessor or exact ground certificate changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundDirectGroundFallbackV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundDirectGroundFallbackV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("direct fallback arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


class QueryBoundDirectFallbackTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    INFEASIBILITY_CERTIFICATE = "INFEASIBILITY_CERTIFICATE"


class QueryBoundDirectFallbackTerminalCodeV1(str, Enum):
    FULL_GROUND_FALLBACK = "FULL_GROUND_FALLBACK"
    FULL_GROUND_EXACT_INFEASIBLE = "FULL_GROUND_EXACT_INFEASIBLE"


_AtomFact = tuple[
    str,
    tuple[int, ...],
    bool,
    bool,
    Fraction,
    Fraction,
    int,
    int,
]


@dataclass(frozen=True, slots=True)
class QueryBoundExactGroundRowV1:
    _issuer: InitVar[object]
    binding: graph_v1.V075ObservationRowBindingV1 = field(repr=False)
    atoms: tuple[H2GraphTransitionAtomV1, ...] = field(repr=False)
    _atom_facts: tuple[_AtomFact, ...] = field(init=False, repr=False)
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ROW_ISSUER
            or type(self.binding) is not graph_v1.V075ObservationRowBindingV1
            or type(self.atoms) is not tuple
            or not self.atoms
            or any(type(item) is not H2GraphTransitionAtomV1 for item in self.atoms)
            or sum((item.probability for item in self.atoms), Fraction(0)) != 1
            or len({item.realized_row_reward for item in self.atoms}) != 1
        ):
            _fail("exact direct-fallback row is malformed or caller-minted")
        facts = []
        for atom in self.atoms:
            state = graph_v1.V075SymbolicGraphStateV1(
                self.binding.context,
                atom.next_state.ranks,
                atom.failure,
            )
            facts.append(
                (
                    state.state_id,
                    atom.next_state.ranks,
                    atom.failure,
                    atom.terminal,
                    atom.probability,
                    atom.realized_row_reward,
                    atom.spawn_cell,
                    atom.spawn_rank,
                )
            )
        object.__setattr__(self, "_atom_facts", tuple(facts))
        object.__setattr__(self, "_row_id", content_id(ROW_DOMAIN, self._payload()))

    @property
    def reward(self) -> Fraction:
        return self._atom_facts[0][5]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_exact_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.binding.context_id,
            "state_id": self.binding.state_id,
            "remaining_horizon": self.binding.remaining_horizon,
            "action": list(self.binding.action),
            "row_binding_id": self.binding.row_binding_id,
            "atoms": [
                {
                    "next_state_id": item[0],
                    "next_ranks": list(item[1]),
                    "failure": item[2],
                    "terminal": item[3],
                    "probability": _fdoc(item[4]),
                    "realized_row_reward": _fdoc(item[5]),
                    "spawn_cell": item[6],
                    "spawn_rank": item[7],
                }
                for item in self._atom_facts
            ],
            "probability_mass": _fdoc(Fraction(1)),
            "exact_ground_transition_row": True,
        }

    @property
    def row_id(self) -> str:
        current = content_id(ROW_DOMAIN, self._payload())
        if current != self._row_id:
            _fail("exact direct-fallback row changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "exact_ground_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class QueryBoundExactGroundPolicyDecisionV1:
    _issuer: InitVar[object]
    state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]
    exact_ground_row_id: str
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.state_id, "fallback policy state")
        _cid(self.exact_ground_row_id, "fallback policy row")
        if (
            _issuer is not _POLICY_ISSUER
            or self.remaining_horizon not in (1, 2)
            or type(self.action) is not tuple
            or len(self.action) != 3
            or any(type(item) is not int for item in self.action)
            or self.action[0] >= self.action[1]
            or self.action[2] not in self.action[:2]
        ):
            _fail("exact direct-fallback policy decision is malformed")
        object.__setattr__(
            self,
            "_decision_id",
            content_id(POLICY_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_exact_ground_policy_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "exact_ground_row_id": self.exact_ground_row_id,
            "deterministic_ground_policy": True,
        }

    @property
    def decision_id(self) -> str:
        current = content_id(POLICY_DOMAIN, self._payload())
        if current != self._decision_id:
            _fail("exact direct-fallback policy decision changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class QueryBoundDirectFallbackWorkV1:
    _issuer: InitVar[object]
    states_expanded: int
    actions_evaluated: int
    ground_steps: int
    outcome_rows: int
    bellman_backups: int
    dominance_comparisons: int
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        values = (
            self.states_expanded,
            self.actions_evaluated,
            self.ground_steps,
            self.outcome_rows,
            self.bellman_backups,
            self.dominance_comparisons,
        )
        if (
            _issuer is not _WORK_ISSUER
            or any(type(item) is not int or item < 0 for item in values)
            or self.states_expanded > MAX_FALLBACK_STATES
            or self.actions_evaluated > MAX_FALLBACK_ACTIONS
            or self.ground_steps != self.actions_evaluated
            or self.outcome_rows > MAX_FALLBACK_OUTCOME_ROWS
            or self.bellman_backups > MAX_FALLBACK_BELLMAN_BACKUPS
        ):
            _fail("exact direct-fallback native work is malformed or over cap")
        object.__setattr__(self, "_work_id", content_id(WORK_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_direct_fallback_work.v1",
            "schema_version": SCHEMA_VERSION,
            "counters": {
                "fallback.states_expanded": self.states_expanded,
                "fallback.actions_evaluated": self.actions_evaluated,
                "fallback.ground_steps": self.ground_steps,
                "fallback.outcome_rows": self.outcome_rows,
                "fallback.bellman_backups": self.bellman_backups,
            },
            "diagnostic_dominance_comparisons": self.dominance_comparisons,
            "hard_caps": {
                "max_states_expanded": MAX_FALLBACK_STATES,
                "max_actions_evaluated": MAX_FALLBACK_ACTIONS,
                "max_ground_steps": MAX_FALLBACK_ACTIONS,
                "max_outcome_rows": MAX_FALLBACK_OUTCOME_ROWS,
                "max_bellman_backups": MAX_FALLBACK_BELLMAN_BACKUPS,
            },
            "native_counter_source": True,
            "formal_counter_records_materialized": False,
            "formal_work_vector_materialized": False,
        }

    @property
    def work_id(self) -> str:
        current = content_id(WORK_DOMAIN, self._payload())
        if current != self._work_id:
            _fail("exact direct-fallback work changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "fallback_work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class _GroundPoint:
    reward: Fraction
    failure: Fraction
    signature: tuple[tuple[str, int, tuple[int, int, int]], ...]


@dataclass(slots=True)
class _QueryBoundFallbackLedgerV1:
    """Source-owned exact fallback counters and stage-local hook sites."""

    states_expanded: int = 0
    actions_evaluated: int = 0
    ground_steps: int = 0
    outcome_rows: int = 0
    bellman_backups: int = 0
    dominance_comparisons: int = 0
    cap_checks: int = 0
    cap_rejections: int = 0
    route_started: bool = False
    route_finished: bool = False
    solver_started: bool = False
    solver_finished: bool = False

    def _guard(self, proposed: int, maximum: int, label: str) -> None:
        accounting_runtime.emit_owned_operation_v1(
            "query-fallback.control.cap-check"
        )
        self.cap_checks += 1
        if proposed > maximum:
            accounting_runtime.emit_owned_operation_v1(
                "query-fallback.control.cap-rejection"
            )
            self.cap_rejections += 1
            _fail(f"direct fallback {label} cap exhausted")

    def begin_route(self) -> None:
        if self.route_started:
            _fail("direct fallback route attempt was duplicated")
        self.route_started = True

    def finish_route(self, *, success: bool) -> None:
        if not self.route_started or self.route_finished or type(success) is not bool:
            _fail("direct fallback route terminal changed")
        accounting_runtime.emit_owned_operation_v1(
            (
                "query-fallback.route.success"
                if success
                else "query-fallback.route.failure"
            )
        )
        self.route_finished = True

    def begin_solver(self) -> None:
        if self.solver_started:
            _fail("direct fallback solver attempt was duplicated")
        self.solver_started = True

    def finish_solver(self, *, success: bool) -> None:
        if not self.solver_started or self.solver_finished or type(success) is not bool:
            _fail("direct fallback solver terminal changed")
        accounting_runtime.emit_owned_operation_v1(
            (
                "query-fallback.solver.success"
                if success
                else "query-fallback.solver.failure"
            )
        )
        self.solver_finished = True

    def expand_state(self) -> None:
        self._guard(
            self.states_expanded + 1,
            MAX_FALLBACK_STATES,
            "state-expansion",
        )
        accounting_runtime.emit_owned_operation_v1(
            "query-fallback.state.expanded"
        )
        self.states_expanded += 1

    def evaluate_action(self) -> None:
        self._guard(
            self.actions_evaluated + 1,
            MAX_FALLBACK_ACTIONS,
            "action-evaluation",
        )
        accounting_runtime.emit_owned_operation_v1(
            "query-fallback.action.evaluated"
        )
        self.actions_evaluated += 1

    def ground_step(self) -> None:
        self._guard(
            self.ground_steps + 1,
            MAX_FALLBACK_ACTIONS,
            "ground-step",
        )
        accounting_runtime.emit_owned_operation_v1(
            "query-fallback.kernel.transition"
        )
        self.ground_steps += 1

    def record_outcomes(self, count: int) -> None:
        if type(count) is not int or count <= 0:
            _fail("direct fallback exact row has no outcome atom")
        self._guard(
            self.outcome_rows + count,
            MAX_FALLBACK_OUTCOME_ROWS,
            "outcome-row",
        )
        for _ in range(count):
            accounting_runtime.emit_owned_operation_v1(
                "query-fallback.outcome.row"
            )
            self.outcome_rows += 1

    def bellman_backup(self) -> None:
        self._guard(
            self.bellman_backups + 1,
            MAX_FALLBACK_BELLMAN_BACKUPS,
            "Bellman-backup",
        )
        accounting_runtime.emit_owned_operation_v1(
            "query-fallback.bellman.backup"
        )
        self.bellman_backups += 1

    def dominance_comparison(self) -> None:
        self.dominance_comparisons += 1


def _pareto(
    points: Iterable[_GroundPoint],
    ledger: _QueryBoundFallbackLedgerV1,
) -> tuple[_GroundPoint, ...]:
    best_at_failure: dict[Fraction, _GroundPoint] = {}
    for item in points:
        prior = best_at_failure.get(item.failure)
        if prior is not None:
            ledger.dominance_comparison()
        if (
            prior is None
            or item.reward > prior.reward
            or (item.reward == prior.reward and item.signature < prior.signature)
        ):
            best_at_failure[item.failure] = item
    kept = []
    best_reward: Fraction | None = None
    for failure in sorted(best_at_failure):
        point = best_at_failure[failure]
        if best_reward is not None:
            ledger.dominance_comparison()
        if best_reward is not None and point.reward <= best_reward:
            continue
        kept.append(point)
        best_reward = point.reward
    return tuple(kept)


def _enumerate_exact_rows(
    *,
    context: public_v1.V075PublicReplicateContextV1,
    law: tuple[tuple[int, Fraction], ...],
    ledger: _QueryBoundFallbackLedgerV1,
) -> tuple[QueryBoundExactGroundRowV1, ...]:
    kernel = H2GraphKernelV1(
        context.topology,
        context.rank_cap,
        context.horizon,
        law,
    )
    root = graph_v1.root_catalogue_v1(context)
    rows: dict[tuple[str, int, tuple[int, int, int]], QueryBoundExactGroundRowV1] = {}
    children: dict[str, graph_v1.V075SymbolicGraphStateV1] = {}

    def add(
        catalogue: graph_v1.V075LegalActionCatalogueV1,
        action: tuple[int, int, int],
    ) -> None:
        ledger.evaluate_action()
        ledger.ground_step()
        binding = graph_v1.observation_row_binding_v1(context, catalogue, action)
        atoms = kernel.exact_atoms(
            catalogue.state.to_kernel_state(),
            H2GraphActionV1(*action),
            remaining_horizon=catalogue.remaining_horizon,
        )
        ledger.record_outcomes(len(atoms))
        row = QueryBoundExactGroundRowV1(_ROW_ISSUER, binding, atoms)
        key = (binding.state_id, binding.remaining_horizon, binding.action)
        if key in rows:
            _fail("direct fallback exact inventory duplicated one row")
        rows[key] = row
        if catalogue.remaining_horizon == 2:
            for atom in atoms:
                if atom.failure:
                    continue
                state = graph_v1.V075SymbolicGraphStateV1(
                    context,
                    atom.next_state.ranks,
                    False,
                )
                prior = children.setdefault(state.state_id, state)
                if prior != state:
                    _fail("direct fallback exact successor identity collided")

    ledger.expand_state()
    for action in root.actions:
        add(root, action)
    for state_id in sorted(children):
        ledger.expand_state()
        state = children[state_id]
        catalogue = graph_v1.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph_v1.legal_action_triples_v1(context, state.ranks, state.failure),
        )
        for action in catalogue.actions:
            add(catalogue, action)
    return tuple(sorted(rows.values(), key=lambda item: item.row_id))


def _solve_exact_ground(
    *,
    context: public_v1.V075PublicReplicateContextV1,
    rows: tuple[QueryBoundExactGroundRowV1, ...],
    risk_tolerance: Fraction,
    ledger: _QueryBoundFallbackLedgerV1,
) -> _GroundPoint | None:
    by_key = {
        (item.binding.state_id, item.binding.remaining_horizon, item.binding.action): item
        for item in rows
    }
    if len(by_key) != len(rows):
        _fail("direct fallback exact inventory key collision")
    root = graph_v1.root_catalogue_v1(context)
    all_points = []
    for root_action in root.actions:
        root_row = by_key[(root.state.state_id, 2, root_action)]
        environment_failure = sum(
            (item.probability for item in root_row.atoms if item.failure),
            Fraction(0),
        )
        child_weights: dict[str, Fraction] = {}
        child_states: dict[str, graph_v1.V075SymbolicGraphStateV1] = {}
        for atom in root_row.atoms:
            if atom.failure:
                continue
            state = graph_v1.V075SymbolicGraphStateV1(
                context,
                atom.next_state.ranks,
                False,
            )
            child_states[state.state_id] = state
            child_weights[state.state_id] = (
                child_weights.get(state.state_id, Fraction(0)) + atom.probability
            )
        points = (
            _GroundPoint(
                root_row.reward,
                environment_failure,
                ((root.state.state_id, 2, root_action),),
            ),
        )
        ledger.bellman_backup()
        for state_id in sorted(child_states):
            actions = graph_v1.legal_action_triples_v1(
                context,
                child_states[state_id].ranks,
                False,
            )
            expanded = []
            for point in points:
                for action in actions:
                    child = by_key[(state_id, 1, action)]
                    child_failure = sum(
                        (item.probability for item in child.atoms if item.failure),
                        Fraction(0),
                    )
                    expanded.append(
                        _GroundPoint(
                            point.reward + child_weights[state_id] * child.reward,
                            point.failure
                            + child_weights[state_id] * child_failure,
                            point.signature + ((state_id, 1, action),),
                        )
                    )
                    ledger.bellman_backup()
            points = _pareto(expanded, ledger)
        all_points.extend(points)
    feasible = tuple(
        item
        for item in _pareto(all_points, ledger)
        if item.failure <= risk_tolerance
    )
    if not feasible:
        return None
    return max(
        feasible,
        key=lambda item: (item.reward, -item.failure, item.signature),
    )


@dataclass(frozen=True, slots=True)
class QueryBoundDirectGroundFallbackV1:
    _issuer: InitVar[object]
    predecessor: final_v1.QueryBoundFinalLocalReplanningV1 = field(repr=False)
    occurrence_identity: backend_v1.V075BatchNativeOccurrenceIdentityV1
    environment_commitment: public_v1.V075OpaqueEnvironmentCommitmentV1
    reveal_verification: public_v1.V075EnvironmentRevealVerificationV1
    exact_rows: tuple[QueryBoundExactGroundRowV1, ...] = field(repr=False)
    policy: tuple[QueryBoundExactGroundPolicyDecisionV1, ...]
    selected_expected_reward: Fraction | None
    selected_failure_probability: Fraction | None
    work: QueryBoundDirectFallbackWorkV1
    terminal_class: QueryBoundDirectFallbackTerminalClassV1
    terminal_code: QueryBoundDirectFallbackTerminalCodeV1
    _inventory_id: str = field(init=False, repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.predecessor) is not final_v1.QueryBoundFinalLocalReplanningV1
            or type(self.occurrence_identity)
            is not backend_v1.V075BatchNativeOccurrenceIdentityV1
            or type(self.environment_commitment)
            is not public_v1.V075OpaqueEnvironmentCommitmentV1
            or type(self.reveal_verification)
            is not public_v1.V075EnvironmentRevealVerificationV1
            or self.reveal_verification.commitment != self.environment_commitment
            or not self.reveal_verification.matched
            or type(self.exact_rows) is not tuple
            or not self.exact_rows
            or any(type(item) is not QueryBoundExactGroundRowV1 for item in self.exact_rows)
            or tuple(item.row_id for item in self.exact_rows)
            != tuple(sorted({item.row_id for item in self.exact_rows}))
            or type(self.policy) is not tuple
            or any(
                type(item) is not QueryBoundExactGroundPolicyDecisionV1
                for item in self.policy
            )
            or type(self.work) is not QueryBoundDirectFallbackWorkV1
            or type(self.terminal_class) is not QueryBoundDirectFallbackTerminalClassV1
            or type(self.terminal_code) is not QueryBoundDirectFallbackTerminalCodeV1
        ):
            _fail("direct-ground fallback result is malformed or caller-minted")
        final_v1.require_query_bound_final_local_replanning_v1(self.predecessor)
        backend_v1.replay_v075_batch_native_occurrence_identity_v1(
            self.occurrence_identity
        )
        for row in self.exact_rows:
            row.__post_init__(_ROW_ISSUER)
        for decision in self.policy:
            decision.__post_init__(_POLICY_ISSUER)
        self.work.__post_init__(_WORK_ISSUER)
        predecessor_document = self.predecessor.to_document()
        frontier = self.predecessor.successor_proof.failed_frontier
        if (
            predecessor_document["local_allowed_after_result"] is not False
            or predecessor_document["local_forbidden_reason"]
            != "LOCAL_TRANSACTION_BUDGET_EXHAUSTED"
            or predecessor_document["next_required_action"]
            != "DIRECT_GROUND_FALLBACK"
            or frontier is None
            or any(item.next_registered_checkpoint is not None for item in frontier.obligations)
            or self.occurrence_identity.arm
            is not worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.occurrence_identity.context_id
            != self.predecessor.successor_model.context.context_id
            or self.work.actions_evaluated != len(self.exact_rows)
            or self.work.ground_steps != len(self.exact_rows)
            or self.work.outcome_rows != sum(len(item.atoms) for item in self.exact_rows)
        ):
            _fail("direct fallback crossed its final-local or exact inventory boundary")
        row_by_id = {item.row_id: item for item in self.exact_rows}
        for decision in self.policy:
            row = row_by_id.get(decision.exact_ground_row_id)
            if (
                row is None
                or row.binding.state_id != decision.state_id
                or row.binding.remaining_horizon != decision.remaining_horizon
                or row.binding.action != decision.action
            ):
                _fail("direct fallback policy crossed its exact row")
        feasible = self.terminal_class is QueryBoundDirectFallbackTerminalClassV1.PLAN_CERTIFICATE
        if (
            feasible
            != (
                self.terminal_code
                is QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_FALLBACK
                and bool(self.policy)
                and type(self.selected_expected_reward) is Fraction
                and type(self.selected_failure_probability) is Fraction
            )
            or (not feasible)
            != (
                self.terminal_code
                is QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_EXACT_INFEASIBLE
                and not self.policy
                and self.selected_expected_reward is None
                and self.selected_failure_probability is None
            )
        ):
            _fail("direct fallback terminal and exact policy disagree")
        object.__setattr__(
            self,
            "_inventory_id",
            content_id(INVENTORY_DOMAIN, self._inventory_payload()),
        )
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _inventory_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_exact_ground_inventory.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.occurrence_identity.context_id,
            "exact_ground_row_ids": [item.row_id for item in self.exact_rows],
            "state_count": self.work.states_expanded,
            "action_row_count": len(self.exact_rows),
            "outcome_row_count": sum(len(item.atoms) for item in self.exact_rows),
            "complete_h2_ground_closure": True,
        }

    @property
    def inventory_id(self) -> str:
        current = content_id(INVENTORY_DOMAIN, self._inventory_payload())
        if current != self._inventory_id:
            _fail("direct fallback exact inventory changed after issuance")
        return current

    def _payload(self) -> dict[str, Any]:
        threshold = worker_v1.V075WorkerThresholdProfileV1()
        feasible = self.terminal_class is QueryBoundDirectFallbackTerminalClassV1.PLAN_CERTIFICATE
        first_transaction = self.predecessor.transaction.predecessor.transaction
        cumulative_local_ground_draw_count = (
            first_transaction.total_ground_draw_count
            + self.predecessor.transaction.total_ground_draw_count
        )
        return {
            "schema": "acfqp.construction_k7_query_bound_direct_ground_fallback.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.predecessor.transaction.request.logical_occurrence_id,
            "reusable_abstract_query_id": self.predecessor.transaction.request.reusable_abstract_query_id,
            "final_local_replanning_id": self.predecessor.result_id,
            "failed_abstract_model_id": self.predecessor.successor_model.model_id,
            "failed_abstract_proof_id": self.predecessor.successor_proof.proof_id,
            "failed_abstract_frontier_id": self.predecessor.successor_proof.failed_frontier.frontier_id,
            "fallback_occurrence_id": self.occurrence_identity.occurrence_id,
            "fallback_target_tape_namespace_id": self.occurrence_identity.target_tape_namespace_id,
            "context_id": self.occurrence_identity.context_id,
            "route": worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND.value,
            "environment_commitment_id": self.environment_commitment.commitment_id,
            "environment_reveal_verification_id": self.reveal_verification.verification_id,
            "exact_ground_inventory_id": self.inventory_id,
            "policy_decision_ids": [item.decision_id for item in self.policy],
            "selected_expected_reward": (
                None if self.selected_expected_reward is None else _fdoc(self.selected_expected_reward)
            ),
            "selected_failure_probability": (
                None
                if self.selected_failure_probability is None
                else _fdoc(self.selected_failure_probability)
            ),
            "risk_tolerance": _fdoc(threshold.risk_tolerance),
            "normalized_regret_tolerance": _fdoc(threshold.normalized_regret_tolerance),
            "exact_normalized_regret": None if not feasible else _fdoc(Fraction(0)),
            "fallback_work_id": self.work.work_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "local_transaction_count": 2,
            "maximum_local_transactions_per_logical_occurrence": 2,
            "cumulative_local_ground_draw_count": cumulative_local_ground_draw_count,
            "transaction_3_created": False,
            "private_environment_reveal_matched": True,
            "private_law_accessed_by_fallback": True,
            "private_law_serialized": False,
            "complete_exact_h2_ground_inventory": True,
            "complete_exact_ground_search": True,
            "selected_policy_exactly_optimal_under_risk_constraint": feasible,
            "full_ground_infeasibility_proved": not feasible,
            "plan_certificate_issued": feasible,
            "infeasibility_certificate_issued": not feasible,
            "construction_only": True,
            "scientific_endpoint_credit_allowed": False,
            "formal_counter_records_materialized": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "next_required_action": "MATERIALIZE_K7_COUNTER_RECORDS_AND_OCCURRENCE_CLOSURE",
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("direct fallback result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_identity": self.occurrence_identity.to_document(),
            "environment_commitment": self.environment_commitment.to_document(),
            "environment_reveal_verification": self.reveal_verification.to_document(),
            "exact_ground_inventory": {
                **self._inventory_payload(),
                "exact_ground_rows": [item.to_document() for item in self.exact_rows],
                "exact_ground_inventory_id": self.inventory_id,
            },
            "policy": [item.to_document() for item in self.policy],
            "work": self.work.to_document(),
            "query_bound_direct_ground_fallback_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _build_direct_fallback(
    predecessor: final_v1.QueryBoundFinalLocalReplanningV1,
) -> QueryBoundDirectGroundFallbackV1:
    predecessor = final_v1.require_query_bound_final_local_replanning_v1(predecessor)
    ledger = _QueryBoundFallbackLedgerV1()
    ledger.begin_route()
    try:
        result = _build_direct_fallback_under_ledger(predecessor, ledger)
    except BaseException:
        if ledger.solver_started and not ledger.solver_finished:
            ledger.finish_solver(success=False)
        if not ledger.route_finished:
            ledger.finish_route(success=False)
        raise
    ledger.finish_route(success=True)
    return result


def _build_direct_fallback_under_ledger(
    predecessor: final_v1.QueryBoundFinalLocalReplanningV1,
    ledger: _QueryBoundFallbackLedgerV1,
) -> QueryBoundDirectGroundFallbackV1:
    predecessor_document = predecessor.to_document()
    frontier = predecessor.successor_proof.failed_frontier
    if (
        predecessor_document["local_allowed_after_result"] is not False
        or predecessor_document["next_required_action"] != "DIRECT_GROUND_FALLBACK"
        or frontier is None
        or any(item.next_registered_checkpoint is not None for item in frontier.obligations)
    ):
        _fail("direct fallback requires an exhausted failed final-local result")
    prepared = fixture_v1.prepare_v075_k7_construction_environment_v1(
        environment_marker=ground_v1.ENVIRONMENT_MARKER,
        identity_marker=predecessor.result_id,
    )
    model = predecessor.successor_model
    contexts = tuple(
        item
        for item in prepared.namespace.family.replicate_contexts
        if item.context_id == model.context.context_id
    )
    first_transaction = predecessor.transaction.predecessor.transaction
    if (
        len(contexts) != 1
        or contexts[0] != model.context
        or prepared.namespace.family.generation_id
        != first_transaction.namespace_binding.private_environment_generation_id
        or prepared.namespace.family.generation_id
        != predecessor.transaction.namespace_binding.private_environment_generation_id
        or prepared.namespace.target_tape_namespace_id
        in {
            first_transaction.native_occurrence.target_tape_namespace_id,
            predecessor.transaction.native_occurrence.target_tape_namespace_id,
        }
    ):
        _fail("direct fallback environment or fresh namespace crossed local recovery")
    context = contexts[0]
    arm = worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    occurrence = backend_v1.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
        namespace=prepared.namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=tuple(worker_v1.V075WorkerArmV1).index(arm),
        threshold_profile=prepared.namespace.workload.threshold_profile,
        cap_profile=prepared.namespace.workload.cap_profile,
        source_prior_transport=None,
    )
    laws = prepared.generated_environment.secret_laws_for_commitment()
    reveal = public_v1.verify_opaque_environment_reveal_v1(
        commitment=prepared.namespace.environment_commitment,
        secret_salt=prepared.private_salt,
        secret_laws=laws,
    )
    if not reveal.matched:
        _fail("direct fallback private environment does not match its commitment")
    context_index = prepared.namespace.family.replicate_contexts.index(context)
    rows = _enumerate_exact_rows(
        context=context,
        law=laws[context_index],
        ledger=ledger,
    )
    threshold = worker_v1.V075WorkerThresholdProfileV1()
    ledger.begin_solver()
    optimum = _solve_exact_ground(
        context=context,
        rows=rows,
        risk_tolerance=threshold.risk_tolerance,
        ledger=ledger,
    )
    ledger.finish_solver(success=True)
    rows_by_key = {
        (item.binding.state_id, item.binding.remaining_horizon, item.binding.action): item
        for item in rows
    }
    policy = ()
    if optimum is not None:
        policy = tuple(
            QueryBoundExactGroundPolicyDecisionV1(
                _POLICY_ISSUER,
                state_id,
                remaining_horizon,
                action,
                rows_by_key[(state_id, remaining_horizon, action)].row_id,
            )
            for state_id, remaining_horizon, action in optimum.signature
        )
    work = QueryBoundDirectFallbackWorkV1(
        _WORK_ISSUER,
        ledger.states_expanded,
        ledger.actions_evaluated,
        ledger.ground_steps,
        ledger.outcome_rows,
        ledger.bellman_backups,
        ledger.dominance_comparisons,
    )
    feasible = optimum is not None
    return QueryBoundDirectGroundFallbackV1(
        _RESULT_ISSUER,
        predecessor,
        occurrence,
        prepared.namespace.environment_commitment,
        reveal,
        rows,
        policy,
        None if optimum is None else optimum.reward,
        None if optimum is None else optimum.failure,
        work,
        (
            QueryBoundDirectFallbackTerminalClassV1.PLAN_CERTIFICATE
            if feasible
            else QueryBoundDirectFallbackTerminalClassV1.INFEASIBILITY_CERTIFICATE
        ),
        (
            QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_FALLBACK
            if feasible
            else QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_EXACT_INFEASIBLE
        ),
    )


def execute_query_bound_direct_ground_fallback_v1(
    predecessor: final_v1.QueryBoundFinalLocalReplanningV1,
) -> QueryBoundDirectGroundFallbackV1:
    """Execute the complete construction-only exact ground fallback."""

    return _build_direct_fallback(predecessor)


@dataclass(frozen=True, slots=True)
class QueryBoundDirectGroundFallbackVerificationV1:
    _issuer: InitVar[object]
    fallback_result_id: str
    final_local_replanning_id: str
    logical_occurrence_id: str
    fallback_occurrence_id: str
    exact_ground_inventory_id: str
    fallback_work_id: str
    terminal_class: QueryBoundDirectFallbackTerminalClassV1
    terminal_code: QueryBoundDirectFallbackTerminalCodeV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.fallback_result_id, "verified fallback result"),
            (self.final_local_replanning_id, "verified final-local result"),
            (self.logical_occurrence_id, "verified logical occurrence"),
            (self.fallback_occurrence_id, "verified fallback occurrence"),
            (self.exact_ground_inventory_id, "verified exact inventory"),
            (self.fallback_work_id, "verified fallback work"),
        ):
            _cid(value, label)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.terminal_class) is not QueryBoundDirectFallbackTerminalClassV1
            or type(self.terminal_code) is not QueryBoundDirectFallbackTerminalCodeV1
        ):
            _fail("direct fallback verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_direct_ground_fallback_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "fallback_result_id": self.fallback_result_id,
            "final_local_replanning_id": self.final_local_replanning_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "fallback_occurrence_id": self.fallback_occurrence_id,
            "exact_ground_inventory_id": self.exact_ground_inventory_id,
            "fallback_work_id": self.fallback_work_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "final_local_result_exactly_recomputed": True,
            "committed_private_environment_reveal_reverified": True,
            "complete_exact_h2_inventory_rebuilt": True,
            "constrained_ground_optimum_recomputed": True,
            "result_bytes_exactly_matched": True,
            "verification_lane": "EVALUATION",
            "verification_work_included_in_operational_fallback_work": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("direct fallback verification changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_query_bound_direct_ground_fallback_v1(
    claimed: QueryBoundDirectGroundFallbackV1,
) -> QueryBoundDirectGroundFallbackVerificationV1:
    """Rebuild the committed exact ground problem and compare full bytes."""

    if type(claimed) is not QueryBoundDirectGroundFallbackV1:
        _fail("direct fallback verifier requires one exact result type")
    final_v1.verify_query_bound_final_local_replanning_v1(claimed.predecessor)
    expected = _build_direct_fallback(claimed.predecessor)
    if expected.canonical_bytes != claimed.canonical_bytes:
        _fail("direct fallback result differs from complete exact recomputation")
    return QueryBoundDirectGroundFallbackVerificationV1(
        _VERIFICATION_ISSUER,
        claimed.result_id,
        claimed.predecessor.result_id,
        claimed.predecessor.transaction.request.logical_occurrence_id,
        claimed.occurrence_identity.occurrence_id,
        claimed.inventory_id,
        claimed.work.work_id,
        claimed.terminal_class,
        claimed.terminal_code,
    )


__all__ = [
    "ConstructionK7QueryBoundDirectGroundFallbackV1Error",
    "LOCAL_DOMAINS",
    "MAX_FALLBACK_ACTIONS",
    "MAX_FALLBACK_BELLMAN_BACKUPS",
    "MAX_FALLBACK_OUTCOME_ROWS",
    "MAX_FALLBACK_STATES",
    "QueryBoundDirectFallbackTerminalClassV1",
    "QueryBoundDirectFallbackTerminalCodeV1",
    "QueryBoundDirectFallbackWorkV1",
    "QueryBoundDirectGroundFallbackV1",
    "QueryBoundDirectGroundFallbackVerificationV1",
    "QueryBoundExactGroundPolicyDecisionV1",
    "QueryBoundExactGroundRowV1",
    "execute_query_bound_direct_ground_fallback_v1",
    "verify_query_bound_direct_ground_fallback_v1",
]
