"""Train-only exact-oracle signatures for approximate strategic quotients.

The behavioural minimizer in :mod:`acfqp.abstraction.behavioral` preserves the
entire one-step controlled model exactly.  This module supplies the complementary
Phase-3A upper bound: use exact unrestricted ground planning information from a
declared training profile to construct a smaller, query-independent state
partition, then accept it only through the ordinary exact realization audit.

No held-out query is accepted by the builder.  Held-out evaluation is a
separate caller responsibility, which makes leakage mechanically testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Any, Callable, Hashable, Iterable

from acfqp.core import QuerySpec
from acfqp.planning.audit import AbstractPolicyAudit, audit_abstract_policy
from acfqp.planning.ground import (
    solve_ground_action_frontier,
    solve_ground_pareto,
)
from acfqp.planning.lift import lift_semantic_policy_decisions
from acfqp.planning.nominal import solve_nominal_pareto
from acfqp.planning.policy import FiniteHorizonPolicy

from .partition import Partition
from .quotient import QuotientModels, build_quotient_models


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


@dataclass(frozen=True, slots=True)
class OracleFrontierPoint:
    expected_reward: Fraction
    failure_probability: Fraction


@dataclass(frozen=True, slots=True)
class ActionConditionedParetoFrontier:
    state: Hashable
    remaining: int
    ground_action: Hashable
    points: tuple[OracleFrontierPoint, ...]


@dataclass(frozen=True, slots=True)
class GroundOracleRecord:
    state: Hashable
    remaining: int
    frontier: tuple[OracleFrontierPoint, ...]
    feasible: bool
    selected_ground_action: Hashable | None
    selected_semantic_action: Hashable | None
    selected_reward: Fraction | None
    selected_failure: Fraction | None
    maximum_reward: Fraction
    minimum_failure: Fraction
    normalizer: Fraction


@dataclass(frozen=True, slots=True)
class GroundOracleTable:
    """Exact unrestricted J0 records used only by the training constructor."""

    states: tuple[Hashable, ...]
    max_horizon: int
    reward_weights: tuple[tuple[str, Fraction], ...]
    goal: str
    delta: Fraction
    records: tuple[GroundOracleRecord, ...]
    action_frontiers: tuple[ActionConditionedParetoFrontier, ...]
    action_basis: str = "unrestricted_ground_actions"

    def record(self, state: Hashable, remaining: int) -> GroundOracleRecord:
        for record in self.records:
            if record.state == state and record.remaining == remaining:
                return record
        raise KeyError(f"oracle record is unavailable for {(state, remaining)!r}")


@dataclass(frozen=True, order=True, slots=True)
class OracleSignatureAtom:
    atom_id: str
    remaining: int
    channel: str


@dataclass(frozen=True, slots=True)
class OracleCandidateEvaluation:
    atom_ids: tuple[str, ...]
    cell_count: int
    compression: Fraction
    built: bool
    all_training_queries_certified: bool
    maximum_regret_upper: Fraction | None
    maximum_failure_excess: Fraction | None
    reachable_mixed_cell_count: int
    partition_signature: tuple[tuple[str, ...], ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OracleTrainingEvaluation:
    query: QuerySpec[Any]
    abstract_policy: FiniteHorizonPolicy[Any, Any]
    audit: AbstractPolicyAudit


@dataclass(frozen=True, slots=True)
class OraclePartitionSelection:
    partition: Partition
    quotient_models: QuotientModels
    selected_atoms: tuple[OracleSignatureAtom, ...]
    candidate_trace: tuple[OracleCandidateEvaluation, ...]
    training_evaluations: tuple[OracleTrainingEvaluation, ...]
    reachable_mixed_cells: tuple[Hashable, ...]


def _frontier_values(result: Any) -> tuple[OracleFrontierPoint, ...]:
    return tuple(
        OracleFrontierPoint(point.expected_reward, point.failure_probability)
        for point in result.frontier
    )


def _semantic_label_for_ground_action(
    kernel: Any,
    adapter: Any,
    state: Hashable,
    ground_action: Hashable,
) -> Hashable:
    matching: list[Hashable] = []
    for label in adapter.labels(kernel, state):
        support = {
            action
            for probability, action in adapter.concretize(kernel, state, label)
            if Fraction(probability) > 0
        }
        if ground_action in support:
            matching.append(label)
    if len(matching) != 1:
        raise ValueError(
            "each ground action must belong to exactly one semantic-action support; "
            f"state={state!r}, action={ground_action!r}, labels={matching!r}"
        )
    return matching[0]


def build_ground_oracle_table(
    kernel: Any,
    states: Iterable[Hashable],
    semantic_adapter: Any,
    *,
    max_horizon: int,
    reward_weights: tuple[tuple[str, Fraction], ...],
    goal: str,
    delta: Fraction,
    normalizer_proof_id: str = "oracle_table.kernel_reward_upper_bound.v1",
) -> GroundOracleTable:
    """Compute complete state and first-action-conditioned exact J0 tables."""

    registered = _ordered(states)
    if not registered or len(set(registered)) != len(registered):
        raise ValueError("oracle table states must be nonempty and unique")
    if max_horizon <= 0 or max_horizon > int(kernel.horizon):
        raise ValueError("oracle-table horizon lies outside the kernel horizon")
    raw_weights = {name: Fraction(value) for name, value in reward_weights}
    records: list[GroundOracleRecord] = []
    action_records: list[ActionConditionedParetoFrontier] = []
    for state in registered:
        if kernel.is_terminal(state):
            continue
        for remaining in range(1, max_horizon + 1):
            normalizer = Fraction(
                kernel.reward_upper_bound(remaining, raw_weights, goal)
            )
            if normalizer <= 0:
                raise ValueError("oracle query requires a positive reward upper bound")
            query = QuerySpec.from_state(
                state,
                horizon=remaining,
                reward_weights=reward_weights,
                goal=goal,
                delta=delta,
                normalizer=normalizer,
                normalizer_proof_id=normalizer_proof_id,
            )
            result = solve_ground_pareto(kernel, query)
            if not result.frontier:
                raise RuntimeError("exact ground oracle produced an empty frontier")
            selected = result.selected
            selected_action = (
                selected.policy.action(state, remaining)
                if selected is not None
                else None
            )
            semantic_action = (
                _semantic_label_for_ground_action(
                    kernel,
                    semantic_adapter,
                    state,
                    selected_action,
                )
                if selected_action is not None
                else None
            )
            records.append(
                GroundOracleRecord(
                    state=state,
                    remaining=remaining,
                    frontier=_frontier_values(result),
                    feasible=selected is not None,
                    selected_ground_action=selected_action,
                    selected_semantic_action=semantic_action,
                    selected_reward=(selected.expected_reward if selected else None),
                    selected_failure=(
                        selected.failure_probability if selected else None
                    ),
                    maximum_reward=max(
                        point.expected_reward for point in result.frontier
                    ),
                    minimum_failure=min(
                        point.failure_probability for point in result.frontier
                    ),
                    normalizer=normalizer,
                )
            )
            for action in _ordered(kernel.actions(state)):
                conditioned = solve_ground_action_frontier(
                    kernel,
                    query,
                    state=state,
                    remaining=remaining,
                    action=action,
                )
                action_records.append(
                    ActionConditionedParetoFrontier(
                        state,
                        remaining,
                        action,
                        _frontier_values(conditioned),
                    )
                )
    records.sort(key=lambda record: (repr(record.state), record.remaining))
    action_records.sort(
        key=lambda record: (
            repr(record.state),
            record.remaining,
            repr(record.ground_action),
        )
    )
    return GroundOracleTable(
        registered,
        max_horizon,
        tuple((name, Fraction(value)) for name, value in reward_weights),
        goal,
        Fraction(delta),
        tuple(records),
        tuple(action_records),
    )


def oracle_signature_atoms(table: GroundOracleTable) -> tuple[OracleSignatureAtom, ...]:
    """Return the frozen compact Phase-3A oracle atom basis."""

    return tuple(
        atom
        for remaining in range(1, table.max_horizon + 1)
        for atom in (
            OracleSignatureAtom(
                f"h{remaining}:selected_semantic_action@delta", remaining, "action"
            ),
            OracleSignatureAtom(
                f"h{remaining}:maximum_normalized_reward", remaining, "reward"
            ),
        )
    )


def _atom_value(
    table: GroundOracleTable,
    atom: OracleSignatureAtom,
    state: Hashable,
) -> Hashable:
    record = table.record(state, atom.remaining)
    if atom.channel == "action":
        return record.selected_semantic_action
    if atom.channel == "reward":
        return record.maximum_reward / record.normalizer
    raise ValueError(f"unsupported oracle signature channel: {atom.channel!r}")


def oracle_partition(
    kernel: Any,
    states: Iterable[Hashable],
    semantic_adapter: Any,
    table: GroundOracleTable,
    atoms: Iterable[OracleSignatureAtom],
) -> Partition:
    """Build one state-only partition from a selected oracle atom subset."""

    selected = tuple(sorted(atoms, key=lambda atom: atom.atom_id))
    mapping: dict[Hashable, Hashable] = {}
    for state in _ordered(states):
        if kernel.is_terminal(state):
            status = getattr(getattr(state, "status", None), "value", "terminal")
            mapping[state] = ("terminal", status)
            continue
        labels = _ordered(semantic_adapter.labels(kernel, state))
        if not labels:
            raise ValueError("active oracle-partition state has no semantic action")
        mapping[state] = (
            "active",
            labels,
            tuple((atom.atom_id, _atom_value(table, atom, state)) for atom in selected),
        )
    return Partition.from_mapping(mapping)


def _nominal_proposal(result: Any) -> Any:
    if result.selected is not None:
        return result.selected
    if not result.frontier:
        raise RuntimeError("nominal quotient has no policy proposal")
    return min(
        result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def _reachable_mixed_cells(
    kernel: Any,
    query: QuerySpec[Any],
    partition: Partition,
    policy: FiniteHorizonPolicy[Any, Any],
    semantic_adapter: Any,
    orbit_key: Callable[[Hashable], Hashable],
) -> tuple[Hashable, ...]:
    lifted = lift_semantic_policy_decisions(
        kernel,
        query,
        partition,
        policy,
        semantic_adapter,
    )
    reachable_orbits: dict[Hashable, set[Hashable]] = {}
    for decision in lifted.decisions:
        cell = partition.cell_of(decision.state)
        reachable_orbits.setdefault(cell, set()).add(orbit_key(decision.state))
    return tuple(
        cell
        for cell in partition.cell_ids
        if len(reachable_orbits.get(cell, set())) > 1
    )


def select_oracle_partition(
    kernel: Any,
    states: Iterable[Hashable],
    semantic_adapter: Any,
    table: GroundOracleTable,
    training_queries: Iterable[QuerySpec[Any]],
    *,
    regret_tolerance: Fraction = Fraction(1, 100),
    minimum_compression: Fraction = Fraction(5),
    orbit_key: Callable[[Hashable], Hashable] | None = None,
    require_reachable_mixed_cell: bool = True,
) -> OraclePartitionSelection:
    """Exhaustively select the smallest audited train-only atom partition.

    Candidate subsets are enumerated by cardinality and canonical atom ID.
    Every candidate is materialized against its own labelled partition; this
    avoids reusing an isomorphic model whose cell identifiers came from a
    different atom subset.  The final tie order is cell count, atom count,
    atom IDs, then the label-independent partition signature.  No held-out
    query enters this function.
    """

    registered = _ordered(states)
    queries = tuple(training_queries)
    if not queries:
        raise ValueError("oracle partition selection requires training queries")
    if any(query.horizon > table.max_horizon for query in queries):
        raise ValueError("training query horizon exceeds the oracle table")
    atoms = oracle_signature_atoms(table)
    identity_orbit = orbit_key or (lambda state: state)
    trace: list[OracleCandidateEvaluation] = []
    passing: list[
        tuple[
            Partition,
            QuotientModels,
            tuple[OracleSignatureAtom, ...],
            tuple[OracleTrainingEvaluation, ...],
            tuple[Hashable, ...],
        ]
    ] = []
    for count in range(len(atoms) + 1):
        for subset in combinations(atoms, count):
            partition = oracle_partition(
                kernel,
                registered,
                semantic_adapter,
                table,
                subset,
            )
            signature = partition.signature()
            compression = Fraction(len(registered), len(partition.cell_ids))
            atom_ids = tuple(atom.atom_id for atom in subset)
            try:
                models = build_quotient_models(
                    kernel,
                    registered,
                    partition,
                    semantic_adapter=semantic_adapter,
                )
                evaluations_list: list[OracleTrainingEvaluation] = []
                mixed: set[Hashable] = set()
                for query in queries:
                    proposal = _nominal_proposal(
                        solve_nominal_pareto(models.nominal, query)
                    )
                    audit = audit_abstract_policy(
                        kernel,
                        query,
                        models.envelope,
                        proposal.policy,
                        regret_tolerance=regret_tolerance,
                    )
                    evaluations_list.append(
                        OracleTrainingEvaluation(query, proposal.policy, audit)
                    )
                    mixed.update(
                        _reachable_mixed_cells(
                            kernel,
                            query,
                            partition,
                            proposal.policy,
                            semantic_adapter,
                            identity_orbit,
                        )
                    )
                evaluations = tuple(evaluations_list)
                mixed_cells = _ordered(mixed)
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                detail = f"{type(error).__name__}: {error}"
                trace.append(
                    OracleCandidateEvaluation(
                        atom_ids,
                        len(partition.cell_ids),
                        compression,
                        False,
                        False,
                        None,
                        None,
                        0,
                        signature,
                        detail,
                    )
                )
                continue
            regret_values = tuple(
                evaluation.audit.regret_upper
                for evaluation in evaluations
                if evaluation.audit.regret_upper is not None
            )
            maximum_regret = max(regret_values) if regret_values else None
            failure_excesses = tuple(
                max(
                    Fraction(0),
                    evaluation.audit.lifted_failure_upper - evaluation.query.delta,
                )
                for evaluation in evaluations
                if evaluation.audit.lifted_failure_upper is not None
            )
            maximum_failure_excess = (
                max(failure_excesses) if failure_excesses else None
            )
            certified = all(evaluation.audit.certified for evaluation in evaluations)
            trace.append(
                OracleCandidateEvaluation(
                    atom_ids,
                    len(partition.cell_ids),
                    compression,
                    True,
                    certified,
                    maximum_regret,
                    maximum_failure_excess,
                    len(mixed_cells),
                    signature,
                )
            )
            nontrivial = bool(mixed_cells) or not require_reachable_mixed_cell
            if certified and compression >= minimum_compression and nontrivial:
                passing.append(
                    (partition, models, subset, evaluations, mixed_cells)
                )

    if not passing:
        raise RuntimeError("no oracle-signature partition passed the training gate")
    partition, models, selected, evaluations, mixed_cells = min(
        passing,
        key=lambda item: (
            len(item[0].cell_ids),
            len(item[2]),
            tuple(atom.atom_id for atom in item[2]),
            item[0].signature(),
        ),
    )
    return OraclePartitionSelection(
        partition,
        models,
        tuple(selected),
        tuple(trace),
        tuple(evaluations),
        tuple(mixed_cells),
    )


__all__ = [
    "ActionConditionedParetoFrontier",
    "GroundOracleRecord",
    "GroundOracleTable",
    "OracleCandidateEvaluation",
    "OracleFrontierPoint",
    "OraclePartitionSelection",
    "OracleSignatureAtom",
    "OracleTrainingEvaluation",
    "build_ground_oracle_table",
    "oracle_partition",
    "oracle_signature_atoms",
    "select_oracle_partition",
]
