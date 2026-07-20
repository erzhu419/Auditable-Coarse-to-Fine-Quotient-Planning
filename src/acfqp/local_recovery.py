"""Proof-directed, query-scoped local ground recovery.

This module deliberately does *not* rebuild a reusable abstract planning
model.  A :class:`HybridPolicyOverlay` belongs to one query and delegates to
the frozen abstract policy everywhere except a proof-authorized set of
cell--horizon pairs.  The local worker sees only an allowlisted kernel slice;
the authoritative kernel is used again only by :func:`audit_hybrid_policy`.

All certificate arithmetic is exact.  In particular, the failed-proof
frontier is derived from one-step (``direct``) realization residuals rather
than recursively accumulated root bounds.  Otherwise every failed proof
would incorrectly make its root the frontier and local recovery would collapse
into a disguised ground replan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Hashable, Iterable, Mapping

from acfqp.abstraction.quotient import ExactRealizationEnvelope, GroundRealization
from acfqp.artifacts import object_id
from acfqp.planning.audit import (
    AbstractPolicyAudit,
    AuditIssue,
    CellPolicyBound,
    unrestricted_upper_envelope,
)
from acfqp.planning.common import (
    as_fraction,
    is_stopped,
    iter_outcomes,
    outcome_reward,
    query_horizon,
    query_initial_distribution,
    reward_weights,
    validate_query,
)
from acfqp.planning.ground import PolicyEvaluation, evaluate_ground_policy
from acfqp.planning.policy import FiniteHorizonPolicy


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _fraction_payload(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _state_id(state: Hashable) -> str:
    return object_id(state, "state")


def _action_id(action: Hashable) -> str:
    return object_id(action, "ground-action")


def _node_id(cell: Hashable, remaining: int) -> str:
    return object_id(
        {"cell": repr(cell), "remaining": remaining},
        "proof-node",
    )


def _successor_tv(left: GroundRealization, right: GroundRealization) -> Fraction:
    left_mass = dict(left.successor_probabilities)
    right_mass = dict(right.successor_probabilities)
    support = set(left_mass) | set(right_mass)
    return sum(
        (
            abs(left_mass.get(cell, Fraction(0)) - right_mass.get(cell, Fraction(0)))
            for cell in support
        ),
        Fraction(0),
    ) / 2


@dataclass(frozen=True, slots=True)
class ProofWitness:
    """One complete unordered realization-pair comparison at a proof node."""

    witness_id: str
    left_state: Hashable
    right_state: Hashable
    normalized_reward_gap: Fraction
    failure_gap: Fraction
    successor_tv: Fraction

    @property
    def separates(self) -> bool:
        return bool(
            self.normalized_reward_gap or self.failure_gap or self.successor_tv
        )


@dataclass(frozen=True, slots=True)
class ProofNode:
    """A reachable selected-action proof obligation.

    ``direct_bad`` means that the selected semantic action has a non-singleton
    Bellman realization in a channel that actually failed the plan certificate.
    Raw successor TV is retained as evidence but is not itself sufficient when
    all affected continuation bounds agree. ``inherited_bad`` means that a
    strict descendant has such a residual. A node may have both properties;
    only ``direct_bad`` participates in the earliest failed-proof frontier.
    """

    node_id: str
    cell: Hashable
    remaining: int
    selected_action: Hashable | None
    normalized_reward_min: Fraction
    normalized_reward_max: Fraction
    normalized_reward_range: Fraction
    failure_min: Fraction
    failure_max: Fraction
    failure_range: Fraction
    max_pair_successor_tv: Fraction
    direct_bad: bool
    inherited_bad: bool
    audit_reward_lower: Fraction | None
    audit_failure_upper: Fraction | None
    witnesses: tuple[ProofWitness, ...]
    issue_codes: tuple[str, ...] = ()

    @property
    def reward_range(self) -> Fraction:
        return self.normalized_reward_range

    @property
    def successor_tv(self) -> Fraction:
        return self.max_pair_successor_tv

    @property
    def bad(self) -> bool:
        return self.direct_bad or self.inherited_bad or bool(self.issue_codes)


@dataclass(frozen=True, slots=True)
class ProofEdge:
    """A selected-action dependency edge with exact mass bounds."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    probability_lower: Fraction
    probability_upper: Fraction
    supporting_state_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FailedProofFrontier:
    """The antichain of DirectBad nodes with no strict DirectBad ancestor."""

    graph_id: str
    nodes: tuple[ProofNode, ...]
    frontier_id: str

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.nodes)

    @property
    def cell_horizon_pairs(self) -> tuple[tuple[Hashable, int], ...]:
        return tuple((node.cell, node.remaining) for node in self.nodes)


@dataclass(frozen=True, slots=True)
class FailedProofGraph:
    """Complete reachable proof dependency DAG for one candidate plan."""

    nodes: tuple[ProofNode, ...]
    edges: tuple[ProofEdge, ...]
    root_node_ids: tuple[str, ...]
    audit_certified: bool
    graph_id: str

    def node(self, node_id: str) -> ProofNode:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(f"unknown proof node {node_id!r}")

    @property
    def direct_bad_nodes(self) -> tuple[ProofNode, ...]:
        return tuple(node for node in self.nodes if node.direct_bad)

    @property
    def inherited_bad_nodes(self) -> tuple[ProofNode, ...]:
        return tuple(node for node in self.nodes if node.inherited_bad)

    def frontier(self) -> FailedProofFrontier:
        direct = {node.node_id for node in self.nodes if node.direct_bad}
        outgoing: dict[str, tuple[str, ...]] = {}
        for node in self.nodes:
            outgoing[node.node_id] = tuple(
                edge.target_node_id
                for edge in self.edges
                if edge.source_node_id == node.node_id
            )

        def has_strict_direct_ancestor(target: str) -> bool:
            pending = [(root, False) for root in self.root_node_ids]
            seen: set[tuple[str, bool]] = set()
            while pending:
                current, seen_direct = pending.pop()
                marker = (current, seen_direct)
                if marker in seen:
                    continue
                seen.add(marker)
                if current == target:
                    if seen_direct:
                        return True
                    continue
                next_seen = seen_direct or current in direct
                pending.extend((child, next_seen) for child in outgoing.get(current, ()))
            return False

        selected = (
            ()
            if self.audit_certified
            else tuple(
                sorted(
                    (
                        node
                        for node in self.nodes
                        if node.direct_bad
                        and not has_strict_direct_ancestor(node.node_id)
                    ),
                    key=lambda item: (-item.remaining, repr(item.cell), item.node_id),
                )
            )
        )
        payload = {
            "graph_id": self.graph_id,
            "node_ids": tuple(node.node_id for node in selected),
        }
        return FailedProofFrontier(
            graph_id=self.graph_id,
            nodes=selected,
            frontier_id=object_id(payload, "failed-proof-frontier"),
        )


def build_failed_proof_graph(
    kernel: Any,
    query: Any,
    envelope: ExactRealizationEnvelope,
    policy: FiniteHorizonPolicy[Any, Any],
    audit: AbstractPolicyAudit,
) -> FailedProofGraph:
    """Build the deterministic direct/inherited failed-proof graph.

    Every unordered pair of selected-action realizations is retained as a
    witness, including zero-distance pairs.  Keeping the complete inventory is
    important: a verifier can recompute the maxima and detect selective witness
    omission rather than trusting a claimed counterexample.
    """

    validate_query(kernel, query)
    if envelope.horizon != int(kernel.horizon):
        raise ValueError("envelope and kernel horizons disagree")
    partition = envelope.partition
    horizon = query_horizon(kernel, query)
    weights = reward_weights(query)
    audit_bounds = {
        (bound.remaining, bound.cell): bound for bound in audit.reachable_bounds
    }
    audit_issues: dict[tuple[int, Hashable], list[str]] = {}
    for issue in audit.issues:
        audit_issues.setdefault((issue.remaining, issue.cell), []).append(issue.code)
    value_obligation_failed = bool(
        audit.regret_upper is None
        or audit.regret_upper > audit.regret_tolerance
    )
    risk_obligation_failed = bool(
        audit.lifted_failure_upper is None
        or audit.lifted_failure_upper > audit.risk_tolerance
    )

    roots = tuple(
        sorted(
            {
                _node_id(partition.cell_of(state), horizon)
                for probability, state in query_initial_distribution(kernel, query)
                if probability > 0 and horizon > 0 and not is_stopped(kernel, state, getattr(query, "goal", None))
            }
        )
    )
    pending: list[tuple[int, Hashable]] = [
        (horizon, partition.cell_of(state))
        for probability, state in query_initial_distribution(kernel, query)
        if probability > 0 and horizon > 0 and not is_stopped(kernel, state, getattr(query, "goal", None))
    ]
    discovered: set[tuple[int, Hashable]] = set()
    raw_nodes: dict[tuple[int, Hashable], dict[str, Any]] = {}
    raw_edges: dict[tuple[str, str], dict[str, Any]] = {}

    while pending:
        remaining, cell = pending.pop()
        key = (remaining, cell)
        if key in discovered or remaining <= 0:
            continue
        discovered.add(key)
        node_id = _node_id(cell, remaining)
        issues = tuple(sorted(set(audit_issues.get(key, ()))))
        try:
            selected_action: Hashable | None = policy.action(cell, remaining)
            realizations = tuple(
                sorted(
                    envelope.realizations(cell, selected_action),
                    key=lambda value: (
                        repr(value.state),
                        repr(value.reward_features),
                        repr(value.successor_probabilities),
                    ),
                )
            )
        except KeyError:
            selected_action = None
            realizations = ()

        rewards: list[Fraction] = []
        failures: list[Fraction] = []
        missing_continuation_bound = False
        for realization in realizations:
            reward = realization.reward(weights)
            failure = realization.failure_probability
            if remaining > 1:
                for successor, probability in realization.successor_probabilities:
                    bound = audit_bounds.get((remaining - 1, successor))
                    if bound is None:
                        missing_continuation_bound = True
                        continue
                    reward += probability * bound.reward_lower
                    failure += probability * bound.failure_upper
            rewards.append(reward)
            failures.append(failure)
        if missing_continuation_bound:
            issues = tuple(sorted(set((*issues, "BOUNDARY_PROOF_MISSING"))))
        witnesses: list[ProofWitness] = []
        for left_index, left in enumerate(realizations):
            for right in realizations[left_index + 1 :]:
                reward_gap = abs(left.reward(weights) - right.reward(weights))
                failure_gap = abs(left.failure_probability - right.failure_probability)
                tv = _successor_tv(left, right)
                witness_payload = {
                    "node_id": node_id,
                    "left_state_id": _state_id(left.state),
                    "right_state_id": _state_id(right.state),
                    "normalized_reward_gap": reward_gap,
                    "failure_gap": failure_gap,
                    "successor_tv": tv,
                }
                witnesses.append(
                    ProofWitness(
                        witness_id=object_id(witness_payload, "proof-witness"),
                        left_state=left.state,
                        right_state=right.state,
                        normalized_reward_gap=reward_gap,
                        failure_gap=failure_gap,
                        successor_tv=tv,
                    )
                )
        witnesses.sort(
            key=lambda item: (
                _state_id(item.left_state),
                _state_id(item.right_state),
                item.witness_id,
            )
        )
        reward_min = min(rewards) if rewards else Fraction(0)
        reward_max = max(rewards) if rewards else Fraction(0)
        failure_min = min(failures) if failures else Fraction(0)
        failure_max = max(failures) if failures else Fraction(0)
        max_tv = max((witness.successor_tv for witness in witnesses), default=Fraction(0))
        direct_bad = bool(
            (value_obligation_failed and reward_max - reward_min)
            or (risk_obligation_failed and failure_max - failure_min)
            or issues
            or selected_action is None
        )
        bound = audit_bounds.get(key)
        raw_nodes[key] = {
            "node_id": node_id,
            "cell": cell,
            "remaining": remaining,
            "selected_action": selected_action,
            "reward_min": reward_min,
            "reward_max": reward_max,
            "failure_min": failure_min,
            "failure_max": failure_max,
            "max_tv": max_tv,
            "direct_bad": direct_bad,
            "bound": bound,
            "witnesses": tuple(witnesses),
            "issues": issues,
        }

        if selected_action is None or remaining <= 1:
            continue
        successor_states: dict[Hashable, list[tuple[Hashable, Fraction]]] = {}
        for realization in realizations:
            for successor, probability in realization.successor_probabilities:
                if probability > 0:
                    successor_states.setdefault(successor, []).append(
                        (realization.state, probability)
                    )
        for successor in sorted(successor_states, key=repr):
            target_id = _node_id(successor, remaining - 1)
            observations = successor_states[successor]
            by_state = {state: probability for state, probability in observations}
            all_states = tuple(realization.state for realization in realizations)
            masses = tuple(by_state.get(state, Fraction(0)) for state in all_states)
            edge_payload = {
                "source_node_id": node_id,
                "target_node_id": target_id,
                "probability_lower": min(masses, default=Fraction(0)),
                "probability_upper": max(masses, default=Fraction(0)),
                "supporting_state_ids": tuple(
                    sorted(_state_id(state) for state, probability in observations if probability > 0)
                ),
            }
            raw_edges[(node_id, target_id)] = edge_payload
            pending.append((remaining - 1, successor))

    edges = tuple(
        ProofEdge(
            edge_id=object_id(payload, "proof-edge"),
            source_node_id=payload["source_node_id"],
            target_node_id=payload["target_node_id"],
            probability_lower=payload["probability_lower"],
            probability_upper=payload["probability_upper"],
            supporting_state_ids=payload["supporting_state_ids"],
        )
        for _, payload in sorted(raw_edges.items())
    )
    outgoing: dict[str, tuple[str, ...]] = {}
    for record in raw_nodes.values():
        outgoing[record["node_id"]] = tuple(
            edge.target_node_id
            for edge in edges
            if edge.source_node_id == record["node_id"]
        )
    direct_ids = {
        record["node_id"] for record in raw_nodes.values() if record["direct_bad"]
    }

    def inherited(node_id: str) -> bool:
        pending_ids = list(outgoing.get(node_id, ()))
        seen: set[str] = set()
        while pending_ids:
            current = pending_ids.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in direct_ids:
                return True
            pending_ids.extend(outgoing.get(current, ()))
        return False

    nodes = tuple(
        ProofNode(
            node_id=record["node_id"],
            cell=record["cell"],
            remaining=record["remaining"],
            selected_action=record["selected_action"],
            normalized_reward_min=record["reward_min"],
            normalized_reward_max=record["reward_max"],
            normalized_reward_range=record["reward_max"] - record["reward_min"],
            failure_min=record["failure_min"],
            failure_max=record["failure_max"],
            failure_range=record["failure_max"] - record["failure_min"],
            max_pair_successor_tv=record["max_tv"],
            direct_bad=record["direct_bad"],
            inherited_bad=inherited(record["node_id"]),
            audit_reward_lower=(
                record["bound"].reward_lower if record["bound"] is not None else None
            ),
            audit_failure_upper=(
                record["bound"].failure_upper if record["bound"] is not None else None
            ),
            witnesses=record["witnesses"],
            issue_codes=record["issues"],
        )
        for _, record in sorted(
            raw_nodes.items(), key=lambda item: (-item[0][0], repr(item[0][1]))
        )
    )
    graph_payload = {
        "root_node_ids": roots,
        "nodes": tuple(
            {
                "node_id": node.node_id,
                "direct_bad": node.direct_bad,
                "inherited_bad": node.inherited_bad,
                "reward_range": node.normalized_reward_range,
                "failure_range": node.failure_range,
                "successor_tv": node.max_pair_successor_tv,
                "witness_ids": tuple(witness.witness_id for witness in node.witnesses),
            }
            for node in nodes
        ),
        "edge_ids": tuple(edge.edge_id for edge in edges),
        "audit_certified": audit.certified,
    }
    return FailedProofGraph(
        nodes=nodes,
        edges=edges,
        root_node_ids=roots,
        audit_certified=audit.certified,
        graph_id=object_id(graph_payload, "failed-proof-graph"),
    )


class UnauthorizedLocalRecoveryAccess(PermissionError):
    """Raised before any kernel call outside the recovery allowlist."""


@dataclass(frozen=True, slots=True)
class LocalRecoveryAuthorization:
    """Content-addressed state/action allowlist for one recovery transaction."""

    frontier_id: str
    frontier_state_actions: tuple[tuple[Hashable, Hashable], ...]
    reverse_dependency_state_actions: tuple[tuple[Hashable, Hashable], ...] = ()
    authorization_id: str = field(init=False)

    def __post_init__(self) -> None:
        frontier_unique = set(self.frontier_state_actions)
        if len(frontier_unique) != len(self.frontier_state_actions):
            raise ValueError("frontier authorization contains duplicate pairs")
        reverse_unique = set(self.reverse_dependency_state_actions)
        if len(reverse_unique) != len(self.reverse_dependency_state_actions):
            raise ValueError("reverse-dependency authorization contains duplicate pairs")
        overlap = frontier_unique & reverse_unique
        if overlap:
            raise ValueError("frontier and reverse-dependency authorizations overlap")
        frontier_ordered = tuple(
            sorted(frontier_unique, key=lambda pair: (repr(pair[0]), repr(pair[1])))
        )
        reverse_ordered = tuple(
            sorted(reverse_unique, key=lambda pair: (repr(pair[0]), repr(pair[1])))
        )
        object.__setattr__(self, "frontier_state_actions", frontier_ordered)
        object.__setattr__(self, "reverse_dependency_state_actions", reverse_ordered)
        payload = {
            "frontier_id": self.frontier_id,
            "frontier_pairs": tuple(
                (_state_id(state), _action_id(action))
                for state, action in frontier_ordered
            ),
            "reverse_dependency_pairs": tuple(
                (_state_id(state), _action_id(action))
                for state, action in reverse_ordered
            ),
        }
        object.__setattr__(
            self,
            "authorization_id",
            object_id(payload, "local-recovery-authorization"),
        )

    @classmethod
    def for_frontier(
        cls,
        kernel: Any,
        envelope: ExactRealizationEnvelope,
        frontier: FailedProofFrontier,
        graph: FailedProofGraph | None = None,
        *,
        include_strict_ancestors: bool = True,
    ) -> "LocalRecoveryAuthorization":
        frontier_pairs: list[tuple[Hashable, Hashable]] = []
        for node in frontier.nodes:
            for state in envelope.partition.members(node.cell):
                if not kernel.is_terminal(state):
                    frontier_pairs.extend(
                        (state, action) for action in kernel.actions(state)
                    )
        reverse_pairs: list[tuple[Hashable, Hashable]] = []
        if include_strict_ancestors and graph is not None:
            if graph.graph_id != frontier.graph_id:
                raise ValueError("frontier and graph IDs disagree")
            reverse: dict[str, set[str]] = {}
            for edge in graph.edges:
                reverse.setdefault(edge.target_node_id, set()).add(edge.source_node_id)
            pending = [node.node_id for node in frontier.nodes]
            ancestor_ids: set[str] = set()
            while pending:
                current = pending.pop()
                for parent in reverse.get(current, set()):
                    if parent not in ancestor_ids:
                        ancestor_ids.add(parent)
                        pending.append(parent)
            for node_id in sorted(ancestor_ids):
                node = graph.node(node_id)
                if node.selected_action is None:
                    raise ValueError(
                        "a reverse dependency lacks its selected semantic action"
                    )
                for state in envelope.partition.members(node.cell):
                    if not kernel.is_terminal(state):
                        raw_support = tuple(
                            envelope.concretizer(state, node.selected_action)
                        )
                        if not raw_support:
                            raise ValueError(
                                "ancestor selected-action concretizer has empty support"
                            )
                        total = sum(
                            (as_fraction(probability) for probability, _ in raw_support),
                            Fraction(0),
                        )
                        if total != 1 or any(
                            as_fraction(probability) <= 0
                            for probability, _ in raw_support
                        ):
                            raise ValueError(
                                "ancestor selected-action concretizer is not normalized"
                            )
                        legal = set(kernel.actions(state))
                        support = {
                            action for _, action in raw_support if action in legal
                        }
                        if len(support) != len({action for _, action in raw_support}):
                            raise ValueError(
                                "ancestor concretizer contains an illegal ground action"
                            )
                        reverse_pairs.extend((state, action) for action in support)
        frontier_set = set(frontier_pairs)
        # A state/action can occur at more than one horizon.  The authorization
        # is intentionally an SA capability rather than a state-time
        # capability, so count it once and attribute it to the frontier first.
        reverse_pairs = [pair for pair in reverse_pairs if pair not in frontier_set]
        return cls(frontier.frontier_id, tuple(frontier_pairs), tuple(set(reverse_pairs)))

    @property
    def allowed_state_actions(self) -> tuple[tuple[Hashable, Hashable], ...]:
        return self.frontier_state_actions + self.reverse_dependency_state_actions

    @property
    def allowed_states(self) -> tuple[Hashable, ...]:
        return _ordered({state for state, _ in self.allowed_state_actions})

    def permits(self, state: Hashable, action: Hashable) -> bool:
        return (state, action) in set(self.allowed_state_actions)


@dataclass(frozen=True, slots=True)
class KernelAccessRecord:
    sequence: int
    operation: str
    state_id: str
    action_id: str | None


class AuthorizedKernelView:
    """Narrow kernel facade with a non-mutable, append-only public log."""

    def __init__(self, kernel: Any, authorization: LocalRecoveryAuthorization) -> None:
        self._kernel = kernel
        self.authorization = authorization
        self._allowed = frozenset(authorization.allowed_state_actions)
        self._by_state: dict[Hashable, tuple[Hashable, ...]] = {
            state: _ordered(action for candidate, action in self._allowed if candidate == state)
            for state in authorization.allowed_states
        }
        self._log: list[KernelAccessRecord] = []

    @property
    def horizon(self) -> int:
        return int(self._kernel.horizon)

    @property
    def access_log(self) -> tuple[KernelAccessRecord, ...]:
        return tuple(self._log)

    def _record(
        self, operation: str, state: Hashable, action: Hashable | None = None
    ) -> None:
        self._log.append(
            KernelAccessRecord(
                sequence=len(self._log),
                operation=operation,
                state_id=_state_id(state),
                action_id=_action_id(action) if action is not None else None,
            )
        )

    def actions(self, state: Hashable) -> tuple[Hashable, ...]:
        if state not in self._by_state:
            raise UnauthorizedLocalRecoveryAccess(
                f"actions requested outside authorized state {_state_id(state)}"
            )
        self._record("actions", state)
        return self._by_state[state]

    def step(self, state: Hashable, action: Hashable) -> tuple[Any, ...]:
        if (state, action) not in self._allowed:
            raise UnauthorizedLocalRecoveryAccess(
                "step requested outside authorized state/action pair "
                f"{_state_id(state)}/{_action_id(action)}"
            )
        self._record("step", state, action)
        return iter_outcomes(self._kernel, state, action)

    def is_terminal(self, state: Hashable) -> bool:
        if state not in self._by_state:
            raise UnauthorizedLocalRecoveryAccess(
                f"terminal query requested outside authorized state {_state_id(state)}"
            )
        self._record("is_terminal", state)
        return bool(self._kernel.is_terminal(state))


def materialize_authorized_slice(
    kernel: Any,
    query: Any,
    envelope: ExactRealizationEnvelope,
    frontier: FailedProofFrontier,
    authorization: LocalRecoveryAuthorization | None = None,
    *,
    graph: FailedProofGraph | None = None,
    state_payload: Callable[[Hashable], Any] = repr,
    action_payload: Callable[[Hashable], Any] = repr,
) -> dict[str, Any]:
    """Materialize the exact finite worker input through an authorized view.

    The returned document contains opaque state/action payloads and stable IDs,
    never a kernel object or callable.  Successors are named only by abstract
    cell--horizon node IDs; certified boundary data must be supplied separately
    to the isolated solver.
    """

    validate_query(kernel, query)
    selected_authorization = authorization or LocalRecoveryAuthorization.for_frontier(
        kernel, envelope, frontier, graph
    )
    if selected_authorization.frontier_id != frontier.frontier_id:
        raise ValueError("authorization is bound to a different failed-proof frontier")
    view = AuthorizedKernelView(kernel, selected_authorization)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    partition = envelope.partition
    cells: list[dict[str, Any]] = []
    for node in frontier.nodes:
        members: list[dict[str, Any]] = []
        expected_active = tuple(
            state
            for state in partition.members(node.cell)
            if not kernel.is_terminal(state)
        )
        for state in sorted(expected_active, key=repr):
            actions: list[dict[str, Any]] = []
            for action in view.actions(state):
                immediate_reward = Fraction(0)
                immediate_failure = Fraction(0)
                termination = Fraction(0)
                successor_mass: dict[str, Fraction] = {}
                successor_cells: dict[str, str] = {}
                for outcome in view.step(state, action):
                    probability = as_fraction(outcome.probability)
                    immediate_reward += probability * outcome_reward(outcome, weights)
                    stopped = bool(
                        outcome.failure
                        or outcome.terminal
                        or is_stopped(kernel, outcome.next_state, goal)
                        or node.remaining <= 1
                    )
                    if outcome.failure:
                        immediate_failure += probability
                    if stopped:
                        termination += probability
                    else:
                        successor_cell = partition.cell_of(outcome.next_state)
                        successor_node = _node_id(successor_cell, node.remaining - 1)
                        successor_mass[successor_node] = (
                            successor_mass.get(successor_node, Fraction(0)) + probability
                        )
                        successor_cells[successor_node] = repr(successor_cell)
                actions.append(
                    {
                        "action_id": _action_id(action),
                        "action": action_payload(action),
                        "immediate_reward": _fraction_payload(immediate_reward),
                        "failure_probability": _fraction_payload(immediate_failure),
                        "termination_probability": _fraction_payload(termination),
                        "successors": [
                            {
                                "node_id": successor,
                                "cell": successor_cells[successor],
                                "probability": _fraction_payload(probability),
                            }
                            for successor, probability in sorted(successor_mass.items())
                        ],
                    }
                )
            members.append(
                {
                    "state_id": _state_id(state),
                    "state": state_payload(state),
                    "actions": sorted(actions, key=lambda item: item["action_id"]),
                }
            )
        cells.append(
            {
                "node_id": node.node_id,
                "cell": repr(node.cell),
                "remaining": node.remaining,
                "members": members,
            }
        )
    payload = {
        "schema": "acfqp.authorized_ground_slice.v1",
        "frontier_id": frontier.frontier_id,
        "authorization_id": selected_authorization.authorization_id,
        "authorization_counts": {
            "frontier_state_actions": len(
                selected_authorization.frontier_state_actions
            ),
            "reverse_dependency_state_actions": len(
                selected_authorization.reverse_dependency_state_actions
            ),
            "total_state_actions": len(
                selected_authorization.allowed_state_actions
            ),
        },
        "cells": sorted(cells, key=lambda item: (-item["remaining"], item["node_id"])),
        "access_log": [
            {
                "sequence": record.sequence,
                "operation": record.operation,
                "state_id": record.state_id,
                "action_id": record.action_id,
            }
            for record in view.access_log
        ],
    }
    payload["slice_id"] = object_id(payload, "authorized-ground-slice")
    return payload


def redact_authorized_slice_for_worker(document: Mapping[str, Any]) -> dict[str, Any]:
    """Strip trusted-side payload/accounting fields from a materialized slice.

    The isolated solver needs only opaque IDs and exact Bellman branch data.
    State/action payloads, access logs, and authorization counters remain on the
    trusted side and therefore cannot be used as covert extra worker authority.
    """

    cells = []
    for cell in document["cells"]:
        members = []
        for member in cell["members"]:
            actions = []
            for action in member["actions"]:
                actions.append(
                    {
                        "action_id": action["action_id"],
                        "immediate_reward": action["immediate_reward"],
                        "failure_probability": action["failure_probability"],
                        "termination_probability": action[
                            "termination_probability"
                        ],
                        "successors": [
                            {
                                "node_id": successor["node_id"],
                                "probability": successor["probability"],
                            }
                            for successor in action["successors"]
                        ],
                    }
                )
            members.append(
                {"state_id": member["state_id"], "actions": actions}
            )
        cells.append(
            {
                "node_id": cell["node_id"],
                "cell": cell["cell"],
                "remaining": cell["remaining"],
                "members": members,
            }
        )
    payload = {
        "schema": "acfqp.authorized_ground_slice.v1",
        "frontier_id": document["frontier_id"],
        "authorization_id": document["authorization_id"],
        "cells": cells,
    }
    payload["slice_id"] = object_id(payload, "authorized-ground-slice")
    return payload


def build_redacted_boundary_view(
    query: Any,
    envelope: ExactRealizationEnvelope,
    policy: FiniteHorizonPolicy[Any, Any],
    graph: FailedProofGraph,
    *,
    unrestricted_reward_upper: Fraction,
    regret_tolerance: Fraction,
) -> dict[str, Any]:
    """Serialize only abstract continuations and certificate scalars for the worker."""

    weights = reward_weights(query)
    unrestricted_upper = as_fraction(unrestricted_reward_upper)
    tolerance = as_fraction(regret_tolerance)
    if tolerance < 0:
        raise ValueError("regret tolerance must be nonnegative")
    partition = envelope.partition
    node_pairs = {(node.remaining, node.cell) for node in graph.nodes}
    # Alternate local actions may enter a cell not used by the original plan.
    # It is safe to expose a policy-defined abstract boundary node, but never a
    # ground realization identity.  Enumerating all policy-defined pairs keeps
    # this view query scoped while making the hand-off explicit.
    for decision in policy.decisions:
        if decision.remaining <= query.horizon:
            node_pairs.add((decision.remaining, decision.state))
    nodes: list[dict[str, Any]] = []
    for remaining, cell in sorted(node_pairs, key=lambda item: (-item[0], repr(item[1]))):
        try:
            action = policy.action(cell, remaining)
            realizations = envelope.realizations(cell, action)
        except KeyError:
            continue
        realization_rows: list[dict[str, Any]] = []
        for index, realization in enumerate(
            sorted(realizations, key=lambda value: repr(value.state))
        ):
            realization_rows.append(
                {
                    # The ID is node-local and intentionally does not reveal a
                    # ground state identifier.
                    "realization_id": object_id(
                        {"node": _node_id(cell, remaining), "ordinal": index},
                        "redacted-realization",
                    ),
                    "immediate_reward": _fraction_payload(realization.reward(weights)),
                    "failure_probability": _fraction_payload(
                        realization.failure_probability
                    ),
                    "successors": [
                        {
                            "node_id": _node_id(successor, remaining - 1),
                            "probability": _fraction_payload(probability),
                        }
                        for successor, probability in realization.successor_probabilities
                        if remaining > 1 and probability > 0
                    ],
                }
            )
        nodes.append(
            {
                "node_id": _node_id(cell, remaining),
                "cell": repr(cell),
                "remaining": remaining,
                "selected_action": repr(action),
                "abstract_realizations": realization_rows,
            }
        )
    root_mass: dict[str, Fraction] = {}
    for probability, state in query.initial_distribution:
        node_id = _node_id(partition.cell_of(state), query.horizon)
        root_mass[node_id] = root_mass.get(node_id, Fraction(0)) + probability
    payload = {
        "schema": "acfqp.redacted_boundary_view.v1",
        "graph_id": graph.graph_id,
        "frontier_id": graph.frontier().frontier_id,
        "delta": _fraction_payload(as_fraction(query.delta)),
        "unrestricted_reward_upper": _fraction_payload(unrestricted_upper),
        "regret_tolerance": _fraction_payload(tolerance),
        "roots": [
            {"node_id": node_id, "probability": _fraction_payload(probability)}
            for node_id, probability in sorted(root_mass.items())
        ],
        "nodes": sorted(nodes, key=lambda item: (-item["remaining"], item["node_id"])),
    }
    payload["boundary_view_id"] = object_id(payload, "redacted-boundary-view")
    return payload


@dataclass(frozen=True, slots=True)
class GroundPatchDecision:
    remaining: int
    cell: Hashable
    state: Hashable
    action: Hashable

    def __post_init__(self) -> None:
        if self.remaining <= 0:
            raise ValueError("ground patch decisions require positive remaining horizon")


@dataclass(frozen=True, slots=True)
class HybridPolicyOverlay:
    """Immutable direct-ground exceptions over a frozen abstract policy."""

    base_policy: FiniteHorizonPolicy[Any, Any] = field(compare=False, repr=False)
    decisions: tuple[GroundPatchDecision, ...]
    query_id: str = "unspecified-query"
    frontier_id: str = "unspecified-frontier"
    overlay_id: str = field(init=False)

    def __post_init__(self) -> None:
        seen: set[tuple[int, Hashable, Hashable]] = set()
        state_time_seen: dict[tuple[int, Hashable], Hashable] = {}
        ordered = tuple(
            sorted(
                self.decisions,
                key=lambda item: (
                    -item.remaining,
                    repr(item.cell),
                    repr(item.state),
                    repr(item.action),
                ),
            )
        )
        for decision in ordered:
            key = (decision.remaining, decision.cell, decision.state)
            if key in seen:
                raise ValueError(f"duplicate hybrid patch decision for {key!r}")
            seen.add(key)
            state_time = (decision.remaining, decision.state)
            incumbent_cell = state_time_seen.get(state_time)
            if incumbent_cell is not None and incumbent_cell != decision.cell:
                raise ValueError(
                    "one ground state-time pair cannot be patched through two cells"
                )
            state_time_seen[state_time] = decision.cell
        object.__setattr__(self, "decisions", ordered)
        payload = {
            "query_id": self.query_id,
            "frontier_id": self.frontier_id,
            "base_policy_signature": self.base_policy.signature(),
            "decisions": tuple(
                {
                    "remaining": decision.remaining,
                    "cell": repr(decision.cell),
                    "state_id": _state_id(decision.state),
                    "action_id": _action_id(decision.action),
                }
                for decision in ordered
            ),
        }
        object.__setattr__(self, "overlay_id", object_id(payload, "hybrid-policy-overlay"))

    @property
    def localized_cell_horizon_pairs(self) -> tuple[tuple[int, Hashable], ...]:
        return tuple(
            sorted(
                {(decision.remaining, decision.cell) for decision in self.decisions},
                key=lambda item: (-item[0], repr(item[1])),
            )
        )

    def patched_actions(
        self, cell: Hashable, remaining: int
    ) -> tuple[tuple[Hashable, Hashable], ...]:
        return tuple(
            (decision.state, decision.action)
            for decision in self.decisions
            if decision.cell == cell and decision.remaining == remaining
        )

    def is_localized(self, cell: Hashable, remaining: int) -> bool:
        return bool(self.patched_actions(cell, remaining))

    def ground_action(
        self, cell: Hashable, state: Hashable, remaining: int
    ) -> Hashable:
        for decision in self.decisions:
            if (
                decision.cell == cell
                and decision.state == state
                and decision.remaining == remaining
            ):
                return decision.action
        raise KeyError(
            f"overlay has no ground action for cell={cell!r}, state={state!r}, "
            f"remaining={remaining}"
        )


def audit_hybrid_policy(
    kernel: Any,
    query: Any,
    envelope: ExactRealizationEnvelope,
    overlay: HybridPolicyOverlay,
    *,
    regret_tolerance: Fraction = Fraction(1, 20),
    goal_cells: Iterable[Hashable] = (),
) -> AbstractPolicyAudit:
    """Full-authority sound audit of a query-scoped hybrid overlay.

    A localized cell must contain exactly one legal primitive action for every
    active member.  Its proof takes the minimum reward and maximum failure over
    those exact state-specific decisions.  Every other node continues to use
    the frozen realization envelope and abstract selector.
    """

    validate_query(kernel, query)
    if envelope.horizon != int(kernel.horizon):
        raise ValueError("envelope and kernel horizons disagree")
    partition = envelope.partition
    horizon = query_horizon(kernel, query)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    goals = set(goal_cells)
    issues: list[AuditIssue] = []
    issue_keys: set[tuple[str, Hashable, int]] = set()
    memo: dict[tuple[int, Hashable], tuple[Fraction, Fraction] | None] = {}

    def record(code: str, cell: Hashable, remaining: int, detail: str) -> None:
        marker = (code, cell, remaining)
        if marker not in issue_keys:
            issue_keys.add(marker)
            issues.append(AuditIssue(code, cell, remaining, detail))

    overlay_valid = True
    for decision in overlay.decisions:
        try:
            expected_cell = partition.cell_of(decision.state)
        except KeyError:
            record(
                "PATCH_STATE_UNREGISTERED",
                decision.cell,
                decision.remaining,
                f"state {decision.state!r} is outside the RAPM partition",
            )
            overlay_valid = False
            continue
        if expected_cell != decision.cell:
            record(
                "PATCH_CELL_MISMATCH",
                decision.cell,
                decision.remaining,
                f"state belongs to {expected_cell!r}",
            )
            overlay_valid = False
        if decision.remaining > horizon:
            record(
                "PATCH_HORIZON_OUTSIDE_QUERY",
                decision.cell,
                decision.remaining,
                f"query horizon is {horizon}",
            )
            overlay_valid = False
        if (
            not kernel.is_terminal(decision.state)
            and decision.action not in set(kernel.actions(decision.state))
        ):
            record(
                "PATCH_ACTION_UNAVAILABLE",
                decision.cell,
                decision.remaining,
                f"illegal primitive action {decision.action!r}",
            )
            overlay_valid = False

    def continuation(
        outcome: Any, remaining: int
    ) -> tuple[Fraction, Fraction] | None:
        if (
            remaining <= 1
            or outcome.failure
            or outcome.terminal
            or is_stopped(kernel, outcome.next_state, goal)
        ):
            return Fraction(0), Fraction(0)
        successor = partition.cell_of(outcome.next_state)
        return bounds(successor, remaining - 1)

    def bounds(cell: Hashable, remaining: int) -> tuple[Fraction, Fraction] | None:
        key = (remaining, cell)
        if key in memo:
            return memo[key]
        members = partition.members(cell)
        if remaining <= 0 or cell in goals or all(kernel.is_terminal(state) for state in members):
            memo[key] = (Fraction(0), Fraction(0))
            return memo[key]

        reward_values: list[Fraction] = []
        failure_values: list[Fraction] = []
        patch = dict(overlay.patched_actions(cell, remaining))
        if patch:
            active_members = tuple(
                state for state in members if not kernel.is_terminal(state)
            )
            missing = set(active_members) - set(patch)
            extra = set(patch) - set(active_members)
            if missing or extra:
                record(
                    "PATCH_MEMBER_COVERAGE",
                    cell,
                    remaining,
                    f"missing={tuple(sorted(map(repr, missing)))!r}, "
                    f"extra={tuple(sorted(map(repr, extra)))!r}",
                )
                memo[key] = None
                return None
            for state in members:
                if kernel.is_terminal(state):
                    reward_values.append(Fraction(0))
                    failure_values.append(Fraction(0))
                    continue
                action = patch[state]
                if action not in set(kernel.actions(state)):
                    record(
                        "PATCH_ACTION_UNAVAILABLE",
                        cell,
                        remaining,
                        f"illegal primitive action {action!r} at state {state!r}",
                    )
                    memo[key] = None
                    return None
                reward = Fraction(0)
                failure = Fraction(0)
                for outcome in iter_outcomes(kernel, state, action):
                    probability = as_fraction(outcome.probability)
                    branch_reward = outcome_reward(outcome, weights)
                    branch_failure = Fraction(1) if outcome.failure else Fraction(0)
                    downstream = continuation(outcome, remaining)
                    if downstream is None:
                        memo[key] = None
                        return None
                    branch_reward += downstream[0]
                    branch_failure += downstream[1]
                    reward += probability * branch_reward
                    failure += probability * branch_failure
                reward_values.append(reward)
                failure_values.append(failure)
        else:
            try:
                action = overlay.base_policy.action(cell, remaining)
            except KeyError:
                record("POLICY_UNDEFINED", cell, remaining, "no abstract boundary action")
                memo[key] = None
                return None
            try:
                realizations = envelope.realizations(cell, action)
            except KeyError:
                record(
                    "ACTION_UNAVAILABLE",
                    cell,
                    remaining,
                    f"semantic action {action!r} lacks a common exact realization",
                )
                memo[key] = None
                return None
            active_states = {realization.state for realization in realizations}
            for state in members:
                if kernel.is_terminal(state):
                    reward_values.append(Fraction(0))
                    failure_values.append(Fraction(0))
                elif state not in active_states:
                    record(
                        "REALIZATION_MISSING",
                        cell,
                        remaining,
                        f"no exact realization for nonterminal state {state!r}",
                    )
                    memo[key] = None
                    return None
            for realization in realizations:
                reward = realization.reward(weights)
                failure = realization.failure_probability
                for successor, probability in realization.successor_probabilities:
                    downstream = bounds(successor, remaining - 1)
                    if downstream is None:
                        memo[key] = None
                        return None
                    reward += probability * downstream[0]
                    failure += probability * downstream[1]
                reward_values.append(reward)
                failure_values.append(failure)
        if not reward_values:
            record("REALIZATION_MISSING", cell, remaining, "cell has no auditable behavior")
            memo[key] = None
            return None
        memo[key] = min(reward_values), max(failure_values)
        return memo[key]

    upper = unrestricted_upper_envelope(kernel, query, partition)
    root_upper = Fraction(0)
    root_lower = Fraction(0)
    root_failure = Fraction(0)
    complete = overlay_valid
    for probability, state in query_initial_distribution(kernel, query):
        cell = partition.cell_of(state)
        root_upper += probability * upper[(horizon, cell)]
        result = bounds(cell, horizon)
        if result is None:
            complete = False
        else:
            root_lower += probability * result[0]
            root_failure += probability * result[1]
    tolerance = as_fraction(regret_tolerance)
    risk_tolerance = as_fraction(query.delta)
    regret = root_upper - root_lower if complete else None
    certified = bool(
        complete
        and regret is not None
        and regret <= tolerance
        and root_failure <= risk_tolerance
    )
    reachable = tuple(
        CellPolicyBound(cell, remaining, result[0], result[1])
        for (remaining, cell), result in sorted(
            memo.items(), key=lambda item: (-item[0][0], repr(item[0][1]))
        )
        if result is not None
    )
    issues.sort(key=lambda issue: (-issue.remaining, repr(issue.cell), issue.code))
    return AbstractPolicyAudit(
        unrestricted_reward_upper=root_upper,
        lifted_reward_lower=root_lower if complete else None,
        lifted_failure_upper=root_failure if complete else None,
        regret_upper=regret,
        regret_tolerance=tolerance,
        risk_tolerance=risk_tolerance,
        certified=certified,
        issues=tuple(issues),
        reachable_bounds=reachable,
    )


@dataclass(frozen=True, slots=True)
class HybridAction:
    kind: str
    action: Hashable

    def __post_init__(self) -> None:
        if self.kind not in {"ground", "abstract"}:
            raise ValueError("hybrid action kind must be 'ground' or 'abstract'")


class _HybridKernelView:
    """Evaluation-only exact kernel integrating unpatched concretizers."""

    def __init__(self, kernel: Any, envelope: ExactRealizationEnvelope) -> None:
        self.ground_kernel = kernel
        self.envelope = envelope

    def __getattr__(self, name: str) -> Any:
        return getattr(self.ground_kernel, name)

    @property
    def horizon(self) -> int:
        return int(self.ground_kernel.horizon)

    def initial_distribution(self) -> tuple[tuple[Fraction, Hashable], ...]:
        return tuple(self.ground_kernel.initial_distribution())

    def is_terminal(self, state: Hashable) -> bool:
        return bool(self.ground_kernel.is_terminal(state))

    def actions(self, state: Hashable) -> tuple[HybridAction, ...]:
        ground = tuple(HybridAction("ground", action) for action in self.ground_kernel.actions(state))
        abstract = tuple(
            HybridAction("abstract", action)
            for action in self.envelope.semantic_action_provider(state)
        )
        return ground + abstract

    def step(self, state: Hashable, hybrid_action: HybridAction) -> tuple[Any, ...]:
        if hybrid_action.kind == "ground":
            return iter_outcomes(self.ground_kernel, state, hybrid_action.action)
        raw = tuple(self.envelope.concretizer(state, hybrid_action.action))
        if not raw:
            raise ValueError("abstract concretizer has empty support")
        masses: dict[tuple[Any, tuple[Any, ...], bool, bool], Fraction] = {}
        total_action_mass = Fraction(0)
        for raw_probability, action in raw:
            action_probability = as_fraction(raw_probability)
            if action_probability <= 0:
                raise ValueError("concretizer probabilities must be positive")
            total_action_mass += action_probability
            for outcome in iter_outcomes(self.ground_kernel, state, action):
                features = tuple(getattr(outcome, "reward_features", ()))
                atom = (
                    outcome.next_state,
                    features,
                    bool(outcome.failure),
                    bool(outcome.terminal),
                )
                masses[atom] = masses.get(atom, Fraction(0)) + (
                    action_probability * as_fraction(outcome.probability)
                )
        if total_action_mass != 1:
            raise ValueError("concretizer probabilities must sum to one")
        from acfqp.core import Outcome

        return tuple(
            Outcome(
                probability=probability,
                next_state=atom[0],
                reward_features=atom[1],
                failure=atom[2],
                terminal=atom[3],
            )
            for atom, probability in sorted(masses.items(), key=lambda item: repr(item[0]))
        )


@dataclass(frozen=True, slots=True)
class HybridPolicyLift:
    overlay: HybridPolicyOverlay
    lifted_policy: FiniteHorizonPolicy[Any, HybridAction]
    evaluation: PolicyEvaluation
    patched_decision_count: int
    abstract_decision_count: int


def lift_hybrid_policy(
    kernel: Any,
    query: Any,
    envelope: ExactRealizationEnvelope,
    overlay: HybridPolicyOverlay,
) -> HybridPolicyLift:
    """Lift a hybrid selector to its exact reachable ground state-time graph."""

    view = _HybridKernelView(kernel, envelope)
    validate_query(view, query)
    partition = envelope.partition
    horizon = query_horizon(view, query)
    goal = getattr(query, "goal", None)
    pending = [
        (horizon, state)
        for probability, state in query_initial_distribution(view, query)
        if probability > 0
    ]
    visited: set[tuple[int, Hashable]] = set()
    decisions: dict[tuple[int, Hashable], HybridAction] = {}
    patched_count = 0
    abstract_count = 0
    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or is_stopped(view, state, goal):
            continue
        cell = partition.cell_of(state)
        if overlay.is_localized(cell, remaining):
            action = HybridAction(
                "ground", overlay.ground_action(cell, state, remaining)
            )
            if action.action not in set(kernel.actions(state)):
                raise ValueError(f"hybrid overlay selected illegal action {action.action!r}")
            patched_count += 1
        else:
            action = HybridAction(
                "abstract", overlay.base_policy.action(cell, remaining)
            )
            # Normalize now, even at the last stage, so malformed concretizers
            # cannot hide behind horizon truncation.
            tuple(envelope.concretizer(state, action.action))
            abstract_count += 1
        decisions[marker] = action
        if remaining <= 1:
            continue
        for outcome in view.step(state, action):
            if outcome.failure or outcome.terminal or is_stopped(view, outcome.next_state, goal):
                continue
            pending.append((remaining - 1, outcome.next_state))
    lifted = FiniteHorizonPolicy.from_mapping(decisions)
    evaluation = evaluate_ground_policy(view, query, lifted)
    return HybridPolicyLift(
        overlay=overlay,
        lifted_policy=lifted,
        evaluation=evaluation,
        patched_decision_count=patched_count,
        abstract_decision_count=abstract_count,
    )


__all__ = [
    "AuthorizedKernelView",
    "FailedProofFrontier",
    "FailedProofGraph",
    "GroundPatchDecision",
    "HybridAction",
    "HybridPolicyLift",
    "HybridPolicyOverlay",
    "KernelAccessRecord",
    "LocalRecoveryAuthorization",
    "ProofEdge",
    "ProofNode",
    "ProofWitness",
    "UnauthorizedLocalRecoveryAccess",
    "audit_hybrid_policy",
    "build_failed_proof_graph",
    "build_redacted_boundary_view",
    "lift_hybrid_policy",
    "materialize_authorized_slice",
    "redact_authorized_slice_for_worker",
]
