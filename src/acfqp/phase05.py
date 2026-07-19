"""Executable Phase 0.5 vertical slice for both canonical tiny domains."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Hashable, Iterable

from acfqp.abstraction import Partition, QuotientModels, build_quotient_models
from acfqp.artifacts import (
    PHASE05_REQUIRED_PATHS,
    canonical_json,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
    write_json,
)
from acfqp.core import QuerySpec
from acfqp.build_coverage import BuildCoverage, transition_closure
from acfqp.domains import G2048Kernel, generate_solvable_lmb
from acfqp.domains.semantic import (
    BoundaryActionLabel,
    G2048SemanticAdapter,
    LMBSemanticAdapter,
    restriction_diagnostic,
)
from acfqp.enumeration import EnumerationStatus, enumerate_reachable
from acfqp.planning import (
    AbstractPolicyAudit,
    FiniteHorizonPolicy,
    audit_abstract_policy,
    solve_ground_pareto,
    solve_nominal_pareto,
)
from acfqp.planning.common import reward_weights as normalized_reward_weights
from acfqp.refinement import (
    CEGARStatus,
    Predicate,
    RankedSplitCandidate,
    RefinementBudget,
    RefinementCounters,
    RefinementTracker,
    attempt_split,
    record_ground_fallback,
    refine_once,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_CAP = 50_000


@dataclass(frozen=True)
class Fixture:
    name: str
    kernel: Any
    adapter: Any
    query: QuerySpec[Any]
    structural: dict[str, Any]
    normalizer: Fraction
    generation_evidence: Any = None


@dataclass(frozen=True)
class WitnessPlan:
    cell: Hashable
    action: Hashable
    remaining: int
    left: Hashable
    right: Hashable
    observed_gap: Fraction
    predicate: Predicate
    candidate: RankedSplitCandidate
    parent_width: Fraction
    child_width: Fraction
    provisional_partition: Partition


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timed(callable_: Any) -> tuple[Any, int]:
    start = time.perf_counter_ns()
    value = callable_()
    return value, time.perf_counter_ns() - start


def _fixture(name: str) -> Fixture:
    if name == "g2048":
        kernel = G2048Kernel(2)
        horizon = 1
        normalizer = Fraction(horizon)
        query = QuerySpec(
            kernel.initial_distribution(),
            horizon,
            (("merge", Fraction(1)),),
            "default",
            Fraction(1, 20),
            normalizer,
            "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
        )
        return Fixture(
            name,
            kernel,
            G2048SemanticAdapter(),
            query,
            {
                "structural_key": "g2048_select_canonical_2x2_v0",
                "benchmark_role": "infeasibility_and_soundness_regression",
                "domain": "G2048-Select",
                "board_size": 2,
                "rank_cap": kernel.rank_cap,
                "horizon_max": kernel.horizon,
                "phase05_query_horizon": horizon,
                "spawn_distribution": kernel.spawn_distribution,
                "semantic_action_adapter": "boundary-actions.v1",
                "initial_partition": "active/status",
                "grammar_version": "phase05-domain-atoms.v1",
            },
            normalizer,
        )
    if name == "lmb":
        kernel, evidence = generate_solvable_lmb(
            tile_count=6,
            type_count=2,
            capacity=3,
            max_layers=1,
            seed=17,
        )
        normalizer = Fraction(2 * kernel.tile_count, 3)
        query = QuerySpec(
            kernel.initial_distribution(),
            kernel.horizon,
            (
                ("match", Fraction(1)),
                ("terminal_clear", Fraction(1)),
            ),
            "default",
            Fraction(1, 20),
            normalizer,
            "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
        )
        return Fixture(
            name,
            kernel,
            LMBSemanticAdapter(),
            query,
            {
                "structural_key": "lmb_generated_n6_t2_k3_d1_v0",
                "benchmark_role": "phase05_construction_and_fallback_regression",
                "domain": "Layered Matching Buffer",
                "tile_count": kernel.tile_count,
                "type_count": kernel.type_count,
                "capacity": kernel.capacity,
                "max_layers": kernel.max_layers,
                "horizon_max": kernel.horizon,
                "tile_types": kernel.tile_types,
                "blockers": kernel.blockers,
                "generation_seed": 17,
                "semantic_action_adapter": "boundary-actions.v1",
                "initial_partition": "status + remaining_object_count<=5/2",
                "grammar_version": "phase05-domain-atoms.v1",
            },
            normalizer,
            evidence,
        )
    raise ValueError(f"unknown Phase 0.5 fixture: {name!r}")


def _transition_closure(
    kernel: Any,
    initial_distribution: Iterable[tuple[Fraction, Hashable]],
    state_cap: int = STATE_CAP,
) -> tuple[Hashable, ...]:
    """Backward-compatible wrapper around the public coverage constructor."""

    return transition_closure(
        kernel,
        initial_distribution,
        state_cap=state_cap,
    )


def _status_name(state: Any) -> str:
    status = getattr(state, "status", None)
    return str(getattr(status, "value", status or "terminal"))


def _initial_partition(fixture: Fixture, states: Iterable[Hashable]) -> Partition:
    mapping: dict[Hashable, str] = {}
    for state in states:
        if fixture.kernel.is_terminal(state):
            mapping[state] = f"terminal:{_status_name(state)}"
        elif fixture.name == "lmb":
            features = dict(fixture.adapter.features(fixture.kernel, state))
            mapping[state] = (
                "active:late"
                if features["remaining_object_count"] <= Fraction(5, 2)
                else "active:early"
            )
        else:
            mapping[state] = "active:root"
    return Partition.from_mapping(mapping)


def _state_catalog(states: Iterable[Hashable]) -> dict[Hashable, str]:
    return {state: object_id(state, "state") for state in sorted(states, key=repr)}


def _policy_document(
    policy: FiniteHorizonPolicy[Any, Any] | None,
    state_ids: dict[Hashable, str],
    *,
    level: str,
    transition_source: Any | None = None,
) -> dict[str, Any] | None:
    if policy is None:
        return None
    policy_id = object_id({"level": level, "signature": policy.signature()}, "policy")
    node_ids = {
        (decision.remaining, decision.state): object_id(
            {
                "policy_id": policy_id,
                "remaining": decision.remaining,
                "state_or_cell": state_ids.get(decision.state) or str(decision.state),
            },
            "policy-node",
        )
        for decision in policy.decisions
    }
    decisions = []
    for decision in policy.decisions:
        state_reference = state_ids.get(decision.state)
        child_states: tuple[Hashable, ...] = ()
        if transition_source is not None and decision.remaining > 1:
            if hasattr(transition_source, "step"):
                child_states = tuple(
                    sorted(
                        {
                            outcome.next_state
                            for outcome in transition_source.step(
                                decision.state, decision.action
                            )
                            if not outcome.failure
                            and not outcome.terminal
                            and not transition_source.is_terminal(outcome.next_state)
                        },
                        key=repr,
                    )
                )
            elif hasattr(transition_source, "transition"):
                child_states = tuple(
                    successor
                    for successor, probability in transition_source.transition(
                        decision.state, decision.action
                    ).successor_probabilities
                    if probability > 0
                )
        child_node_ids = [
            node_ids[(decision.remaining - 1, child)]
            for child in child_states
            if (decision.remaining - 1, child) in node_ids
        ]
        decisions.append(
            {
                "node_id": node_ids[(decision.remaining, decision.state)],
                "remaining": decision.remaining,
                "state_or_cell": state_reference or str(decision.state),
                "state_repr": repr(decision.state),
                "action": decision.action,
                "child_node_ids": child_node_ids,
            }
        )
    return {
        "policy_id": policy_id,
        "level": level,
        "selector_class": "deterministic_finite_horizon_markov",
        "decisions": decisions,
        "signature": policy.signature(),
    }


def _frontier_document(
    result: Any,
    state_ids: dict[Hashable, str],
    level: str,
    *,
    query_id: str,
    transition_source: Any | None = None,
    oracle_accounting: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_signature = result.selected.policy.signature() if result.selected else None
    frontier = []
    for point in result.frontier:
        policy_document = _policy_document(
            point.policy,
            state_ids,
            level=level,
            transition_source=transition_source,
        )
        frontier.append(
            {
                "frontier_point_id": object_id(
                    {
                        "query_id": query_id,
                        "expected_reward": point.expected_reward,
                        "failure_probability": point.failure_probability,
                        "policy_id": policy_document["policy_id"],
                    },
                    "frontier-point",
                ),
                "expected_reward": point.expected_reward,
                "failure_probability": point.failure_probability,
                "selected": point.policy.signature() == selected_signature,
                "policy": policy_document,
            }
        )
    return {
        "query_id": query_id,
        "feasible": result.feasible,
        "composed_candidate_count": result.composed_candidate_count,
        "selection": {
            "status": "SELECTED" if result.selected is not None else "INFEASIBLE_QUERY",
            "selected_policy_id": (
                next(
                    item["policy"]["policy_id"]
                    for item in frontier
                    if item["selected"]
                )
                if result.selected is not None
                else None
            ),
        },
        "oracle_accounting": oracle_accounting,
        "frontier": frontier,
    }


def _enumeration_document(
    result: Any, state_ids: dict[Hashable, str], kernel: Any
) -> dict[str, Any]:
    transitions = []
    failure_states: set[str] = set()
    for transition in result.transitions:
        record = {
            "depth": transition.depth,
            "state": state_ids[transition.state],
            "action": transition.action,
            "outcomes": [
                {
                    "probability": outcome.probability,
                    "next_state": state_ids[outcome.next_state],
                    "reward_features": outcome.reward_features,
                    "entered_failure": outcome.failure,
                    "terminal": outcome.terminal,
                }
                for outcome in transition.outcomes
            ],
        }
        record["transition_id"] = object_id(record, "transition")
        transitions.append(record)
        failure_states.update(
            state_ids[outcome.next_state]
            for outcome in transition.outcomes
            if outcome.failure
        )
    terminal_states = {
        state_ids[state] for state in result.states if kernel.is_terminal(state)
    }
    success_states = terminal_states - failure_states
    kernel_payload = {"horizon": result.horizon, "transitions": transitions}
    return {
        "status": result.status,
        "evaluation_tier": result.evaluation_tier,
        "complete": result.complete,
        "horizon": result.horizon,
        "state_count": result.state_count,
        "state_count_lower_bound": result.state_count_lower_bound,
        "state_count_by_depth": [len(layer) for layer in result.layers],
        "cap_handling": {
            "state_cap": STATE_CAP,
            "cap_exceeded": result.status is EnumerationStatus.STATE_CAP_EXCEEDED,
            "truncated_result_is_exact_sound": False,
        },
        "layers": [[state_ids[state] for state in layer] for layer in result.layers],
        "states": [
            {
                "id": state_ids[state],
                "state": state,
                "terminal": kernel.is_terminal(state),
            }
            for state in result.states
        ],
        "failure_set": sorted(failure_states),
        "success_set": sorted(success_states),
        "failure_success_sets_disjoint": not bool(failure_states & success_states),
        "transitions": transitions,
        "transition_kernel_sha256": canonical_sha256(kernel_payload),
    }


def _partition_document(
    partition: Partition,
    state_ids: dict[Hashable, str],
    *,
    ground_state_count: int,
) -> dict[str, Any]:
    return {
        "cell_count": len(partition.cell_ids),
        "ground_state_count": ground_state_count,
        "compression_ratio": Fraction(ground_state_count, len(partition.cell_ids)),
        "signature": partition.signature(),
        "cells": [
            {
                "cell_id": str(cell),
                "members": [state_ids[state] for state in partition.members(cell)],
            }
            for cell in partition.cell_ids
        ],
    }


def _nominal_document(models: QuotientModels) -> dict[str, Any]:
    return {
        "purpose": "proposal_only",
        "construction": "arithmetic mean over represented exact ground realizations",
        "entries": [
            {
                "cell": str(entry.cell),
                "action": entry.action,
                "reward_features": entry.model.reward_features,
                "successor_probabilities": tuple(
                    (str(cell), probability)
                    for cell, probability in entry.model.successor_probabilities
                ),
                "failure_probability": entry.model.failure_probability,
                "termination_probability": entry.model.termination_probability,
                "realization_count": entry.model.realization_count,
            }
            for entry in models.nominal.entries
        ],
    }


def _envelope_document(
    models: QuotientModels,
    state_ids: dict[Hashable, str],
    query: QuerySpec[Any],
) -> dict[str, Any]:
    weights = normalized_reward_weights(query)
    entries = []
    for entry in models.envelope.entries:
        record = {
            "cell": str(entry.cell),
            "action": entry.action,
            "reward_lower": min(
                (realization.reward(weights) for realization in entry.realizations),
                default=Fraction(0),
            ),
            "reward_upper": max(
                (realization.reward(weights) for realization in entry.realizations),
                default=Fraction(0),
            ),
            "failure_lower": min(
                (realization.failure_probability for realization in entry.realizations),
                default=Fraction(0),
            ),
            "failure_upper": max(
                (realization.failure_probability for realization in entry.realizations),
                default=Fraction(0),
            ),
            "realizations": [
                {
                    "state": state_ids[realization.state],
                    "reward_features": realization.reward_features,
                    "successor_probabilities": tuple(
                        (str(cell), probability)
                        for cell, probability in realization.successor_probabilities
                    ),
                    "failure_probability": realization.failure_probability,
                    "termination_probability": realization.termination_probability,
                }
                for realization in entry.realizations
            ],
        }
        record["entry_id"] = object_id(record, "envelope-entry")
        entries.append(record)
    return {
        "purpose": "independent_exact_sound_audit",
        "construction": "enumerate every correlated ground realization; no nominal residual used",
        "entries": entries,
    }


def _pointwise_audits(
    fixture: Fixture,
    models: QuotientModels,
    policy: FiniteHorizonPolicy[Any, Any],
    state_ids: dict[Hashable, str],
) -> list[dict[str, Any]]:
    records = []
    for probability, state in fixture.query.initial_distribution:
        point_query = QuerySpec.from_state(
            state,
            horizon=fixture.query.horizon,
            reward_weights=fixture.query.reward_weights,
            goal=fixture.query.goal,
            delta=fixture.query.delta,
            normalizer=fixture.query.normalizer,
            normalizer_proof_id=fixture.query.normalizer_proof_id,
        )
        audit = audit_abstract_policy(
            fixture.kernel, point_query, models.envelope, policy
        )
        records.append(
            {
                "point_query_id": object_id(point_query, "query"),
                "initial_probability": probability,
                "state": state_ids[state],
                "root_cell": str(models.envelope.partition.cell_of(state)),
                "unrestricted_reward_upper": audit.unrestricted_reward_upper,
                "lifted_reward_lower": audit.lifted_reward_lower,
                "lifted_failure_upper": audit.lifted_failure_upper,
                "regret_upper": audit.regret_upper,
                "certified": audit.certified,
            }
        )
    return records


def _audit_document(
    audit: AbstractPolicyAudit,
    pointwise: list[dict[str, Any]],
    *,
    query_id: str,
    policy_document: dict[str, Any],
    envelope_document: dict[str, Any],
    envelope_artifact: str,
    kernel_sha256: str,
    audit_stage: str,
) -> dict[str, Any]:
    regrets = [record["regret_upper"] for record in pointwise if record["regret_upper"] is not None]
    risks = [
        record["lifted_failure_upper"]
        for record in pointwise
        if record["lifted_failure_upper"] is not None
    ]
    aggregate_certified = audit.certified
    pointwise_all_certified = bool(pointwise) and all(
        record["certified"] for record in pointwise
    )
    combined_certified = aggregate_certified and pointwise_all_certified
    bound_ids = {
        (str(bound.cell), bound.remaining): object_id(
            {
                "audit_stage": audit_stage,
                "cell": str(bound.cell),
                "remaining": bound.remaining,
            },
            "proof-bound",
        )
        for bound in audit.reachable_bounds
    }
    policy_nodes = {
        (decision["state_or_cell"], decision["remaining"]): decision
        for decision in policy_document["decisions"]
    }
    envelope_entries = {
        (entry["cell"], canonical_json(entry["action"])): entry
        for entry in envelope_document["entries"]
    }
    reachable_bounds = []
    proof_dependencies = []
    for bound in audit.reachable_bounds:
        key = (str(bound.cell), bound.remaining)
        policy_node = policy_nodes.get(key)
        envelope_entry = (
            envelope_entries.get((key[0], canonical_json(policy_node["action"])))
            if policy_node is not None
            else None
        )
        child_ids: set[str] = set()
        if envelope_entry is not None and bound.remaining > 0:
            for realization in envelope_entry["realizations"]:
                for successor, probability in realization["successor_probabilities"]:
                    if probability > 0:
                        child_id = bound_ids.get((successor, bound.remaining - 1))
                        if child_id is not None:
                            child_ids.add(child_id)
        bound_id = bound_ids[key]
        reachable_bounds.append(
            {
                "bound_id": bound_id,
                "cell": str(bound.cell),
                "remaining": bound.remaining,
                "semantic_action": policy_node["action"] if policy_node else None,
                "reward_lower": bound.reward_lower,
                "failure_upper": bound.failure_upper,
            }
        )
        proof_dependencies.append(
            {
                "dependency_id": bound_id,
                "kind": "cell_policy_bound" if envelope_entry else "terminal_base",
                "cell": str(bound.cell),
                "remaining_horizon": bound.remaining,
                "policy_node_id": policy_node["node_id"] if policy_node else None,
                "envelope_ref": (
                    {
                        "artifact": envelope_artifact,
                        "entry_id": envelope_entry["entry_id"],
                    }
                    if envelope_entry is not None
                    else None
                ),
                "kernel_ref": {
                    "artifact": "ground/enumeration.json",
                    "transition_kernel_sha256": kernel_sha256,
                },
                "query_ref": {
                    "artifact": "config/query.json",
                    "query_id": query_id,
                },
                "child_dependency_ids": sorted(child_ids),
            }
        )
    root_dependency_id = object_id(
        {"audit_stage": audit_stage, "query_id": query_id, "kind": "rho0_aggregate"},
        "proof-root",
    )
    root_children = sorted(
        {
            bound_ids[(record["root_cell"], max(bound.remaining for bound in audit.reachable_bounds))]
            for record in pointwise
            if (
                record["root_cell"],
                max(bound.remaining for bound in audit.reachable_bounds),
            )
            in bound_ids
        }
    ) if audit.reachable_bounds else []
    proof_dependencies.append(
        {
            "dependency_id": root_dependency_id,
            "kind": "rho0_aggregate",
            "query_ref": {"artifact": "config/query.json", "query_id": query_id},
            "child_dependency_ids": root_children,
            "point_query_ids": [record["point_query_id"] for record in pointwise],
        }
    )
    return {
        "audit_stage": audit_stage,
        "evidence": "exact_sound",
        "query_id": query_id,
        "policy_id": policy_document["policy_id"],
        "policy": policy_document,
        "U_all": audit.unrestricted_reward_upper,
        "L_pi": audit.lifted_reward_lower,
        "U_F": audit.lifted_failure_upper,
        "unrestricted_reward_upper": audit.unrestricted_reward_upper,
        "lifted_reward_lower": audit.lifted_reward_lower,
        "lifted_failure_upper": audit.lifted_failure_upper,
        "regret_upper": audit.regret_upper,
        "regret_tolerance": audit.regret_tolerance,
        "risk_tolerance": audit.risk_tolerance,
        "aggregate_certified": aggregate_certified,
        "pointwise_all_certified": pointwise_all_certified,
        "certified": combined_certified,
        "certification_scope": "rho0_aggregate_and_every_initial_support_point",
        "pointwise": pointwise,
        "maximum_pointwise_regret_upper": max(regrets) if regrets else None,
        "maximum_pointwise_failure_upper": max(risks) if risks else None,
        "issues": audit.issues,
        "reachable_bounds": reachable_bounds,
        "proof_dependencies": proof_dependencies,
        "certificate_dependency_ids": [root_dependency_id],
        "proof_dependency_count": len(proof_dependencies),
    }


def _realization_vector(realization: Any, weights: dict[str, Fraction]) -> tuple[Any, ...]:
    return (
        realization.reward(weights),
        realization.failure_probability,
        dict(realization.successor_probabilities),
    )


def _realization_distance(left: Any, right: Any, weights: dict[str, Fraction]) -> Fraction:
    left_vector = _realization_vector(left, weights)
    right_vector = _realization_vector(right, weights)
    successors = set(left_vector[2]) | set(right_vector[2])
    transition_distance = sum(
        (
            abs(
                left_vector[2].get(cell, Fraction(0))
                - right_vector[2].get(cell, Fraction(0))
            )
            for cell in successors
        ),
        Fraction(0),
    ) / 2
    return (
        abs(left_vector[0] - right_vector[0])
        + abs(left_vector[1] - right_vector[1])
        + transition_distance
    )


def _cell_width(
    models: QuotientModels,
    cell: Hashable,
    action: Hashable,
    weights: dict[str, Fraction],
) -> Fraction:
    if action not in models.envelope.actions(cell):
        return Fraction(0)
    realizations = models.envelope.realizations(cell, action)
    return max(
        (
            _realization_distance(left, right, weights)
            for left in realizations
            for right in realizations
        ),
        default=Fraction(0),
    )


def _fixed_refinement_witness(
    fixture: Fixture,
    states: tuple[Hashable, ...],
    partition: Partition,
    models: QuotientModels,
    policy: FiniteHorizonPolicy[Any, Any],
) -> WitnessPlan:
    if fixture.name == "g2048":
        cell = "active:root"
        feature_name = "rank_sum"
        threshold = Fraction(3)
        initial_rate = Fraction(0)
    else:
        cell = "active:late"
        feature_name = "action_count"
        threshold = Fraction(3, 2)
        initial_rate = Fraction(6)
    action = BoundaryActionLabel.FIRST
    remaining_values = [
        decision.remaining
        for decision in policy.decisions
        if decision.state == cell and decision.action == action
    ]
    if not remaining_values:
        raise AssertionError(f"nominal policy does not reach refinement cell {cell!r}")
    remaining = max(remaining_values)

    feature_cache = {
        state: dict(fixture.adapter.features(fixture.kernel, state))
        for state in partition.members(cell)
    }
    predicate = Predicate(
        feature_name,
        "<=",
        threshold,
        lambda state: feature_cache[state][feature_name],
    )
    provisional = attempt_split(partition, cell, predicate, RefinementTracker())
    if not provisional.accepted:
        raise AssertionError(f"pre-registered Phase 0.5 predicate is not a split: {provisional}")
    provisional_models = build_quotient_models(
        fixture.kernel,
        states,
        provisional.partition,
        semantic_adapter=fixture.adapter,
    )
    weights = normalized_reward_weights(fixture.query)
    parent_width = _cell_width(models, cell, action, weights)
    child_width = max(
        _cell_width(provisional_models, child, action, weights)
        for child in (provisional.false_cell, provisional.true_cell)
        if child is not None
    )
    reduction = parent_width - child_width
    if reduction < 0:
        raise AssertionError("a split cannot have a negative exact width reduction")

    realizations = models.envelope.realizations(cell, action)
    separating_pairs = [
        (left, right)
        for index, left in enumerate(realizations)
        for right in realizations[index + 1 :]
        if predicate(left.state) != predicate(right.state)
    ]
    if not separating_pairs:
        raise AssertionError("pre-registered predicate has no exact witness pair")
    left, right = min(
        separating_pairs,
        key=lambda pair: (
            -_realization_distance(pair[0], pair[1], weights),
            repr(pair[0].state),
            repr(pair[1].state),
        ),
    )
    feature_count = len(feature_cache[left.state])
    rate_cost = Fraction(1 + math.ceil(math.log2(feature_count)))
    if initial_rate:
        rate_cost += 1  # depth charge for the pre-partitioned LMB cell
    candidate = RankedSplitCandidate(
        predicate,
        audit_width_reduction=reduction,
        newly_certified_pairs=0,
        failure_width_reduction=Fraction(0),
        rate_cost=rate_cost,
    )
    return WitnessPlan(
        cell,
        action,
        remaining,
        left.state,
        right.state,
        _realization_distance(left, right, weights),
        predicate,
        candidate,
        parent_width,
        child_width,
        provisional.partition,
    )


def _select_nominal_proposal(result: Any) -> Any:
    if result.selected is not None:
        return result.selected
    if not result.frontier:
        raise RuntimeError("nominal quotient has no contingent policy proposal")
    return min(
        result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def _source_tree_hash() -> str:
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = PROJECT_ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for filename in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = PROJECT_ROOT / filename
        if path.is_file():
            paths.append(path)
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    paths = [PROJECT_ROOT / "DECISION_LEDGER.md", *sorted((PROJECT_ROOT / "specs").glob("*.md"))]
    return {path.relative_to(PROJECT_ROOT).as_posix(): sha256_file(path) for path in paths}


def _reference_manifest_hashes() -> dict[str, str]:
    result = {}
    for filename in ("download_manifest.json", "repo_clone_manifest.json"):
        path = PROJECT_ROOT / "reference" / filename
        if path.is_file():
            result[f"reference/{filename}"] = sha256_file(path)
    return result


def run_fixture(
    name: str,
    output_dir: Path,
    *,
    query_override: QuerySpec[Any] | None = None,
) -> dict[str, Any]:
    """Run and write one complete, exact Phase 0.5 benchmark bundle."""

    started = _utc_now()
    total_start = time.perf_counter_ns()
    fixture = _fixture(name)
    if query_override is not None:
        fixture = replace(
            fixture,
            query=query_override,
            normalizer=query_override.normalizer,
        )
    if fixture.normalizer != fixture.query.normalizer:
        raise AssertionError("fixture/query reward-normalizer metadata diverged")
    budget = RefinementBudget.phase05()

    enumeration, enumeration_ns = _timed(
        lambda: enumerate_reachable(
            fixture.kernel,
            initial_distribution=fixture.query.initial_distribution,
            horizon=fixture.query.horizon,
            state_cap=STATE_CAP,
        )
    )
    if enumeration.status is not EnumerationStatus.EXACT or not enumeration.complete:
        raise RuntimeError("canonical Phase 0.5 fixture exceeded exact enumeration")
    build_coverage, closure_ns = _timed(
        lambda: BuildCoverage.from_query(
            fixture.kernel,
            fixture.query,
            state_cap=STATE_CAP,
        )
    )
    closure = build_coverage.covered_states
    closure_ids = _state_catalog(closure)
    enumeration_ids = _state_catalog(enumeration.states)

    ground, j0_ns = _timed(lambda: solve_ground_pareto(fixture.kernel, fixture.query))
    partition_before = _initial_partition(fixture, closure)
    models_before, model_before_ns = _timed(
        lambda: build_quotient_models(
            fixture.kernel,
            closure,
            partition_before,
            semantic_adapter=fixture.adapter,
        )
    )
    nominal_before, nominal_before_ns = _timed(
        lambda: solve_nominal_pareto(models_before.nominal, fixture.query)
    )
    proposal_before = _select_nominal_proposal(nominal_before)
    audit_before, audit_before_ns = _timed(
        lambda: audit_abstract_policy(
            fixture.kernel,
            fixture.query,
            models_before.envelope,
            proposal_before.policy,
        )
    )
    before_pointwise = _pointwise_audits(
        fixture, models_before, proposal_before.policy, closure_ids
    )
    before_combined_certified = audit_before.certified and all(
        record["certified"] for record in before_pointwise
    )
    if before_combined_certified:
        raise AssertionError("Phase 0.5 fixture must begin with an uncertified proposal")

    witness_plan, witness_ns = _timed(
        lambda: _fixed_refinement_witness(
            fixture,
            closure,
            partition_before,
            models_before,
            proposal_before.policy,
        )
    )
    tracker = RefinementTracker()
    initial_rate = Fraction(5) if name == "lmb" else Fraction(0)
    if name == "lmb":
        tracker.path_predicates[witness_plan.cell] = (
            "remaining_object_count|<=|5/2",
        )
    counters = RefinementCounters(
        leaves=len(partition_before.cell_ids),
        accepted_splits=0,
        rate_bits=initial_rate,
        candidate_evaluations=0,
        fallback_invocations=0,
    )
    refinement, refinement_ns = _timed(
        lambda: refine_once(
            partition_before,
            witness_plan.cell,
            (witness_plan.candidate,),
            tracker,
            budget,
            counters,
            current_audit_width=witness_plan.parent_width,
            witness=(witness_plan.left, witness_plan.right),
            already_certified=False,
            # J0 is an evaluation oracle here; Phase 0.5 still exercises the
            # mandatory construction step before charged production fallback.
            query_feasible=True,
        )
    )
    if refinement.status is not CEGARStatus.SPLIT_ACCEPTED:
        raise AssertionError(f"mandatory deterministic split failed: {refinement}")
    partition_after = refinement.partition
    models_after, model_after_ns = _timed(
        lambda: build_quotient_models(
            fixture.kernel,
            closure,
            partition_after,
            semantic_adapter=fixture.adapter,
        )
    )
    nominal_after, nominal_after_ns = _timed(
        lambda: solve_nominal_pareto(models_after.nominal, fixture.query)
    )
    proposal_after = _select_nominal_proposal(nominal_after)
    audit_after, audit_after_ns = _timed(
        lambda: audit_abstract_policy(
            fixture.kernel,
            fixture.query,
            models_after.envelope,
            proposal_after.policy,
        )
    )
    after_pointwise = _pointwise_audits(
        fixture, models_after, proposal_after.policy, closure_ids
    )

    fallback = None
    fallback_ns = 0
    fallback_charge = None
    final_policy = proposal_after.policy
    after_combined_certified = audit_after.certified and all(
        record["certified"] for record in after_pointwise
    )
    if after_combined_certified:
        final_status = CEGARStatus.CERTIFIED
    else:
        fallback_charge = record_ground_fallback(
            partition_after, budget, refinement.counters
        )
        if fallback_charge.status is not CEGARStatus.GROUND_FALLBACK:
            raise AssertionError("Phase 0.5 fallback budget unexpectedly exhausted")
        fallback, fallback_ns = _timed(
            lambda: solve_ground_pareto(fixture.kernel, fixture.query)
        )
        if fallback.selected is None:
            final_status = CEGARStatus.INFEASIBLE_QUERY
            final_policy = None
        else:
            final_status = CEGARStatus.GROUND_FALLBACK
            final_policy = fallback.selected.policy

    terminal_ns = time.perf_counter_ns() - total_start
    normalizer_proof_id = fixture.query.normalizer_proof_id
    query_payload = {
        "initial_distribution": fixture.query.initial_distribution,
        "initial_distribution_registration": (
            "two-distinct-cells conditioned on a legal merge"
            if name == "g2048"
            else "serialized generated layout with empty buffer"
        ),
        "horizon": fixture.query.horizon,
        "reward_weights": fixture.query.reward_weights,
        "goal": fixture.query.goal,
        "delta": fixture.query.delta,
        "normalizer": fixture.query.normalizer,
        "normalizer_value": fixture.query.normalizer,
        "normalizer_proof_id": normalizer_proof_id,
        "normalizer_proof": (
            "each G2048 normalized merge reward <=1, total<=H"
            if name == "g2048"
            else "at most N/3 matches plus clear bonus N/3, total<=2N/3"
        ),
    }
    query_id = object_id(query_payload, "query")
    query_document = {"query_id": query_id, **query_payload}
    seed_ledger = {
        "benchmark_generation": {
            "seed": 17 if name == "lmb" else None,
            "used": name == "lmb",
        },
        "lmb_backtracking": {
            "seed": 17 if name == "lmb" else None,
            "used": name == "lmb",
        },
        "fixture_selection_order": {
            "seed": None,
            "used": False,
            "deterministic_index": 0 if name == "g2048" else 1,
        },
        "diagnostic_replay_tapes": {
            "seed": None,
            "used": False,
        },
    }
    seed_ledger_id = object_id(seed_ledger, "seed-ledger")
    tape_ledger = {
        "diagnostic_replay": {
            "tape_id": "tape-none-exact-enumeration",
            "used": False,
            "reason": "Phase 0.5 uses exact outcome enumeration, not sampled replay",
        }
    }
    tape_ledger_id = object_id(tape_ledger, "tape-ledger")
    structural_document = {
        **fixture.structural,
        "state_cap": STATE_CAP,
        "phase05_budget": budget,
        "generation_evidence": fixture.generation_evidence,
        "pre_registered_refinement_predicate": witness_plan.predicate.canonical_id,
        "seed_ledger_id": seed_ledger_id,
        "seed_ledger": seed_ledger,
        "tape_ledger_id": tape_ledger_id,
        "tape_ledger": tape_ledger,
    }
    structural_id = object_id(structural_document, "fixture")
    structural_document = {"fixture_id": structural_id, **structural_document}
    witness_payload = {
        "cell": str(witness_plan.cell),
        "semantic_action": witness_plan.action,
        "remaining_horizon": witness_plan.remaining,
        "left_state": closure_ids[witness_plan.left],
        "right_state": closure_ids[witness_plan.right],
        "left_state_value": witness_plan.left,
        "right_state_value": witness_plan.right,
        "audit_channel": "exact_one_step_behavioural_envelope_width",
        "observed_gap": witness_plan.observed_gap,
        "separating_predicate": witness_plan.predicate.canonical_id,
    }
    witness_id = object_id(witness_payload, "witness")
    witness_document = {"witness_id": witness_id, **witness_payload}
    candidate_document = {
        "candidate_id": object_id(
            {
                "witness_id": witness_id,
                "predicate_id": witness_plan.predicate.canonical_id,
            },
            "split-candidate",
        ),
        "witness_id": witness_id,
        "predicate_id": witness_plan.predicate.canonical_id,
        "deterministic_rank": 1,
        "parent_width": witness_plan.parent_width,
        "child_max_width": witness_plan.child_width,
        "audit_width_reduction": witness_plan.candidate.audit_width_reduction,
        "newly_certified_pairs": witness_plan.candidate.newly_certified_pairs,
        "failure_width_reduction": witness_plan.candidate.failure_width_reduction,
        "rate_cost": witness_plan.candidate.rate_cost,
        "score": witness_plan.candidate.score,
        "quality_threshold_passed": (
            witness_plan.candidate.audit_width_reduction * 5
            >= witness_plan.parent_width
        ),
        "witness_separated": (
            witness_plan.predicate(witness_plan.left)
            != witness_plan.predicate(witness_plan.right)
        ),
        "rejection_reasons": [],
        "status": "ACCEPTED",
    }
    enumeration_document = _enumeration_document(
        enumeration, enumeration_ids, fixture.kernel
    )
    enumeration_document["covered_state_ids"] = list(
        build_coverage.covered_state_ids
    )
    enumeration_document["covered_state_count"] = (
        build_coverage.covered_state_count
    )
    envelope_before_document = _envelope_document(
        models_before, closure_ids, fixture.query
    )
    envelope_after_document = _envelope_document(
        models_after, closure_ids, fixture.query
    )
    proposal_before_document = _policy_document(
        proposal_before.policy,
        closure_ids,
        level="abstract",
        transition_source=models_before.nominal,
    )
    proposal_after_document = _policy_document(
        proposal_after.policy,
        closure_ids,
        level="abstract",
        transition_source=models_after.nominal,
    )
    if proposal_before_document is None or proposal_after_document is None:
        raise AssertionError("Phase 0.5 proposal policy document is missing")
    before_audit_document = _audit_document(
        audit_before,
        before_pointwise,
        query_id=query_id,
        policy_document=proposal_before_document,
        envelope_document=envelope_before_document,
        envelope_artifact="rapm/envelope_before.json",
        kernel_sha256=enumeration_document["transition_kernel_sha256"],
        audit_stage="pre_refinement",
    )
    after_audit_document = _audit_document(
        audit_after,
        after_pointwise,
        query_id=query_id,
        policy_document=proposal_after_document,
        envelope_document=envelope_after_document,
        envelope_artifact="rapm/envelope_after.json",
        kernel_sha256=enumeration_document["transition_kernel_sha256"],
        audit_stage="post_refinement",
    )
    j0_invocation_id = object_id(
        {"query_id": query_id, "ordinal": 1, "purpose": "J0_baseline"},
        "oracle-invocation",
    )
    j0_document = _frontier_document(
        ground,
        closure_ids,
        "ground_j0",
        query_id=query_id,
        transition_source=fixture.kernel,
        oracle_accounting={
            "invocation_id": j0_invocation_id,
            "ordinal": 1,
            "purpose": "J0_constrained_baseline",
            "same_query": True,
            "cache_hit": False,
            "composed_candidate_count": ground.composed_candidate_count,
            "elapsed_ns": j0_ns,
        },
    )
    fallback_invocation_id = (
        object_id(
            {"query_id": query_id, "ordinal": 2, "purpose": "charged_fallback"},
            "oracle-invocation",
        )
        if fallback is not None
        else None
    )
    fallback_document = (
        _frontier_document(
            fallback,
            closure_ids,
            "ground_fallback",
            query_id=query_id,
            transition_source=fixture.kernel,
            oracle_accounting={
                "invocation_id": fallback_invocation_id,
                "ordinal": 2,
                "purpose": "charged_same_query_fallback",
                "same_query": True,
                "cache_hit": False,
                "composed_candidate_count": fallback.composed_candidate_count,
                "elapsed_ns": fallback_ns,
            },
        )
        if fallback is not None
        else None
    )
    result_document = {
        "status": final_status,
        "evidence": "exact_sound",
        "query_id": query_id,
        "benchmark_role": fixture.structural["benchmark_role"],
        "claim_eligibility": (
            "infeasibility_only"
            if name == "g2048"
            else "benchmark_result_eligible_after_verification"
        ),
        "normalizer_value": fixture.query.normalizer,
        "normalizer_proof_id": normalizer_proof_id,
        "raw_regret_upper": (
            audit_after.regret_upper * fixture.query.normalizer
            if audit_after.regret_upper is not None
            else None
        ),
        "normalized_regret_upper": audit_after.regret_upper,
        "abstract_audit": after_audit_document,
        "fallback": fallback_document,
        "fallback_location": (
            {
                "initial_cells": sorted(
                    {
                        str(partition_after.cell_of(state))
                        for _, state in fixture.query.initial_distribution
                    }
                ),
                "same_query": True,
                "query_id": query_id,
                "charged": True,
                "cache_hit": False,
                "oracle_invocation_id": fallback_invocation_id,
                "candidate_work": fallback.composed_candidate_count,
                "elapsed_ns": fallback_ns,
            }
            if fallback is not None
            else None
        ),
        "ground_query_feasible": fallback.feasible if fallback is not None else ground.feasible,
        "known_normative_risk": (
            "V0-RISK-001: first-step failure=383/410"
            if name == "g2048"
            else None
        ),
    }
    policy_graph_document = {
        "query_id": query_id,
        "query_specific": True,
        "abstract_proposal_after_split": proposal_after_document,
        "returned_policy": _policy_document(
            final_policy,
            closure_ids,
            level=("ground" if final_status is CEGARStatus.GROUND_FALLBACK else "abstract"),
            transition_source=(
                fixture.kernel
                if final_status is CEGARStatus.GROUND_FALLBACK
                else models_after.nominal
            ),
        ),
        "charged_fallback_locations": result_document["fallback_location"],
    }
    if refinement.split is None or refinement.split.false_cell is None or refinement.split.true_cell is None:
        raise AssertionError("accepted Phase 0.5 split lacks child cells")
    split_children = []
    for branch, child in (
        ("false", refinement.split.false_cell),
        ("true", refinement.split.true_cell),
    ):
        member_ids = sorted(closure_ids[state] for state in partition_after.members(child))
        split_children.append(
            {
                "branch": branch,
                "cell_id": str(child),
                "member_state_ids": member_ids,
                "member_signature_sha256": canonical_sha256(member_ids),
                "path_predicates": list(tracker.predicate_path(child)),
                "path_signature_sha256": canonical_sha256(
                    tracker.predicate_path(child)
                ),
            }
        )
    accepted_split_document = {
        "status": refinement.status,
        "accepted_candidate_id": candidate_document["candidate_id"],
        "accepted_rank": candidate_document["deterministic_rank"],
        "witness_id": witness_id,
        "witness_separated": candidate_document["witness_separated"],
        "predicate": {
            "predicate_id": refinement.split.predicate_id,
            "feature_name": witness_plan.predicate.feature_name,
            "operator": witness_plan.predicate.operator,
            "rational_threshold": witness_plan.predicate.threshold,
        },
        "parent_cell": str(refinement.split.parent_cell),
        "parent_path_predicates": list(
            tracker.predicate_path(refinement.split.parent_cell)
        ),
        "children": split_children,
        "partition_before_signature_sha256": canonical_sha256(
            partition_before.signature()
        ),
        "partition_after_signature_sha256": canonical_sha256(
            partition_after.signature()
        ),
        "rejected_candidates": [],
        "budgets": budget,
        "counters_before": counters,
        "counters_after": refinement.counters,
        "considered_predicates": refinement.considered_predicates,
    }
    candidates_document = {
        "ranking_order": (
            "decreasing score, more newly-certified pairs, larger failure-width "
            "reduction, smaller rate, predicate ID, witness ID"
        ),
        "candidate_count": 1,
        "rejected_candidate_count": 0,
        "candidates": [candidate_document],
    }

    semantic_result = {
        "status": result_document["status"],
        "evidence": result_document["evidence"],
        "query_id": result_document["query_id"],
        "abstract_audit": result_document["abstract_audit"],
        "fallback": (
            {
                "query_id": fallback_document["query_id"],
                "feasible": fallback_document["feasible"],
                "selection": fallback_document["selection"],
                "frontier": fallback_document["frontier"],
            }
            if fallback_document is not None
            else None
        ),
        "fallback_location": (
            {
                key: value
                for key, value in result_document["fallback_location"].items()
                if key != "elapsed_ns"
            }
            if result_document["fallback_location"] is not None
            else None
        ),
        "ground_query_feasible": result_document["ground_query_feasible"],
        "known_normative_risk": result_document["known_normative_risk"],
        "benchmark_role": result_document["benchmark_role"],
        "claim_eligibility": result_document["claim_eligibility"],
        "raw_regret_upper": result_document["raw_regret_upper"],
        "normalized_regret_upper": result_document["normalized_regret_upper"],
    }
    semantic_policy_graph = {
        "query_id": policy_graph_document["query_id"],
        "query_specific": policy_graph_document["query_specific"],
        "abstract_proposal_after_split": policy_graph_document[
            "abstract_proposal_after_split"
        ],
        "returned_policy": policy_graph_document["returned_policy"],
    }
    semantic_payload = {
        "structural": structural_document,
        "query": query_document,
        "enumeration_status": enumeration.status,
        "enumerated_states": tuple(enumeration_ids.values()),
        "closure_states": tuple(closure_ids.values()),
        "partition_before": partition_before.signature(),
        "partition_after": partition_after.signature(),
        "witness": witness_document,
        "candidate": candidate_document,
        "accepted_split": accepted_split_document,
        "transition_kernel_sha256": enumeration_document["transition_kernel_sha256"],
        "audit_before": before_audit_document,
        "audit_after": after_audit_document,
        "result": semantic_result,
        "policy_graph": semantic_policy_graph,
    }
    semantic_hash = object_id(semantic_payload, "semantic")
    spec_hashes = _spec_hashes()
    reference_hashes = _reference_manifest_hashes()
    source_hash = _source_tree_hash()
    coverage_spec = build_coverage.descriptor()
    build_id = object_id(
        {
            "structural_id": structural_id,
            "coverage": coverage_spec,
            "source": source_hash,
        },
        "build",
    )
    kernel_hash = enumeration_document["transition_kernel_sha256"]
    known_exact_j0_status = "FEASIBLE" if ground.feasible else "INFEASIBLE"
    j0_proof_identity = {
        "structural_id": structural_id,
        "build_id": build_id,
        "kernel_hash": kernel_hash,
        "query_hash": query_id,
    }
    j0_proof_id = object_id(
        {
            "identity": j0_proof_identity,
            "status": known_exact_j0_status,
            "frontier": j0_document["frontier"],
        },
        "j0-proof",
    )
    j0_document["known_exact_j0_status"] = known_exact_j0_status
    j0_document["exact_j0_proof_id"] = j0_proof_id
    j0_document["proof_identity"] = j0_proof_identity
    run_id = object_id(
        {
            "fixture": name,
            "semantic_hash": semantic_hash,
            "source_hash": source_hash,
            "contract_hashes": spec_hashes,
        },
        "run",
    )
    metrics_document = {
        "evidence": "exact_sound",
        "final_status": final_status,
        "finite_horizon_reachable_states": enumeration.state_count,
        "rapm_transition_closure_states": len(closure),
        "quotient_leaves_before": len(partition_before.cell_ids),
        "quotient_leaves_after": len(partition_after.cell_ids),
        "compression_before": Fraction(len(closure), len(partition_before.cell_ids)),
        "compression_after": Fraction(len(closure), len(partition_after.cell_ids)),
        "accepted_splits": refinement.counters.accepted_splits,
        "candidate_evaluations": refinement.counters.candidate_evaluations,
        "rate_bits": refinement.counters.rate_bits,
        "exact_oracle_invocations": 1 + int(fallback is not None),
        "fallback_invocations": int(fallback is not None),
        "j0_feasible": ground.feasible,
        "j0_composed_candidates": ground.composed_candidate_count,
        "nominal_candidates_before": nominal_before.composed_candidate_count,
        "nominal_candidates_after": nominal_after.composed_candidate_count,
        "pre_regret_upper": audit_before.regret_upper,
        "pre_failure_upper": audit_before.lifted_failure_upper,
        "post_regret_upper": audit_after.regret_upper,
        "post_raw_regret_upper": (
            audit_after.regret_upper * fixture.query.normalizer
            if audit_after.regret_upper is not None
            else None
        ),
        "post_normalized_regret_upper": audit_after.regret_upper,
        "normalizer_value": fixture.query.normalizer,
        "normalizer_proof_id": normalizer_proof_id,
        "post_failure_upper": audit_after.lifted_failure_upper,
        "post_aggregate_certified": audit_after.certified,
        "post_pointwise_all_certified": all(
            record["certified"] for record in after_pointwise
        ),
        "post_combined_certified": after_audit_document["certified"],
        "oracle_accounting": {
            "invocation_budget": budget.max_fallback_invocations,
            "invocations": [
                j0_document["oracle_accounting"],
                *(
                    [fallback_document["oracle_accounting"]]
                    if fallback_document is not None
                    else []
                ),
            ],
            "component_candidate_work_total": (
                ground.composed_candidate_count
                + (fallback.composed_candidate_count if fallback is not None else 0)
            ),
            "recorded_invocation_total": 1 + int(fallback is not None),
        },
        "gate": {
            "gate_id": "phase0.5",
            "included_in_gate": True,
            "evidence_required": "exact_sound",
            "exclusion_reason": None,
            "checks": {
                "enumeration_exact_and_complete": (
                    enumeration.status is EnumerationStatus.EXACT and enumeration.complete
                ),
                "mandatory_split_accepted": refinement.status is CEGARStatus.SPLIT_ACCEPTED,
                "terminal_result_allowed": final_status
                in {
                    CEGARStatus.CERTIFIED,
                    CEGARStatus.GROUND_FALLBACK,
                    CEGARStatus.INFEASIBLE_QUERY,
                },
                "certificate_or_charged_fallback": (
                    after_audit_document["certified"]
                    or (
                        fallback_document is not None
                        and result_document["fallback_location"]["charged"]
                    )
                ),
            },
        },
        "metric_records": [
            {
                "name": "compression_after",
                "exact_value": Fraction(len(closure), len(partition_after.cell_ids)),
                "unit": "ground_states_per_cell",
                "evidence_label": "exact_sound",
                "provenance_ids": [run_id, query_id],
                "included_in_gate": True,
                "exclusion_reason": None,
            },
            {
                "name": "post_regret_upper",
                "exact_value": audit_after.regret_upper,
                "unit": "normalized_reward",
                "evidence_label": "exact_sound",
                "provenance_ids": after_audit_document["certificate_dependency_ids"],
                "included_in_gate": True,
                "exclusion_reason": None,
            },
            {
                "name": "post_failure_upper",
                "exact_value": audit_after.lifted_failure_upper,
                "unit": "probability",
                "evidence_label": "exact_sound",
                "provenance_ids": after_audit_document["certificate_dependency_ids"],
                "included_in_gate": True,
                "exclusion_reason": None,
            },
        ],
        "timing_ns": {
            "enumeration": enumeration_ns,
            "rapm_closure": closure_ns,
            "j0": j0_ns,
            "model_before": model_before_ns,
            "nominal_before": nominal_before_ns,
            "audit_before": audit_before_ns,
            "witness_and_candidate": witness_ns,
            "refinement": refinement_ns,
            "model_after": model_after_ns,
            "nominal_after": nominal_after_ns,
            "audit_after": audit_after_ns,
            "fallback": fallback_ns,
            "end_to_end": terminal_ns,
        },
    }
    run_document = {
        "schema_version": "phase05.v1",
        "contract_version": "0.4.0",
        "run_id": run_id,
        "fixture_id": structural_id,
        "structural_key": fixture.structural["structural_key"],
        "benchmark_role": fixture.structural["benchmark_role"],
        "execution_profile": "phase05_vertical_slice",
        "build_id": build_id,
        "build_coverage": coverage_spec,
        "query_id": query_id,
        "known_exact_j0_status": known_exact_j0_status,
        "known_exact_j0_proof_id": j0_proof_id,
        "known_exact_j0_structural_id": structural_id,
        "known_exact_j0_build_id": build_id,
        "known_exact_j0_kernel_hash": kernel_hash,
        "known_exact_j0_query_hash": query_id,
        "phase05_test_override": name == "g2048",
        "claim_eligibility": result_document["claim_eligibility"],
        "domain": name,
        "status": final_status,
        "evidence": "exact_sound",
        "semantic_hash": semantic_hash,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "command": (
            f"PYTHONPATH=src python3 -m acfqp.phase05 --domain {name} "
            "--output artifacts/phase05"
        ),
        "vcs": "none",
        "source_tree_sha256": source_hash,
        "dirty_state_digest": source_hash,
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor() or "unreported",
        "worker_count": 1,
        "dependency_lock": {
            "runtime_dependencies": "stdlib_only",
            "pyproject_sha256": sha256_file(PROJECT_ROOT / "pyproject.toml"),
        },
        "seed_ledger": {
            "artifact": "config/structural.json",
            "seed_ledger_id": seed_ledger_id,
            "seed_ids": {
                purpose: object_id(record, f"seed-{purpose}")
                for purpose, record in seed_ledger.items()
            },
        },
        "random_tapes": {
            "artifact": "config/structural.json",
            "tape_ledger_id": tape_ledger_id,
            "tape_ids": [record["tape_id"] for record in tape_ledger.values()],
        },
        "determinism_environment": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "unset; canonical ordering enforced")
        },
        "spec_hashes": spec_hashes,
        "reference_manifest_hashes": reference_hashes,
    }

    documents = {
        "run.json": run_document,
        "config/structural.json": structural_document,
        "config/query.json": query_document,
        "ground/enumeration.json": enumeration_document,
        "ground/j0_frontier.json": j0_document,
        "rapm/partition_before.json": _partition_document(
            partition_before, closure_ids, ground_state_count=len(closure)
        ),
        "rapm/nominal_before.json": _nominal_document(models_before),
        "rapm/envelope_before.json": envelope_before_document,
        "audit/pre_refinement.json": before_audit_document,
        "refinement/witness.json": witness_document,
        "refinement/candidates.json": candidates_document,
        "refinement/accepted_split.json": accepted_split_document,
        "rapm/partition_after.json": _partition_document(
            partition_after, closure_ids, ground_state_count=len(closure)
        ),
        "rapm/nominal_after.json": _nominal_document(models_after),
        "rapm/envelope_after.json": envelope_after_document,
        "result/policy_graph.json": policy_graph_document,
        "result/certificate_or_fallback.json": result_document,
        "metrics.json": metrics_document,
        "events.jsonl": [
            {"sequence": 1, "event": "enumeration_complete"},
            {"sequence": 2, "event": "j0_complete", "feasible": ground.feasible},
            {"sequence": 3, "event": "coarse_policy_uncertified"},
            {"sequence": 4, "event": "counterexample_selected"},
            {"sequence": 5, "event": "split_accepted"},
            {"sequence": 6, "event": "replanned_and_audited"},
            {"sequence": 7, "event": final_status.value},
        ],
    }
    roles = {
        "run.json": "run_metadata",
        "config/structural.json": "structural_config",
        "config/query.json": "query_config",
        "ground/enumeration.json": "exact_enumeration",
        "ground/j0_frontier.json": "ground_oracle_frontier",
        "rapm/partition_before.json": "coarse_partition",
        "rapm/nominal_before.json": "nominal_model",
        "rapm/envelope_before.json": "sound_envelope",
        "audit/pre_refinement.json": "exact_audit",
        "refinement/witness.json": "counterexample_witness",
        "refinement/candidates.json": "split_candidates",
        "refinement/accepted_split.json": "accepted_split",
        "rapm/partition_after.json": "refined_partition",
        "rapm/nominal_after.json": "nominal_model",
        "rapm/envelope_after.json": "sound_envelope",
        "result/policy_graph.json": "query_policy_graph",
        "result/certificate_or_fallback.json": "terminal_result",
        "metrics.json": "run_metrics",
        "events.jsonl": "event_log",
    }
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        roles=roles,
        required_paths=PHASE05_REQUIRED_PATHS,
    )
    integrity_failures = verify_artifact_bundle(output_dir)
    if integrity_failures:
        raise AssertionError(f"artifact integrity failure: {integrity_failures}")
    return {
        "domain": name,
        "run_id": run_id,
        "semantic_hash": semantic_hash,
        "status": final_status.value,
        "enumerated_states": enumeration.state_count,
        "rapm_states": len(closure),
        "leaves_before": len(partition_before.cell_ids),
        "leaves_after": len(partition_after.cell_ids),
        "manifest_sha256": sha256_file(output_dir / "manifest.json"),
        "bundle_sha256": manifest["bundle_sha256"],
    }


def run_phase05(output: Path, domain: str = "all") -> dict[str, Any]:
    names = ("g2048", "lmb") if domain == "all" else (domain,)
    summaries = [run_fixture(name, output / name) for name in names]
    summary = {
        "schema_version": "phase05.index.v1",
        "runs": summaries,
        "all_required_splits_accepted": all(
            summary["leaves_after"] == summary["leaves_before"] + 1
            for summary in summaries
        ),
    }
    write_json(output / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "phase05",
        help="output directory (default: artifacts/phase05)",
    )
    parser.add_argument(
        "--domain",
        choices=("all", "g2048", "lmb"),
        default="all",
    )
    arguments = parser.parse_args(argv)
    summary = run_phase05(arguments.output.resolve(), arguments.domain)
    print(json.dumps(to_jsonable(summary), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
