"""Exact slack-aware causal localization for failed plan certificates.

This module is additive to :mod:`acfqp.local_recovery`.  The Phase 3C v1
``DirectBad`` fixture is intentionally left unchanged; this module supplies
the stronger, general proof-circuit semantics needed before a local-ground
authorization is issued.

The important distinction is between a residual that merely exists somewhere
in a reachable proof DAG and one that can affect the failed root certificate.
For a finite Bellman circuit we repeatedly evaluate the exact pessimistic
proof, retain *all* tied extremizers, and allow a residual to be discharged
only while it lies on a currently active root derivation.  Discharging a risk
gate changes ``max`` to ``min``; discharging a reward-lower gate changes
``min`` to ``max``.  This is an optimistic ambiguity-erasure relaxation, not a
post-recovery certificate.  It is used to minimize the capability exposed to
the local solver; the resulting ground policy must still pass the independent
full audit.

Search is exhaustive up to an explicit evaluation cap.  A cap hit is a
first-class result and never silently falls back to the whole DirectBad set.
All arithmetic is exact ``Fraction`` arithmetic.

One invocation models one sparse local-recovery transaction.  When projected
from a Phase 3C failed-proof graph, only the earliest DirectBad antichain is
recoverable.  DirectBad descendants remain in the exact circuit as Bellman
dependencies but cannot be opened by the same transaction.  If they become
causal after the first overlay, the authority must run the complete audit
again and create a separately bounded transaction.  This module therefore
does not claim one-shot multi-layer repair completeness.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import heapq
from typing import Any, Callable, Iterable


FAILURE_UPPER = "failure_upper"
REWARD_LOWER = "reward_lower"
_CHANNELS = (FAILURE_UPPER, REWARD_LOWER)


def _fraction(value: Fraction | int) -> Fraction:
    """Accept only exact symbolic inputs.

    ``Fraction(float)`` is exact for the binary floating-point value, but that
    is precisely the wrong contract here: a float has already lost the
    caller's intended rational representation.  Causal proof circuits are
    audit objects, so accepting floats, decimal strings, or booleans would
    silently weaken their exactness claim.
    """

    if isinstance(value, bool) or not isinstance(value, (Fraction, int)):
        raise ValueError("causal proof numbers must be exact integers or Fractions")
    return value if isinstance(value, Fraction) else Fraction(value)


@dataclass(frozen=True, slots=True)
class CausalSuccessor:
    """One positive-probability Bellman dependency."""

    node_id: str
    probability: Fraction

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("causal successor node ID must be non-empty")
        probability = _fraction(self.probability)
        if probability <= 0:
            raise ValueError("causal successor probability must be positive")
        object.__setattr__(self, "probability", probability)


@dataclass(frozen=True, slots=True)
class CausalRealization:
    """One exact selected-action realization in a Bellman proof node."""

    realization_id: str
    immediate_reward: Fraction = Fraction(0)
    immediate_failure: Fraction = Fraction(0)
    successors: tuple[CausalSuccessor, ...] = ()

    def __post_init__(self) -> None:
        if not self.realization_id:
            raise ValueError("causal realization ID must be non-empty")
        reward = _fraction(self.immediate_reward)
        failure = _fraction(self.immediate_failure)
        if failure < 0 or failure > 1:
            raise ValueError("immediate failure must lie in [0,1]")
        successors = tuple(self.successors)
        if len({successor.node_id for successor in successors}) != len(successors):
            raise ValueError("a realization contains duplicate successor nodes")
        successor_mass = sum(
            (item.probability for item in successors), Fraction(0)
        )
        if successor_mass > 1:
            raise ValueError("successor probability mass exceeds one")
        if failure + successor_mass > 1:
            raise ValueError(
                "immediate failure plus successor probability mass exceeds one"
            )
        object.__setattr__(self, "immediate_reward", reward)
        object.__setattr__(self, "immediate_failure", failure)
        object.__setattr__(
            self,
            "successors",
            tuple(sorted(successors, key=lambda item: item.node_id)),
        )


@dataclass(frozen=True, slots=True)
class CausalProofNode:
    """A finite-horizon Bellman gate.

    ``recoverable=False`` is used for structural/root handoff nodes.  They are
    still traversed when constructing the active derivation but can never be
    opened as local ground capabilities.
    """

    node_id: str
    realizations: tuple[CausalRealization, ...]
    recoverable: bool = True
    capability_cost: int = 1

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("causal proof node ID must be non-empty")
        realizations = tuple(self.realizations)
        if not realizations:
            raise ValueError("causal proof node must have a realization")
        identifiers = tuple(item.realization_id for item in realizations)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("causal proof node contains duplicate realization IDs")
        if (
            isinstance(self.capability_cost, bool)
            or not isinstance(self.capability_cost, int)
            or self.capability_cost <= 0
        ):
            raise ValueError("capability cost must be a positive integer")
        object.__setattr__(
            self,
            "realizations",
            tuple(sorted(realizations, key=lambda item: item.realization_id)),
        )


@dataclass(frozen=True, slots=True)
class CausalRoot:
    """One exact initial-distribution contribution to the proof root."""

    node_id: str
    probability: Fraction

    def __post_init__(self) -> None:
        probability = _fraction(self.probability)
        if probability <= 0:
            raise ValueError("root probability must be positive")
        object.__setattr__(self, "probability", probability)


@dataclass(frozen=True, slots=True)
class CertificateObligation:
    """A monotone root certificate threshold."""

    channel: str
    threshold: Fraction

    def __post_init__(self) -> None:
        if self.channel not in _CHANNELS:
            raise ValueError(f"unknown certificate channel {self.channel!r}")
        object.__setattr__(self, "threshold", _fraction(self.threshold))

    def passes(self, value: Fraction) -> bool:
        if self.channel == FAILURE_UPPER:
            return value <= self.threshold
        return value >= self.threshold

    def deficit(self, value: Fraction) -> Fraction:
        if self.channel == FAILURE_UPPER:
            return max(value - self.threshold, Fraction(0))
        return max(self.threshold - value, Fraction(0))


@dataclass(frozen=True, slots=True)
class NodeChannelValue:
    """Exact value and extremizers for one Bellman gate/channel."""

    node_id: str
    channel: str
    pessimistic_value: Fraction
    optimistic_value: Fraction
    selected_value: Fraction
    residual_width: Fraction
    active_realization_ids: tuple[str, ...]
    discharged: bool


@dataclass(frozen=True, slots=True)
class CounterfactualCertificate:
    """One exact evaluation of an ambiguity-discharge set."""

    discharged_node_ids: tuple[str, ...]
    root_values: tuple[tuple[str, Fraction], ...]
    deficits: tuple[tuple[str, Fraction], ...]
    failed_channels: tuple[str, ...]
    active_node_ids: tuple[tuple[str, tuple[str, ...]], ...]
    eligible_node_ids: tuple[str, ...]
    node_values: tuple[NodeChannelValue, ...]

    @property
    def certified(self) -> bool:
        return not self.failed_channels

    def root_value(self, channel: str) -> Fraction:
        return dict(self.root_values)[channel]

    def deficit(self, channel: str) -> Fraction:
        return dict(self.deficits)[channel]

    def active_nodes(self, channel: str) -> tuple[str, ...]:
        return dict(self.active_node_ids).get(channel, ())

    def node_value(self, node_id: str, channel: str) -> NodeChannelValue:
        for value in self.node_values:
            if value.node_id == node_id and value.channel == channel:
                return value
        raise KeyError((node_id, channel))


class CausalSearchStatus(str, Enum):
    CERTIFICATE_ALREADY_PASSES = "CERTIFICATE_ALREADY_PASSES"
    CAUSAL_FAMILY_FOUND = "CAUSAL_FAMILY_FOUND"
    NO_CAUSAL_COVER = "NO_CAUSAL_COVER"
    SEARCH_CAP_REACHED = "SEARCH_CAP_REACHED"


@dataclass(frozen=True, slots=True)
class CausalSearchRecord:
    discharged_node_ids: tuple[str, ...]
    activation_trace: tuple[str, ...]
    capability_cost: int
    certificate: CounterfactualCertificate


@dataclass(frozen=True, slots=True)
class SlackAwareCausalFamily:
    """Complete capped search result and its inclusion-minimal terminal family."""

    status: CausalSearchStatus
    evaluation_cap: int
    evaluation_count: int
    search_complete: bool
    baseline: CounterfactualCertificate
    evaluations: tuple[CausalSearchRecord, ...]
    minimal_cover_node_ids: tuple[tuple[str, ...], ...]
    selected_node_ids: tuple[str, ...] | None
    selected_activation_trace: tuple[str, ...] | None
    candidate_node_ids: tuple[str, ...]
    excluded_candidate_node_ids: tuple[str, ...]

    @property
    def found(self) -> bool:
        return self.status == CausalSearchStatus.CAUSAL_FAMILY_FOUND


class CausalProofCircuit:
    """Validated finite acyclic Bellman circuit."""

    def __init__(
        self,
        nodes: Iterable[CausalProofNode],
        roots: Iterable[CausalRoot],
    ) -> None:
        ordered_nodes = tuple(sorted(tuple(nodes), key=lambda item: item.node_id))
        if not ordered_nodes:
            raise ValueError("causal proof circuit must contain nodes")
        if len({node.node_id for node in ordered_nodes}) != len(ordered_nodes):
            raise ValueError("causal proof circuit contains duplicate node IDs")
        self.nodes = ordered_nodes
        self._by_id = {node.node_id: node for node in ordered_nodes}
        ordered_roots = tuple(sorted(tuple(roots), key=lambda item: item.node_id))
        if not ordered_roots:
            raise ValueError("causal proof circuit must contain roots")
        if len({root.node_id for root in ordered_roots}) != len(ordered_roots):
            raise ValueError("causal proof circuit contains duplicate root nodes")
        if any(root.node_id not in self._by_id for root in ordered_roots):
            raise ValueError("causal root names an unknown node")
        if sum((root.probability for root in ordered_roots), Fraction(0)) > 1:
            raise ValueError("root probability mass exceeds one")
        self.roots = ordered_roots
        for node in ordered_nodes:
            for realization in node.realizations:
                for successor in realization.successors:
                    if successor.node_id not in self._by_id:
                        raise ValueError(
                            f"realization names unknown successor {successor.node_id!r}"
                        )
        self._validate_acyclic()

    def node(self, node_id: str) -> CausalProofNode:
        return self._by_id[node_id]

    def _validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("causal proof circuit contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for realization in self.node(node_id).realizations:
                for successor in realization.successors:
                    visit(successor.node_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node in self.nodes:
            visit(node.node_id)


def evaluate_counterfactual_certificate(
    circuit: CausalProofCircuit,
    obligations: Iterable[CertificateObligation],
    discharged_node_ids: Iterable[str] = (),
) -> CounterfactualCertificate:
    """Evaluate one exact ambiguity-erasure counterfactual.

    The active derivation contains every tied extremizer.  Eligibility is
    limited to recoverable, undisclosed nodes with a positive residual in a
    channel that still fails at the root.
    """

    ordered_obligations = tuple(sorted(tuple(obligations), key=lambda item: item.channel))
    if not ordered_obligations:
        raise ValueError("at least one certificate obligation is required")
    if len({item.channel for item in ordered_obligations}) != len(ordered_obligations):
        raise ValueError("certificate obligations contain duplicate channels")
    discharged = frozenset(discharged_node_ids)
    unknown = discharged - set(circuit._by_id)
    if unknown:
        raise ValueError(f"discharge set contains unknown nodes: {sorted(unknown)!r}")
    memo: dict[tuple[str, str], NodeChannelValue] = {}

    def value(node_id: str, channel: str) -> NodeChannelValue:
        key = (node_id, channel)
        if key in memo:
            return memo[key]
        node = circuit.node(node_id)
        branch_values: list[tuple[str, Fraction]] = []
        for realization in node.realizations:
            branch = (
                realization.immediate_failure
                if channel == FAILURE_UPPER
                else realization.immediate_reward
            )
            for successor in realization.successors:
                branch += successor.probability * value(
                    successor.node_id, channel
                ).selected_value
            branch_values.append((realization.realization_id, branch))
        raw_values = tuple(item[1] for item in branch_values)
        if channel == FAILURE_UPPER:
            pessimistic = max(raw_values)
            optimistic = min(raw_values)
        else:
            pessimistic = min(raw_values)
            optimistic = max(raw_values)
        is_discharged = node_id in discharged
        selected = optimistic if is_discharged else pessimistic
        active_ids = tuple(
            realization_id
            for realization_id, branch in branch_values
            if branch == selected
        )
        result = NodeChannelValue(
            node_id=node_id,
            channel=channel,
            pessimistic_value=pessimistic,
            optimistic_value=optimistic,
            selected_value=selected,
            residual_width=abs(pessimistic - optimistic),
            active_realization_ids=active_ids,
            discharged=is_discharged,
        )
        memo[key] = result
        return result

    root_values: dict[str, Fraction] = {}
    deficits: dict[str, Fraction] = {}
    failed: list[str] = []
    obligation_by_channel = {item.channel: item for item in ordered_obligations}
    for obligation in ordered_obligations:
        root = sum(
            (
                item.probability
                * value(item.node_id, obligation.channel).selected_value
                for item in circuit.roots
            ),
            Fraction(0),
        )
        root_values[obligation.channel] = root
        deficits[obligation.channel] = obligation.deficit(root)
        if not obligation.passes(root):
            failed.append(obligation.channel)

    active_by_channel: dict[str, set[str]] = {
        channel: set() for channel in failed
    }
    for channel in failed:
        pending = [root.node_id for root in circuit.roots]
        while pending:
            node_id = pending.pop()
            if node_id in active_by_channel[channel]:
                continue
            active_by_channel[channel].add(node_id)
            node = circuit.node(node_id)
            active_realizations = set(value(node_id, channel).active_realization_ids)
            for realization in node.realizations:
                if realization.realization_id not in active_realizations:
                    continue
                pending.extend(successor.node_id for successor in realization.successors)

    eligible: set[str] = set()
    for channel in failed:
        for node_id in active_by_channel[channel]:
            node = circuit.node(node_id)
            if (
                node.recoverable
                and node_id not in discharged
                and value(node_id, channel).residual_width > 0
            ):
                eligible.add(node_id)

    # Materialize both channels for every node.  This complete inventory makes
    # selective omission detectable by an independent artifact verifier.
    for node in circuit.nodes:
        for channel in _CHANNELS:
            value(node.node_id, channel)

    return CounterfactualCertificate(
        discharged_node_ids=tuple(sorted(discharged)),
        root_values=tuple(sorted(root_values.items())),
        deficits=tuple(sorted(deficits.items())),
        failed_channels=tuple(sorted(failed)),
        active_node_ids=tuple(
            (channel, tuple(sorted(node_ids)))
            for channel, node_ids in sorted(active_by_channel.items())
        ),
        eligible_node_ids=tuple(sorted(eligible)),
        node_values=tuple(
            memo[key] for key in sorted(memo, key=lambda item: (item[0], item[1]))
        ),
    )


def _set_cost(circuit: CausalProofCircuit, node_ids: frozenset[str]) -> tuple[object, ...]:
    return (
        sum(circuit.node(node_id).capability_cost for node_id in node_ids),
        len(node_ids),
        tuple(sorted(node_ids)),
    )


def find_slack_aware_causal_family(
    circuit: CausalProofCircuit,
    obligations: Iterable[CertificateObligation],
    *,
    max_evaluations: int,
) -> SlackAwareCausalFamily:
    """Enumerate the complete active/slack causal family under an exact cap.

    Only active residuals may be appended to a search trace.  This restriction
    is complete for the monotone ambiguity-erasure relaxation: changing an
    inactive gate cannot change the current root extremum, so it can always be
    delayed until it becomes active.  Tied extrema are all active.
    """

    if (
        isinstance(max_evaluations, bool)
        or not isinstance(max_evaluations, int)
        or max_evaluations <= 0
    ):
        raise ValueError("max_evaluations must be a positive integer")
    ordered_obligations = tuple(obligations)
    baseline = evaluate_counterfactual_certificate(circuit, ordered_obligations)
    baseline_record = CausalSearchRecord((), (), 0, baseline)
    if baseline.certified:
        return SlackAwareCausalFamily(
            status=CausalSearchStatus.CERTIFICATE_ALREADY_PASSES,
            evaluation_cap=max_evaluations,
            evaluation_count=1,
            search_complete=True,
            baseline=baseline,
            evaluations=(baseline_record,),
            minimal_cover_node_ids=(),
            selected_node_ids=(),
            selected_activation_trace=(),
            candidate_node_ids=(),
            excluded_candidate_node_ids=(),
        )

    heap: list[tuple[tuple[object, ...], tuple[str, ...], frozenset[str]]] = []
    heapq.heappush(heap, (_set_cost(circuit, frozenset()), (), frozenset()))
    traces: dict[frozenset[str], tuple[str, ...]] = {frozenset(): ()}
    queued: set[frozenset[str]] = {frozenset()}
    visited: set[frozenset[str]] = set()
    records: list[CausalSearchRecord] = []
    terminals: list[frozenset[str]] = []
    candidate_nodes: set[str] = set()

    while heap:
        if len(records) >= max_evaluations:
            return SlackAwareCausalFamily(
                status=CausalSearchStatus.SEARCH_CAP_REACHED,
                evaluation_cap=max_evaluations,
                evaluation_count=len(records),
                search_complete=False,
                baseline=baseline,
                evaluations=tuple(records),
                minimal_cover_node_ids=(),
                selected_node_ids=None,
                selected_activation_trace=None,
                candidate_node_ids=tuple(sorted(candidate_nodes)),
                excluded_candidate_node_ids=(),
            )
        _, _, discharged = heapq.heappop(heap)
        if discharged in visited:
            continue
        visited.add(discharged)
        certificate = (
            baseline
            if not discharged
            else evaluate_counterfactual_certificate(
                circuit, ordered_obligations, discharged
            )
        )
        trace = traces[discharged]
        records.append(
            CausalSearchRecord(
                discharged_node_ids=tuple(sorted(discharged)),
                activation_trace=trace,
                capability_cost=int(_set_cost(circuit, discharged)[0]),
                certificate=certificate,
            )
        )
        if certificate.certified:
            terminals.append(discharged)
            # Supersets cannot be inclusion-minimal terminal sets.
            continue
        candidate_nodes.update(certificate.eligible_node_ids)
        for node_id in certificate.eligible_node_ids:
            child = frozenset((*discharged, node_id))
            if child in queued:
                continue
            queued.add(child)
            child_trace = (*trace, node_id)
            traces[child] = child_trace
            heapq.heappush(
                heap,
                (_set_cost(circuit, child), child_trace, child),
            )

    if not terminals:
        return SlackAwareCausalFamily(
            status=CausalSearchStatus.NO_CAUSAL_COVER,
            evaluation_cap=max_evaluations,
            evaluation_count=len(records),
            search_complete=True,
            baseline=baseline,
            evaluations=tuple(records),
            minimal_cover_node_ids=(),
            selected_node_ids=None,
            selected_activation_trace=None,
            candidate_node_ids=tuple(sorted(candidate_nodes)),
            excluded_candidate_node_ids=tuple(sorted(candidate_nodes)),
        )

    minimal = tuple(
        terminal
        for terminal in terminals
        if not any(other < terminal for other in terminals)
    )
    minimal = tuple(sorted(minimal, key=lambda item: _set_cost(circuit, item)))
    selected = minimal[0]
    selected_record = next(
        record
        for record in records
        if record.discharged_node_ids == tuple(sorted(selected))
    )
    selected_family_nodes = set().union(*minimal) if minimal else set()
    return SlackAwareCausalFamily(
        status=CausalSearchStatus.CAUSAL_FAMILY_FOUND,
        evaluation_cap=max_evaluations,
        evaluation_count=len(records),
        search_complete=True,
        baseline=baseline,
        evaluations=tuple(records),
        minimal_cover_node_ids=tuple(tuple(sorted(item)) for item in minimal),
        selected_node_ids=tuple(sorted(selected)),
        selected_activation_trace=selected_record.activation_trace,
        candidate_node_ids=tuple(sorted(candidate_nodes)),
        excluded_candidate_node_ids=tuple(
            sorted(candidate_nodes - selected_family_nodes)
        ),
    )


def root_channel_gain(
    baseline: CounterfactualCertificate,
    counterfactual: CounterfactualCertificate,
    channel: str,
) -> Fraction:
    """Return the exact beneficial root movement for one channel."""

    if channel == FAILURE_UPPER:
        return baseline.root_value(channel) - counterfactual.root_value(channel)
    if channel == REWARD_LOWER:
        return counterfactual.root_value(channel) - baseline.root_value(channel)
    raise ValueError(f"unknown certificate channel {channel!r}")


def causal_circuit_from_failed_proof(
    kernel: Any,
    query: Any,
    envelope: Any,
    policy: Any,
    failed_proof_graph: Any,
    *,
    capability_cost_provider: Callable[[Any], int] | None = None,
) -> CausalProofCircuit:
    """Project an existing Phase 3C proof DAG into the stronger exact circuit.

    The v1 graph deliberately aggregated dependency-edge mass and therefore is
    not by itself sufficient to recover active extremizers.  This adapter reads
    the authoritative selected-action realizations again and emits one exact
    branch row per realization.  Only nodes in v1's *earliest* ``DirectBad``
    antichain are recoverable.  DirectBad ancestors/descendants outside that
    frontier and propagated-only nodes remain structural handoff gates.

    This is intentionally a one-transaction projection.  If a descendant
    residual remains after applying an overlay, a full post-audit must create
    a new proof graph/frontier and a new occurrence-bound authorization rather
    than letting the first worker traverse multiple local layers.

    This helper never evaluates J0 and never changes the v1 graph or frontier.
    """

    # Local imports keep the generic proof-circuit types usable by the isolated
    # stdlib-only synthetic tests and avoid a dependency cycle with v1.
    from acfqp.artifacts import object_id
    from acfqp.planning.common import (
        as_fraction,
        query_initial_distribution,
        reward_weights,
    )

    graph_nodes = tuple(failed_proof_graph.nodes)
    frontier_node_ids = frozenset(failed_proof_graph.frontier().node_ids)
    keys = {(node.remaining, node.cell): node.node_id for node in graph_nodes}
    if len(keys) != len(graph_nodes):
        raise ValueError("failed-proof graph repeats a cell/horizon node")
    weights = reward_weights(query)
    circuit_nodes: list[CausalProofNode] = []
    for node in graph_nodes:
        if node.selected_action is None:
            raise ValueError("causal circuit cannot project an undefined policy action")
        realizations = tuple(envelope.realizations(node.cell, node.selected_action))
        branches: list[CausalRealization] = []
        for realization in realizations:
            successors: list[CausalSuccessor] = []
            if node.remaining > 1:
                for successor_cell, probability in realization.successor_probabilities:
                    target = keys.get((node.remaining - 1, successor_cell))
                    if target is None:
                        raise ValueError(
                            "selected realization leaves the complete failed-proof graph"
                        )
                    if as_fraction(probability) > 0:
                        successors.append(
                            CausalSuccessor(target, as_fraction(probability))
                        )
            branches.append(
                CausalRealization(
                    realization_id=object_id(
                        {
                            "proof_node_id": node.node_id,
                            "state_id": object_id(realization.state, "state"),
                        },
                        "causal-realization",
                    ),
                    immediate_reward=realization.reward(weights),
                    immediate_failure=realization.failure_probability,
                    successors=tuple(successors),
                )
            )
        if capability_cost_provider is None:
            # Construction/evaluation callers may use the live kernel.  An
            # operational frozen-model consumer must provide its verified
            # binding-time catalogue explicitly and is regression-tested to
            # reject this branch.
            capability_cost = sum(
                len(tuple(kernel.actions(state)))
                for state in envelope.partition.members(node.cell)
                if not kernel.is_terminal(state)
            )
        else:
            capability_cost = capability_cost_provider(node)
        if (
            isinstance(capability_cost, bool)
            or not isinstance(capability_cost, int)
            or capability_cost <= 0
        ):
            raise ValueError("capability cost provider must return a positive integer")
        circuit_nodes.append(
            CausalProofNode(
                node_id=node.node_id,
                realizations=tuple(branches),
                recoverable=bool(
                    node.node_id in frontier_node_ids and not node.issue_codes
                ),
                capability_cost=capability_cost,
            )
        )

    root_mass: dict[str, Fraction] = {}
    horizon = max(node.remaining for node in graph_nodes)
    for probability, state in query_initial_distribution(kernel, query):
        if as_fraction(probability) <= 0:
            continue
        root_id = keys.get((horizon, envelope.partition.cell_of(state)))
        if root_id is None:
            raise ValueError("query root is absent from the failed-proof graph")
        root_mass[root_id] = root_mass.get(root_id, Fraction(0)) + as_fraction(
            probability
        )
    roots = tuple(
        CausalRoot(node_id, probability)
        for node_id, probability in sorted(root_mass.items())
    )
    return CausalProofCircuit(circuit_nodes, roots)
