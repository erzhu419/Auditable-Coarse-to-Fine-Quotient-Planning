#!/usr/bin/env python3
"""Independently verify the frozen aliased safe-chain CEGAR artifact bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Hashable, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.abstraction import Partition, QuotientModels, build_quotient_models  # noqa: E402
from acfqp.artifacts import (  # noqa: E402
    ALIASED_CEGAR_DOCUMENT_CONTRACTS,
    ALIASED_CEGAR_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
)
from acfqp.build_coverage import BuildCoverage  # noqa: E402
from acfqp.core import QuerySpec  # noqa: E402
from acfqp.domains import (  # noqa: E402
    D4_ELEMENTS,
    G2048ActionFrameGeometryAdapter,
    orbit,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.enumeration import EnumerationStatus, enumerate_reachable  # noqa: E402
from acfqp.planning import (  # noqa: E402
    FiniteHorizonPolicy,
    audit_abstract_policy,
    evaluate_ground_policy,
    solve_ground_pareto,
    solve_nominal_pareto,
)
from acfqp.planning.common import reward_weights  # noqa: E402
from acfqp.refinement import (  # noqa: E402
    Predicate,
    RefinementBudget,
    RefinementTracker,
    attempt_split,
)


CONTRACT_VERSION = "0.5.0"
PROFILE_KEY = "g2048_select_safe_chain_aliased_partition_v0"
EXECUTION_PROFILE = "aliased_cegar_positive_control"
ABSTRACTION_SOURCE = "deliberately_aliased_boundary_actions"
GRAMMAR_ID = "g2048.action_frame_geometry.v1"
FEATURE_NAMES = (
    "first_survivor_adjacent_nonmerged_count",
    "first_pair_horizontal",
    "first_survivor_row",
    "first_survivor_column",
    "nonmerged_row",
    "nonmerged_column",
)
FEATURE_SEMANTICS = {
    "coordinate_convention": "zero_based_row_major",
    "action_frame": "first legal primitive action in authoritative kernel order",
    "undefined_frame_convention": (
        "if terminal or FIRST has no unique occupied nonmerged cell, all six atoms are zero"
    ),
    "definitions": {
        "first_survivor_adjacent_nonmerged_count": (
            "1 iff Manhattan(first.survivor, unique_nonmerged_cell)=1, else 0"
        ),
        "first_pair_horizontal": "1 iff row(first.first)=row(first.second), else 0",
        "first_survivor_row": "row(first.survivor)",
        "first_survivor_column": "column(first.survivor)",
        "nonmerged_row": "row(unique_nonmerged_cell)",
        "nonmerged_column": "column(unique_nonmerged_cell)",
    },
}
TARGET_PREDICATE_ID = "first_survivor_adjacent_nonmerged_count|<=|1/2"
EXPECTED_STAGE_VALUES = (
    (
        Fraction(201, 6400),
        Fraction(5059, 8000),
        Fraction(51, 3200),
        Fraction(19999, 20000),
        Fraction(99, 3200),
    ),
    (
        Fraction(3, 64),
        Fraction(21187, 80000),
        Fraction(3, 64),
        Fraction(5099, 10000),
        Fraction(0),
    ),
    (
        Fraction(3, 64),
        Fraction(317, 16000),
        Fraction(3, 64),
        Fraction(397, 20000),
        Fraction(0),
    ),
)
EXPECTED_PARENT_WIDTHS = (Fraction(297, 200), Fraction(297, 400))
EXPECTED_SUPPORTED_CLAIM = (
    "exact CEGAR selected and applied a preregistered current-state geometry atom "
    "to repair an action-label/geometry mismatch and obtained a sound constrained certificate"
)
EXPECTED_UNSUPPORTED_CLAIMS = (
    "automatic predicate invention",
    "unknown symmetry discovery",
    "state quotient discovery beyond D4",
    "exact J0 risk or policy preservation",
    "shared cross-domain strategic coordinates",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def exact(value: Any) -> Fraction:
    if isinstance(value, int) and not isinstance(value, bool):
        return Fraction(value)
    if isinstance(value, dict) and set(value) == {"numerator", "denominator"}:
        return Fraction(value["numerator"], value["denominator"])
    raise ValueError(f"value is not an exact rational: {value!r}")


def _source_tree_hash() -> str:
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for filename in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = ROOT / filename
        if path.is_file():
            paths.append(path)
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    paths = [ROOT / "DECISION_LEDGER.md", *sorted((ROOT / "specs").glob("*.md"))]
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}


def _reference_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for filename in ("download_manifest.json", "repo_clone_manifest.json"):
        path = ROOT / "reference" / filename
        if path.is_file():
            result[f"reference/{filename}"] = sha256_file(path)
    return result


def _state_id(state: Hashable) -> str:
    return object_id(state, "state")


def _histogram(state: Any) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for rank in state.board:
        if rank:
            counts[rank] = counts.get(rank, 0) + 1
    return tuple(sorted(counts.items()))


def _base_cell(kernel: Any, state: Any) -> str:
    if kernel.is_terminal(state):
        return "terminal:failure"
    return f"active|empty={state.board.count(0)}|hist={_histogram(state)!r}"


def _base_partition(kernel: Any, states: Iterable[Hashable]) -> Partition:
    return Partition.from_mapping({state: _base_cell(kernel, state) for state in states})


def _feature_cache(
    adapter: G2048ActionFrameGeometryAdapter,
    kernel: Any,
    states: Iterable[Hashable],
) -> dict[Hashable, dict[str, Fraction]]:
    return {state: dict(adapter.features(kernel, state)) for state in states}


def _predicates(
    cache: dict[Hashable, dict[str, Fraction]],
) -> tuple[Predicate, ...]:
    return tuple(
        Predicate(
            name,
            "<=",
            Fraction(1, 2),
            lambda state, feature_name=name: cache[state][feature_name],
        )
        for name in FEATURE_NAMES
    )


def _select_proposal(result: Any) -> Any:
    if result.selected is not None:
        return result.selected
    return min(
        result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def _lift_policy(
    kernel: Any,
    query: Any,
    partition: Partition,
    abstract_policy: FiniteHorizonPolicy[Any, Any],
    adapter: G2048ActionFrameGeometryAdapter,
) -> FiniteHorizonPolicy[Any, Any]:
    pending = [
        (query.horizon, state)
        for probability, state in query.initial_distribution
        if probability > 0
    ]
    visited: set[tuple[int, Hashable]] = set()
    decisions: dict[tuple[int, Hashable], Hashable] = {}
    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or kernel.is_terminal(state):
            continue
        label = abstract_policy.action(partition.cell_of(state), remaining)
        distribution = tuple(adapter.concretize(kernel, state, label))
        if len(distribution) != 1 or distribution[0][0] != 1:
            raise AssertionError("authoritative boundary concretizer is not singleton")
        action = distribution[0][1]
        decisions[marker] = action
        if remaining <= 1:
            continue
        for outcome in kernel.step(state, action):
            if outcome.failure or outcome.terminal or kernel.is_terminal(outcome.next_state):
                continue
            pending.append((remaining - 1, outcome.next_state))
    return FiniteHorizonPolicy.from_mapping(decisions)


@dataclass(frozen=True)
class StageReplay:
    index: int
    partition: Partition
    models: QuotientModels
    proposal: Any
    nominal_feasible: bool
    audit: Any
    pointwise: tuple[dict[str, Any], ...]
    combined_certified: bool
    lifted_policy: FiniteHorizonPolicy[Any, Any]
    lifted_evaluation: Any


def _pointwise(
    kernel: Any,
    query: Any,
    models: QuotientModels,
    policy: FiniteHorizonPolicy[Any, Any],
) -> tuple[dict[str, Any], ...]:
    records = []
    for probability, state in query.initial_distribution:
        point_query = QuerySpec.from_state(
            state,
            horizon=query.horizon,
            reward_weights=query.reward_weights,
            goal=query.goal,
            delta=query.delta,
            normalizer=query.normalizer,
            normalizer_proof_id=query.normalizer_proof_id,
        )
        audit = audit_abstract_policy(kernel, point_query, models.envelope, policy)
        records.append(
            {
                "point_query_id": object_id(point_query, "query"),
                "point_query": point_query,
                "initial_probability": probability,
                "state": _state_id(state),
                "root_cell": str(models.envelope.partition.cell_of(state)),
                "unrestricted_reward_upper": audit.unrestricted_reward_upper,
                "lifted_reward_lower": audit.lifted_reward_lower,
                "lifted_failure_upper": audit.lifted_failure_upper,
                "regret_upper": audit.regret_upper,
                "certified": audit.certified,
            }
        )
    return tuple(records)


def _build_stage(
    index: int,
    kernel: Any,
    query: Any,
    states: tuple[Hashable, ...],
    partition: Partition,
    adapter: G2048ActionFrameGeometryAdapter,
) -> StageReplay:
    models = build_quotient_models(
        kernel,
        states,
        partition,
        semantic_adapter=adapter,
    )
    nominal = solve_nominal_pareto(models.nominal, query)
    proposal = _select_proposal(nominal)
    audit = audit_abstract_policy(kernel, query, models.envelope, proposal.policy)
    pointwise = _pointwise(kernel, query, models, proposal.policy)
    lifted_policy = _lift_policy(kernel, query, partition, proposal.policy, adapter)
    lifted_evaluation = evaluate_ground_policy(kernel, query, lifted_policy)
    return StageReplay(
        index,
        partition,
        models,
        proposal,
        nominal.feasible,
        audit,
        pointwise,
        bool(audit.certified and all(record["certified"] for record in pointwise)),
        lifted_policy,
        lifted_evaluation,
    )


def _realization_distance(left: Any, right: Any, weights: dict[str, Fraction]) -> Fraction:
    left_reward = left.reward(weights)
    right_reward = right.reward(weights)
    left_successors = dict(left.successor_probabilities)
    right_successors = dict(right.successor_probabilities)
    successors = set(left_successors) | set(right_successors)
    total_variation = sum(
        (
            abs(left_successors.get(cell, 0) - right_successors.get(cell, 0))
            for cell in successors
        ),
        Fraction(0),
    ) / 2
    return (
        abs(left_reward - right_reward)
        + abs(left.failure_probability - right.failure_probability)
        + total_variation
    )


def _cell_width(
    models: QuotientModels,
    cell: Hashable,
    action: Hashable,
    weights: dict[str, Fraction],
) -> Fraction:
    realizations = models.envelope.realizations(cell, action)
    return max(
        (
            _realization_distance(left, right, weights)
            for left in realizations
            for right in realizations
        ),
        default=Fraction(0),
    )


def _failure_width(models: QuotientModels, cell: Hashable, action: Hashable) -> Fraction:
    values = [
        realization.failure_probability
        for realization in models.envelope.realizations(cell, action)
    ]
    return max(values) - min(values) if values else Fraction(0)


@dataclass(frozen=True)
class WitnessReplay:
    witness_id: str
    cell: Hashable
    remaining: int
    action: Hashable
    left: Any
    right: Any
    gap: Fraction
    document: dict[str, Any]

    @property
    def semantic_key(self) -> tuple[Any, ...]:
        return (
            str(self.cell),
            self.remaining,
            str(getattr(self.action, "value", self.action)),
            _state_id(self.left.state),
            _state_id(self.right.state),
            self.gap,
        )


def _witnesses(
    stage: StageReplay,
    weights: dict[str, Fraction],
    feature_cache: dict[Hashable, dict[str, Fraction]],
    *,
    iteration: int,
) -> tuple[WitnessReplay, ...]:
    reachable = {
        (bound.cell, bound.remaining)
        for bound in stage.audit.reachable_bounds
        if bound.remaining > 0
    }
    records: list[WitnessReplay] = []
    for cell, remaining in sorted(reachable, key=lambda item: (-item[1], repr(item[0]))):
        try:
            action = stage.proposal.policy.action(cell, remaining)
            realizations = stage.models.envelope.realizations(cell, action)
        except KeyError:
            continue
        for index, left in enumerate(realizations):
            for right in realizations[index + 1 :]:
                gap = _realization_distance(left, right, weights)
                if gap <= 0:
                    continue
                ordered = sorted((left, right), key=lambda item: repr(item.state))
                left, right = ordered
                left_reward = left.reward(weights)
                right_reward = right.reward(weights)
                left_successors = dict(left.successor_probabilities)
                right_successors = dict(right.successor_probabilities)
                successor_cells = set(left_successors) | set(right_successors)
                reward_discrepancy = abs(left_reward - right_reward)
                failure_discrepancy = abs(
                    left.failure_probability - right.failure_probability
                )
                transition_discrepancy = sum(
                    (
                        abs(
                            left_successors.get(cell, Fraction(0))
                            - right_successors.get(cell, Fraction(0))
                        )
                        for cell in successor_cells
                    ),
                    Fraction(0),
                ) / 2
                if (
                    reward_discrepancy
                    + failure_discrepancy
                    + transition_discrepancy
                    != gap
                ):
                    raise AssertionError("witness discrepancy channels do not sum to gap")
                payload = {
                    "iteration": iteration,
                    "derived_from_audit_stage": stage.index,
                    "cell": str(cell),
                    "semantic_action": action,
                    "remaining_horizon": remaining,
                    "left_state": _state_id(left.state),
                    "right_state": _state_id(right.state),
                    "left_state_value": left.state,
                    "right_state_value": right.state,
                    "left_failure_probability": left.failure_probability,
                    "right_failure_probability": right.failure_probability,
                    "left_reward_features": left.reward_features,
                    "right_reward_features": right.reward_features,
                    "left_successor_probabilities": tuple(
                        (str(successor), probability)
                        for successor, probability in left.successor_probabilities
                    ),
                    "right_successor_probabilities": tuple(
                        (str(successor), probability)
                        for successor, probability in right.successor_probabilities
                    ),
                    "reward_discrepancy": reward_discrepancy,
                    "failure_discrepancy": failure_discrepancy,
                    "transition_total_variation": transition_discrepancy,
                    "discrepancy_channels": tuple(
                        name
                        for name, value in (
                            ("reward", reward_discrepancy),
                            ("failure", failure_discrepancy),
                            (
                                "abstract_transition_total_variation",
                                transition_discrepancy,
                            ),
                        )
                        if value > 0
                    ),
                    "left_geometry": {
                        name: feature_cache[left.state][name]
                        for name in FEATURE_NAMES
                    },
                    "right_geometry": {
                        name: feature_cache[right.state][name]
                        for name in FEATURE_NAMES
                    },
                    "observed_gap": gap,
                    "independent_of_candidate_grammar": True,
                }
                witness_id = object_id(payload, "witness")
                records.append(
                    WitnessReplay(
                        witness_id,
                        cell,
                        remaining,
                        action,
                        left,
                        right,
                        gap,
                        {"witness_id": witness_id, **payload},
                    )
                )
    return tuple(sorted(records, key=lambda item: item.witness_id))


def _clone_tracker(tracker: RefinementTracker) -> RefinementTracker:
    return RefinementTracker(
        path_predicates=dict(tracker.path_predicates),
        evaluated_child_signatures={
            cell: set(signatures)
            for cell, signatures in tracker.evaluated_child_signatures.items()
        },
    )


@dataclass(frozen=True)
class CandidateReplay:
    candidate_id: str
    cell: Hashable
    remaining: int
    action: Hashable
    predicate: Predicate
    child_signature: tuple[tuple[str, ...], ...]
    supporting_witness_ids: tuple[str, ...]
    canonical_witness_id: str
    audit_width_reduction: Fraction
    newly_certified_pairs: int
    failure_width_reduction: Fraction
    rate_cost: Fraction
    child_max_width: Fraction
    provisional_certified: bool
    provisional_failure_upper: Fraction
    provisional_regret_upper: Fraction
    split_status: str

    @property
    def score(self) -> Fraction:
        return self.audit_width_reduction / self.rate_cost

    @property
    def semantic_key(self) -> tuple[Any, ...]:
        return (
            str(self.cell),
            self.remaining,
            str(getattr(self.action, "value", self.action)),
            self.predicate.canonical_id,
            canonical_sha256(self.child_signature),
        )


def _joint_candidates(
    kernel: Any,
    query: Any,
    states: tuple[Hashable, ...],
    adapter: G2048ActionFrameGeometryAdapter,
    stage: StageReplay,
    witnesses: tuple[WitnessReplay, ...],
    predicates: tuple[Predicate, ...],
    tracker: RefinementTracker,
) -> tuple[tuple[CandidateReplay, ...], int]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    separating_cross_products = 0
    for witness in witnesses:
        for predicate in predicates:
            if predicate(witness.left.state) == predicate(witness.right.state):
                continue
            separating_cross_products += 1
            key = (
                witness.cell,
                witness.remaining,
                witness.action,
                predicate.canonical_id,
            )
            record = grouped.setdefault(
                key,
                {
                    "predicate": predicate,
                    "support": set(),
                },
            )
            record["support"].add(witness.witness_id)

    weights = reward_weights(query)
    previously_certified = sum(record["certified"] for record in stage.pointwise)
    rate_cost = Fraction(1 + math.ceil(math.log2(len(FEATURE_NAMES))))
    results: list[CandidateReplay] = []
    for key, record in sorted(
        grouped.items(),
        key=lambda item: (
            -item[0][1],
            repr(item[0][0]),
            repr(item[0][2]),
            item[0][3],
        ),
    ):
        cell, remaining, action, _ = key
        predicate = record["predicate"]
        provisional = attempt_split(
            stage.partition,
            cell,
            predicate,
            _clone_tracker(tracker),
        )
        if not provisional.accepted:
            continue
        children = tuple(
            child
            for child in (provisional.false_cell, provisional.true_cell)
            if child is not None
        )
        child_signature = tuple(
            sorted(
                tuple(
                    sorted(
                        repr(state)
                        for state in provisional.partition.members(child)
                    )
                )
                for child in children
            )
        )
        provisional_stage = _build_stage(
            stage.index + 1,
            kernel,
            query,
            states,
            provisional.partition,
            adapter,
        )
        child_max_width = max(
            _cell_width(provisional_stage.models, child, action, weights)
            for child in children
        )
        child_failure_width = max(
            _failure_width(provisional_stage.models, child, action)
            for child in children
        )
        supporting = tuple(sorted(record["support"]))
        candidate_payload = {
            "stage_index": stage.index,
            "cell": str(cell),
            "remaining_horizon": remaining,
            "semantic_action": action,
            "predicate_id": predicate.canonical_id,
            "child_signature_sha256": canonical_sha256(child_signature),
            "supporting_witness_ids": supporting,
        }
        results.append(
            CandidateReplay(
                object_id(candidate_payload, "split-candidate"),
                cell,
                remaining,
                action,
                predicate,
                child_signature,
                supporting,
                supporting[0],
                _cell_width(stage.models, cell, action, weights) - child_max_width,
                max(
                    0,
                    sum(item["certified"] for item in provisional_stage.pointwise)
                    - previously_certified,
                ),
                _failure_width(stage.models, cell, action) - child_failure_width,
                rate_cost,
                child_max_width,
                provisional_stage.combined_certified,
                provisional_stage.audit.lifted_failure_upper,
                provisional_stage.audit.regret_upper,
                provisional.status.value,
            )
        )
    return tuple(
        sorted(
            results,
            key=lambda candidate: (
                -candidate.score,
                -candidate.newly_certified_pairs,
                -candidate.failure_width_reduction,
                candidate.rate_cost,
                candidate.predicate.canonical_id,
                candidate.canonical_witness_id,
            ),
        )
    ), separating_cross_products


def _partition_document(partition: Partition, state_count: int) -> dict[str, Any]:
    state_ids = {state: _state_id(state) for state in partition.states}
    return {
        "cell_count": len(partition.cell_ids),
        "ground_state_count": state_count,
        "compression_ratio": Fraction(state_count, len(partition.cell_ids)),
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


def _envelope_document(models: QuotientModels, query: Any) -> dict[str, Any]:
    weights = reward_weights(query)
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
                (
                    realization.failure_probability
                    for realization in entry.realizations
                ),
                default=Fraction(0),
            ),
            "failure_upper": max(
                (
                    realization.failure_probability
                    for realization in entry.realizations
                ),
                default=Fraction(0),
            ),
            "realizations": [
                {
                    "state": _state_id(realization.state),
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
        "construction": (
            "enumerate every correlated ground realization; no nominal residual used"
        ),
        "entries": entries,
    }


def _kernel_hash(enumeration: Any) -> str:
    state_ids = {state: _state_id(state) for state in enumeration.states}
    transitions = []
    for transition in enumeration.transitions:
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
    return canonical_sha256({"horizon": enumeration.horizon, "transitions": transitions})


def _coverage_inventory(
    kernel: Any,
    states: tuple[Hashable, ...],
) -> dict[str, Any]:
    state_ids = {state: _state_id(state) for state in states}
    state_records = [
        {
            "id": state_ids[state],
            "state": state,
            "terminal": kernel.is_terminal(state),
        }
        for state in states
    ]
    transitions = []
    for state in states:
        for action in kernel.actions(state):
            record = {
                "state": state_ids[state],
                "action": action,
                "outcomes": tuple(
                    {
                        "probability": outcome.probability,
                        "next_state": state_ids[outcome.next_state],
                        "reward_features": outcome.reward_features,
                        "entered_failure": outcome.failure,
                        "terminal": outcome.terminal,
                    }
                    for outcome in kernel.step(state, action)
                ),
            }
            record["transition_id"] = object_id(record, "coverage-transition")
            transitions.append(record)
    payload = {"states": state_records, "transitions": transitions}
    return {
        "covered_states": state_records,
        "covered_transitions": transitions,
        "covered_transition_count": len(transitions),
        "coverage_transition_kernel_sha256": canonical_sha256(payload),
    }


def _alias_diagnostic(
    kernel: Any,
    states: tuple[Hashable, ...],
    adapter: G2048ActionFrameGeometryAdapter,
) -> dict[str, Any]:
    partition = _base_partition(kernel, states)
    active_cells = tuple(
        cell
        for cell in partition.cell_ids
        if not all(kernel.is_terminal(state) for state in partition.members(cell))
    )
    orbit_records = []
    for cell in active_cells:
        members = set(partition.members(cell))
        representative = min(members, key=repr)
        images = set(orbit(representative, kernel.size))
        orbit_records.append(
            {
                "cell": str(cell),
                "member_count": len(members),
                "d4_orbit_count": len(images),
                "equals_one_complete_d4_orbit": members == images,
            }
        )
    state_set = set(states)
    checked = 0
    mismatches = 0
    samples = []
    for state in states:
        if kernel.is_terminal(state):
            continue
        for transform in D4_ELEMENTS:
            image_state = transform_state(state, transform, kernel.size)
            if image_state not in state_set:
                continue
            for label in adapter.labels(kernel, state):
                if label not in adapter.labels(kernel, image_state):
                    continue
                checked += 1
                source_action = adapter.concretize(kernel, state, label)[0][1]
                image_action = adapter.concretize(kernel, image_state, label)[0][1]
                transformed_action = transform_action(source_action, transform, kernel.size)
                if transformed_action != image_action:
                    mismatches += 1
                    if len(samples) < 8:
                        samples.append(
                            {
                                "state": state,
                                "transform": transform,
                                "label": label,
                                "transformed_source_action": transformed_action,
                                "image_label_action": image_action,
                            }
                        )
    return {
        "diagnostic_only": False,
        "ground_symmetry": "D4 exact automorphism inherited from V0-024",
        "active_histogram_cell_count": len(active_cells),
        "active_cell_orbits": orbit_records,
        "all_active_histogram_cells_equal_complete_d4_orbits": all(
            record["equals_one_complete_d4_orbit"] for record in orbit_records
        ),
        "state_aliasing_beyond_d4_present": False,
        "semantic_action_equivariance_checks": checked,
        "semantic_action_equivariance_mismatches": mismatches,
        "mismatch_samples": samples,
        "counterexample_source": (
            "non_equivariant_boundary_action_label_geometry_mismatch"
        ),
        "claim_exclusion": (
            "this profile does not discover an unknown state quotient or symmetry"
        ),
    }


@dataclass(frozen=True)
class IterationReplay:
    witnesses: tuple[WitnessReplay, ...]
    candidates: tuple[CandidateReplay, ...]
    selected: CandidateReplay
    separating_cross_product_count: int


@dataclass(frozen=True)
class AuthoritativeReplay:
    kernel: Any
    query: Any
    adapter: G2048ActionFrameGeometryAdapter
    enumeration: Any
    coverage: Any
    kernel_hash: str
    coverage_inventory: dict[str, Any]
    stages: tuple[StageReplay, ...]
    iterations: tuple[IterationReplay, ...]
    alias_diagnostic: dict[str, Any]
    ground: Any
    feature_cache: dict[Hashable, dict[str, Fraction]]


@lru_cache(maxsize=1)
def _authoritative_replay() -> AuthoritativeReplay:
    kernel, query = safe_chain_fixture()
    adapter = G2048ActionFrameGeometryAdapter()
    enumeration = enumerate_reachable(
        kernel,
        initial_distribution=query.initial_distribution,
        horizon=query.horizon,
        state_cap=50_000,
    )
    coverage = BuildCoverage.from_query(kernel, query, state_cap=50_000)
    states = coverage.covered_states
    cache = _feature_cache(adapter, kernel, states)
    predicates = _predicates(cache)
    partition = _base_partition(kernel, states)
    tracker = RefinementTracker()
    stages: list[StageReplay] = []
    iterations: list[IterationReplay] = []
    for index in range(3):
        stage = _build_stage(index, kernel, query, states, partition, adapter)
        stages.append(stage)
        if stage.combined_certified:
            break
        witnesses = _witnesses(
            stage,
            reward_weights(query),
            cache,
            iteration=index + 1,
        )
        candidates, separating_cross_products = _joint_candidates(
            kernel,
            query,
            states,
            adapter,
            stage,
            witnesses,
            predicates,
            tracker,
        )
        if not candidates:
            raise AssertionError("authoritative joint candidate inventory has no viable split")
        selected = candidates[0]
        split = attempt_split(partition, selected.cell, selected.predicate, tracker)
        if not split.accepted:
            raise AssertionError("authoritative selected split was rejected")
        iterations.append(
            IterationReplay(
                witnesses,
                candidates,
                selected,
                separating_cross_products,
            )
        )
        partition = split.partition
    if len(stages) != 3 or len(iterations) != 2 or not stages[-1].combined_certified:
        raise AssertionError("authoritative aliased replay did not certify in two splits")
    return AuthoritativeReplay(
        kernel,
        query,
        adapter,
        enumeration,
        coverage,
        _kernel_hash(enumeration),
        _coverage_inventory(kernel, states),
        tuple(stages),
        tuple(iterations),
        _alias_diagnostic(kernel, states, adapter),
        solve_ground_pareto(kernel, query),
        cache,
    )


def _compare_exact(
    document: dict[str, Any],
    field: str,
    expected: Fraction,
    failures: list[str],
    location: str,
) -> None:
    try:
        observed = exact(document.get(field))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        failures.append(f"{location}: {field} is missing or not exact")
        return
    if observed != expected:
        failures.append(
            f"{location}: {field} mismatch ({observed!r} != {expected!r})"
        )


def _partition_mapping(document: dict[str, Any], failures: list[str], location: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for cell in document.get("cells", []):
        cell_id = cell.get("cell_id")
        for state_id in cell.get("members", []):
            if state_id in mapping:
                failures.append(f"{location}: duplicate partition member {state_id!r}")
            mapping[state_id] = cell_id
    return mapping


def _policy_document_replay(
    policy: FiniteHorizonPolicy[Any, Any],
    state_ids: dict[Hashable, str],
    *,
    level: str,
    transition_source: Any,
) -> dict[str, Any]:
    policy_id = object_id({"level": level, "signature": policy.signature()}, "policy")
    node_ids = {
        (decision.remaining, decision.state): object_id(
            {
                "policy_id": policy_id,
                "remaining": decision.remaining,
                "state_or_cell": state_ids.get(decision.state)
                or str(decision.state),
            },
            "policy-node",
        )
        for decision in policy.decisions
    }
    decisions = []
    for decision in policy.decisions:
        child_states: tuple[Hashable, ...] = ()
        if decision.remaining > 1:
            if hasattr(transition_source, "step"):
                child_states = tuple(
                    sorted(
                        {
                            outcome.next_state
                            for outcome in transition_source.step(
                                decision.state,
                                decision.action,
                            )
                            if not outcome.failure
                            and not outcome.terminal
                            and not transition_source.is_terminal(outcome.next_state)
                        },
                        key=repr,
                    )
                )
            else:
                child_states = tuple(
                    successor
                    for successor, probability in transition_source.transition(
                        decision.state,
                        decision.action,
                    ).successor_probabilities
                    if probability > 0
                )
        decisions.append(
            {
                "node_id": node_ids[(decision.remaining, decision.state)],
                "remaining": decision.remaining,
                "state_or_cell": state_ids.get(decision.state)
                or str(decision.state),
                "state_repr": repr(decision.state),
                "action": decision.action,
                "child_node_ids": [
                    node_ids[(decision.remaining - 1, child)]
                    for child in child_states
                    if (decision.remaining - 1, child) in node_ids
                ],
            }
        )
    return {
        "policy_id": policy_id,
        "level": level,
        "selector_class": "deterministic_finite_horizon_markov",
        "decisions": decisions,
        "signature": policy.signature(),
    }


def _verify_policy_document(document: Any, failures: list[str], location: str) -> None:
    if not isinstance(document, dict):
        failures.append(f"{location}: missing policy document")
        return
    if document.get("selector_class") != "deterministic_finite_horizon_markov":
        failures.append(f"{location}: selector is not deterministic finite-horizon Markov")
    decisions = document.get("decisions", [])
    keys = [(item.get("remaining"), item.get("state_or_cell")) for item in decisions]
    if len(keys) != len(set(keys)):
        failures.append(f"{location}: duplicate state/cell-horizon policy decisions")
    node_ids = [item.get("node_id") for item in decisions]
    if None in node_ids or len(node_ids) != len(set(node_ids)):
        failures.append(f"{location}: policy node IDs are missing or duplicated")
    for item in decisions:
        for child in item.get("child_node_ids", []):
            if child not in node_ids:
                failures.append(f"{location}: unresolved policy child {child!r}")


def _verify_iteration_documents(
    bundle: Path,
    replay: AuthoritativeReplay,
    failures: list[str],
) -> None:
    """Independently replay both complete witness/predicate inventories."""

    ranking_order = (
        "decreasing score, more newly-certified pairs, larger failure-width "
        "reduction, smaller rate, predicate ID, canonical witness ID"
    )
    for offset, expected in enumerate(replay.iterations, start=1):
        prefix = bundle / "refinement" / "iterations" / f"{offset:03d}"
        witness_doc = load(prefix / "witness.json")
        candidate_doc = load(prefix / "candidates.json")
        split_doc = load(prefix / "accepted_split.json")
        expected_witness_ids = [item.witness_id for item in expected.witnesses]
        expected_witness_documents = to_jsonable(
            [item.document for item in expected.witnesses]
        )
        if (
            witness_doc.get("inventory_complete") is not True
            or witness_doc.get("iteration") != offset
            or witness_doc.get("derived_from_audit_stage") != offset - 1
            or witness_doc.get("positive_gap_pair_count")
            != len(expected_witness_ids)
            or witness_doc.get("witness_ids") != expected_witness_ids
            or witness_doc.get("witnesses") != expected_witness_documents
            or witness_doc.get("selected_witness_id")
            != expected.selected.canonical_witness_id
        ):
            failures.append(
                f"iteration {offset}: complete authoritative witness inventory mismatch"
            )
        witness_payload = {
            key: value
            for key, value in witness_doc.items()
            if key not in {"witness_inventory_id", "iteration_id"}
        }
        if witness_doc.get("witness_inventory_id") != object_id(
            witness_payload,
            "witness-inventory",
        ):
            failures.append(f"iteration {offset}: witness inventory content ID mismatch")

        rank = {
            candidate.candidate_id: index
            for index, candidate in enumerate(expected.candidates, start=1)
        }
        expected_candidate_records: dict[str, dict[str, Any]] = {}
        for candidate in expected.candidates:
            selected = candidate.candidate_id == expected.selected.candidate_id
            parent_width = _cell_width(
                replay.stages[offset - 1].models,
                candidate.cell,
                candidate.action,
                reward_weights(replay.query),
            )
            quality_passed = bool(
                candidate.newly_certified_pairs > 0
                or (
                    parent_width > 0
                    and candidate.audit_width_reduction * 5 >= parent_width
                )
            )
            expected_candidate_records[candidate.candidate_id] = to_jsonable(
                {
                    "candidate_id": candidate.candidate_id,
                    "cell": str(candidate.cell),
                    "semantic_action": candidate.action,
                    "remaining_horizon": candidate.remaining,
                    "canonical_witness_id": candidate.canonical_witness_id,
                    "supporting_witness_ids": candidate.supporting_witness_ids,
                    "predicate_id": candidate.predicate.canonical_id,
                    "feature_name": candidate.predicate.feature_name,
                    "operator": candidate.predicate.operator,
                    "threshold": candidate.predicate.threshold,
                    "all_supporting_witnesses_separated": True,
                    "split_status": candidate.split_status,
                    "deterministic_rank": rank[candidate.candidate_id],
                    "audit_width_reduction": candidate.audit_width_reduction,
                    "failure_width_reduction": candidate.failure_width_reduction,
                    "newly_certified_pairs": candidate.newly_certified_pairs,
                    "rate_cost": candidate.rate_cost,
                    "score": candidate.score,
                    "parent_width": parent_width,
                    "child_max_width": candidate.child_max_width,
                    "quality_threshold": Fraction(1, 5),
                    "quality_threshold_passed": quality_passed,
                    "rate_budget_passed": True,
                    "structurally_valid": True,
                    "globally_ranked": True,
                    "provisional_certified": candidate.provisional_certified,
                    "provisional_failure_upper": candidate.provisional_failure_upper,
                    "provisional_regret_upper": candidate.provisional_regret_upper,
                    "child_signature_sha256": canonical_sha256(
                        candidate.child_signature
                    ),
                    "selected": selected,
                    "rejection_reason": (
                        None
                        if selected
                        else (
                            "lower_ranked_viable_candidate"
                            if quality_passed
                            else "quality_rule_failed"
                        )
                    ),
                }
            )
        observed_candidate_records = candidate_doc.get("candidates", [])
        observed_by_id = {
            record.get("candidate_id"): record
            for record in observed_candidate_records
            if isinstance(record, dict)
        }
        if (
            len(observed_by_id) != len(observed_candidate_records)
            or observed_by_id != expected_candidate_records
        ):
            failures.append(
                f"iteration {offset}: complete joint candidate inventory mismatch"
            )
        cross_products = len(expected.witnesses) * len(FEATURE_NAMES)
        separating = expected.separating_cross_product_count
        quality_passing = sum(
            record["quality_threshold_passed"]
            for record in expected_candidate_records.values()
        )
        if quality_passing != (3, 2)[offset - 1]:
            failures.append(f"iteration {offset}: quality-pass golden count changed")
        expected_ranking = [item.candidate_id for item in expected.candidates]
        observed_ranking = [
            record.get("candidate_id")
            for record in sorted(
                (
                    record
                    for record in observed_candidate_records
                    if isinstance(record, dict)
                    and isinstance(record.get("deterministic_rank"), int)
                ),
                key=lambda record: record["deterministic_rank"],
            )
        ]
        if (
            candidate_doc.get("complete_joint_inventory") is not True
            or candidate_doc.get("child_signature_deduplication_verified")
            is not True
            or candidate_doc.get("grammar_id") != GRAMMAR_ID
            or candidate_doc.get("grammar_feature_count") != len(FEATURE_NAMES)
            or candidate_doc.get("witness_predicate_cross_product_count")
            != cross_products
            or candidate_doc.get("separating_cross_product_count") != separating
            or candidate_doc.get("nonseparating_cross_product_count")
            != cross_products - separating
            or candidate_doc.get("deduplicated_candidate_count")
            != len(expected.candidates)
            or candidate_doc.get("charged_candidate_evaluation_count")
            != len(expected.candidates)
            or candidate_doc.get("structurally_valid_candidate_count")
            != len(expected.candidates)
            or candidate_doc.get("quality_passing_candidate_count")
            != quality_passing
            or candidate_doc.get("rate_budget_passing_candidate_count")
            != len(expected.candidates)
            or candidate_doc.get("viable_candidate_count") != quality_passing
            or candidate_doc.get("ranking_order") != ranking_order
            or candidate_doc.get("selected_candidate_id")
            != expected.selected.candidate_id
            or candidate_doc.get("selected_predicate_id")
            != expected.selected.predicate.canonical_id
            or candidate_doc.get("selected_witness_id")
            != expected.selected.canonical_witness_id
            or observed_ranking != expected_ranking
        ):
            failures.append(f"iteration {offset}: joint ranking/count mismatch")
        child_signatures = {
            record.get("child_signature_sha256")
            for record in observed_candidate_records
            if isinstance(record, dict)
        }
        if None in child_signatures or len(child_signatures) != len(expected.candidates):
            failures.append(f"iteration {offset}: child signatures are not unique")
        candidate_payload = {
            key: value
            for key, value in candidate_doc.items()
            if key not in {"candidate_inventory_id", "iteration_id"}
        }
        if candidate_doc.get("candidate_inventory_id") != object_id(
            candidate_payload,
            "candidate-inventory",
        ):
            failures.append(f"iteration {offset}: candidate inventory content ID mismatch")

        selected = expected.selected
        before_stage = replay.stages[offset - 1]
        after_stage = replay.stages[offset]
        parent_members = before_stage.partition.members(selected.cell)
        branches = (
            ("false", tuple(state for state in parent_members if not selected.predicate(state))),
            ("true", tuple(state for state in parent_members if selected.predicate(state))),
        )
        expected_children = []
        for branch, members in branches:
            member_ids = sorted(_state_id(state) for state in members)
            child = after_stage.partition.cell_of(members[0])
            if set(after_stage.partition.members(child)) != set(members):
                failures.append(f"iteration {offset}: independent child partition mismatch")
            expected_children.append(
                {
                    "branch": branch,
                    "cell_id": str(child),
                    "member_state_ids": member_ids,
                    "member_count": len(member_ids),
                    "member_signature_sha256": canonical_sha256(member_ids),
                    "path_predicates": [selected.predicate.canonical_id],
                }
            )
        input_partition = load(bundle / f"rapm/partition_{offset - 1:02d}.json")
        input_audit = load(bundle / f"audit/audit_{offset - 1:02d}.json")
        input_nominal = load(bundle / f"rapm/nominal_{offset - 1:02d}.json")
        input_envelope = load(bundle / f"rapm/envelope_{offset - 1:02d}.json")
        output_partition = load(bundle / f"rapm/partition_{offset:02d}.json")
        output_audit = load(bundle / f"audit/audit_{offset:02d}.json")
        output_nominal = load(bundle / f"rapm/nominal_{offset:02d}.json")
        output_envelope = load(bundle / f"rapm/envelope_{offset:02d}.json")
        expected_links = {
            "input_partition_artifact": f"rapm/partition_{offset - 1:02d}.json",
            "input_partition_id": input_partition.get("partition_id"),
            "input_audit_artifact": f"audit/audit_{offset - 1:02d}.json",
            "input_audit_id": input_audit.get("audit_id"),
            "input_nominal_model_id": input_nominal.get("nominal_model_id"),
            "input_envelope_id": input_envelope.get("envelope_id"),
            "output_partition_artifact": f"rapm/partition_{offset:02d}.json",
            "output_partition_id": output_partition.get("partition_id"),
            "output_audit_artifact": f"audit/audit_{offset:02d}.json",
            "output_audit_id": output_audit.get("audit_id"),
            "output_nominal_model_id": output_nominal.get("nominal_model_id"),
            "output_envelope_id": output_envelope.get("envelope_id"),
        }
        candidate_evaluations_before = 0 if offset == 1 else 16
        candidate_evaluations_after = 16 if offset == 1 else 26
        expected_before = {
            "leaves": 9 + offset,
            "accepted_splits": offset - 1,
            "candidate_evaluations": candidate_evaluations_before,
            "fallback_invocations": 0,
            "rate_bits": Fraction(4 * (offset - 1)),
        }
        expected_after = {
            "leaves": 10 + offset,
            "accepted_splits": offset,
            "candidate_evaluations": candidate_evaluations_after,
            "fallback_invocations": 0,
            "rate_bits": Fraction(4 * offset),
        }
        expected_split_fields = {
            "iteration": offset,
            "status": "SPLIT_ACCEPTED",
            "witness_id": selected.canonical_witness_id,
            "witness_inventory_id": witness_doc.get("witness_inventory_id"),
            "candidate_inventory_id": candidate_doc.get("candidate_inventory_id"),
            "accepted_candidate_id": selected.candidate_id,
            "accepted_rank": 1,
            "predicate_id": selected.predicate.canonical_id,
            "parent_cell": str(selected.cell),
            "parent_width": EXPECTED_PARENT_WIDTHS[offset - 1],
            "child_max_width": Fraction(0),
            "audit_width_reduction": EXPECTED_PARENT_WIDTHS[offset - 1],
            "quality_threshold": Fraction(1, 5),
            "quality_threshold_passed": True,
            "witness_separated": True,
            "children": expected_children,
            "partition_before_signature_sha256": canonical_sha256(
                before_stage.partition.signature()
            ),
            "partition_after_signature_sha256": canonical_sha256(
                after_stage.partition.signature()
            ),
            "budget": RefinementBudget.full_v0(),
            "counters_before": expected_before,
            "counters_after": expected_after,
            "considered_predicates": [selected.predicate.canonical_id],
            "global_considered_candidate_ids": [selected.candidate_id],
            "input_stage": offset - 1,
            "output_stage": offset,
            **expected_links,
            "accepted_split_id_scope": (
                "this document excluding accepted_split_id and iteration_record"
            ),
        }
        for field, value in to_jsonable(expected_split_fields).items():
            if split_doc.get(field) != value:
                failures.append(
                    f"iteration {offset}: accepted split/lineage mismatch: {field}"
                )
        accepted_split_payload = {
            key: value
            for key, value in split_doc.items()
            if key not in {"accepted_split_id", "iteration_record"}
        }
        expected_accepted_split_id = object_id(
            accepted_split_payload,
            "accepted-split",
        )
        if split_doc.get("accepted_split_id") != expected_accepted_split_id:
            failures.append(f"iteration {offset}: accepted split content ID mismatch")
        iteration_payload = {
            "index": offset,
            **{key: value for key, value in expected_links.items() if key.endswith("_id")},
            "witness_inventory_id": witness_doc.get("witness_inventory_id"),
            "complete_witness_ids": witness_doc.get("witness_ids"),
            "candidate_inventory_id": candidate_doc.get("candidate_inventory_id"),
            "complete_ranked_candidate_ids": expected_ranking,
            "accepted_split_id": expected_accepted_split_id,
            "leaves_before": expected_before["leaves"],
            "leaves_after": expected_after["leaves"],
            "rate_before": expected_before["rate_bits"],
            "rate_after": expected_after["rate_bits"],
        }
        expected_iteration_id = object_id(
            iteration_payload,
            "refinement-iteration",
        )
        expected_iteration_record = to_jsonable(
            {"iteration_id": expected_iteration_id, **iteration_payload}
        )
        if (
            "iteration_id" in witness_doc
            or "iteration_id" in candidate_doc
            or "iteration_id" in split_doc
            or split_doc.get("iteration_record") != expected_iteration_record
        ):
            failures.append(f"iteration {offset}: refinement iteration ID mismatch")


def verify_aliased_cegar(bundle: Path, *, recompute: bool = False) -> dict[str, Any]:
    bundle = bundle.resolve()
    failures = verify_artifact_bundle(bundle)
    try:
        manifest = load(bundle / "manifest.json")
    except (OSError, json.JSONDecodeError) as error:
        return {
            "status": None,
            "semantic_hash": None,
            "recomputed_semantic_hash": None,
            "failures": failures + [f"cannot load manifest: {error}"],
            "verified": False,
        }
    records = {
        record.get("path"): record
        for record in manifest.get("files", [])
        if isinstance(record, dict)
    }
    if set(manifest.get("required_paths", [])) != set(ALIASED_CEGAR_REQUIRED_PATHS):
        failures.append("manifest does not declare the 29-file aliased CEGAR contract")
    for path, (role, schema) in ALIASED_CEGAR_DOCUMENT_CONTRACTS.items():
        record = records.get(path)
        if not record:
            failures.append(f"required aliased artifact absent: {path}")
        elif record.get("role") != role or record.get("schema") != schema or record.get("required") is not True:
            failures.append(f"aliased role/schema contract mismatch: {path}")

    required_documents = [path for path in ALIASED_CEGAR_REQUIRED_PATHS if path.endswith(".json")]
    try:
        documents = {path: load(bundle / path) for path in required_documents}
        events = [
            json.loads(line)
            for line in (bundle / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot load required aliased documents: {error}")
        return {
            "status": None,
            "semantic_hash": None,
            "recomputed_semantic_hash": None,
            "failures": failures,
            "verified": False,
        }

    run = documents["run.json"]
    structural = documents["config/structural.json"]
    profile = documents["config/profile.json"]
    query_document = documents["config/query.json"]
    enumeration_document = documents["ground/enumeration.json"]
    j0_document = documents["ground/j0_frontier.json"]
    certificate = documents["result/cegar_certificate.json"]
    policy_graph = documents["result/policy_graph.json"]
    metrics = documents["metrics.json"]

    if run.get("contract_version") != CONTRACT_VERSION:
        failures.append("run contract version is not 0.5.0")
    if run.get("schema_version") != "aliased_cegar.v1":
        failures.append("run schema version is not aliased_cegar.v1")
    source_hash = _source_tree_hash()
    if run.get("source_tree_sha256") != source_hash or run.get("dirty_state_digest") != source_hash:
        failures.append("run source-tree parent hash is stale")
    if run.get("spec_hashes") != _spec_hashes():
        failures.append("run spec parent hashes are stale or incomplete")
    expected_reference_hashes = _reference_hashes()
    if len(expected_reference_hashes) == 1:
        failures.append("workspace has only one of the two reference parent manifests")
    if run.get("reference_manifest_hashes") != expected_reference_hashes:
        failures.append("run reference parent hashes are stale or incomplete")

    replay = _authoritative_replay()
    kernel = replay.kernel
    query = replay.query
    structural_payload = {
        **kernel.structural_key(),
        "structural_identity_scope": "ground_transition_semantics_only",
    }
    structural_id = object_id(structural_payload, "ground-structure")
    expected_structural = to_jsonable({"structural_id": structural_id, **structural_payload})
    if structural != expected_structural or "initial_law" in structural:
        failures.append("structural document differs from authoritative ground semantics")

    base_encoder_payload = {
        "encoder": "terminal_failure + active(empty_count,nonzero_rank_histogram)",
        "terminal_failure_singleton": True,
        "incremental_rate_bits": Fraction(0),
    }
    base_encoder_id = object_id(base_encoder_payload, "base-encoder")
    semantic_adapter_payload = {
        "adapter": "boundary-actions.v1:first-last-singleton",
        "labels": ("canonical:first", "canonical:last"),
        "concretizer": "deterministic_singleton",
        "equivariant": False,
    }
    semantic_adapter_id = object_id(
        semantic_adapter_payload,
        "semantic-adapter",
    )
    profile_payload = {
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "abstraction_source": ABSTRACTION_SOURCE,
        "ground_structural_key": kernel.fixture_key,
        "base_encoder_id": base_encoder_id,
        "base_encoder": base_encoder_payload,
        "semantic_adapter_id": semantic_adapter_id,
        "semantic_action_adapter": semantic_adapter_payload,
        "semantic_action_equivariant": False,
        "base_partition_encoder": base_encoder_payload["encoder"],
        "base_partition_incremental_rate_bits": Fraction(0),
        "grammar_id": GRAMMAR_ID,
        "grammar_features": FEATURE_NAMES,
        "grammar_feature_semantics": FEATURE_SEMANTICS,
        "grammar_threshold": Fraction(1, 2),
        "per_split_rate_bits": Fraction(4),
        "budget": RefinementBudget.full_v0(),
        "stop_rule": (
            "stop immediately when aggregate and every rho0 support point certify"
        ),
        "fallback_allowed": True,
        "expected_fallback_for_canonical_run": False,
    }
    profile_id = object_id(profile_payload, "profile")
    profile_hash = canonical_sha256(profile_payload)
    if profile != to_jsonable(
        {
            "profile_id": profile_id,
            "profile_hash": profile_hash,
            **profile_payload,
        }
    ):
        failures.append("profile document differs from the frozen aliased profile")

    query_payload = {
        "initial_distribution": query.initial_distribution,
        "initial_distribution_registration": (
            "uniform eight-state D4 orbit of [[1,1],[2,0]]"
        ),
        "horizon": query.horizon,
        "reward_weights": query.reward_weights,
        "goal": query.goal,
        "delta": query.delta,
        "normalizer": query.normalizer,
        "normalizer_value": query.normalizer,
        "normalizer_proof_id": query.normalizer_proof_id,
        "normalizer_proof": (
            "each normalized merge reward <=1 and total raw reward <=H"
        ),
    }
    query_id = object_id(query_payload, "query")
    if query_document != to_jsonable({"query_id": query_id, **query_payload}):
        failures.append("query document differs from the authoritative safe-chain query")

    coverage = replay.coverage
    coverage_descriptor = to_jsonable(coverage.descriptor())
    if run.get("build_coverage") != coverage_descriptor:
        failures.append("run build coverage differs from authoritative 192-state closure")
    coverage_id = object_id(coverage.descriptor(), "coverage")
    coverage_kernel_hash = replay.coverage_inventory[
        "coverage_transition_kernel_sha256"
    ]
    build_id = object_id(
        {
            "structural_id": structural_id,
            "profile_id": profile_id,
            "coverage": coverage.descriptor(),
            "coverage_transition_kernel_sha256": coverage_kernel_hash,
            "source": source_hash,
        },
        "build",
    )
    if run.get("build_id") != build_id:
        failures.append("run build ID does not bind structure/profile/coverage/source")
    expected_run_context = {
        "fixture_id": structural_id,
        "structural_id": structural_id,
        "structural_key": kernel.fixture_key,
        "ground_structural_id": structural_id,
        "ground_structural_key": kernel.fixture_key,
        "profile_id": profile_id,
        "profile_hash": profile_hash,
        "profile_key": PROFILE_KEY,
        "base_encoder_id": base_encoder_id,
        "semantic_adapter_id": semantic_adapter_id,
        "grammar_id": GRAMMAR_ID,
        "coverage_id": coverage_id,
        "coverage_transition_kernel_sha256": coverage_kernel_hash,
        "execution_profile": EXECUTION_PROFILE,
        "abstraction_source": ABSTRACTION_SOURCE,
        "benchmark_role": "nontrivial_safe_planning_and_quotient_certificate",
        "domain": "g2048_safe_chain",
        "evidence": "exact_sound",
        "claim_eligibility": "action_frame_aliasing_cegar_only",
        "included_in_positive_claim": True,
        "refinement_enabled": True,
        "fallback_enabled": True,
        "phase05_test_override": False,
        "query_id": query_id,
        "status": "CERTIFIED",
        "known_exact_j0_status": "FEASIBLE",
    }
    for field, value in expected_run_context.items():
        if run.get(field) != value:
            failures.append(f"run identity/status mismatch: {field}")

    enumeration = replay.enumeration
    if (
        enumeration.status is not EnumerationStatus.EXACT
        or not enumeration.complete
        or enumeration.state_count != 72
        or tuple(len(layer) for layer in enumeration.layers) != (8, 16, 48)
    ):
        failures.append("authoritative horizon enumeration no longer has 72 nodes")
    expected_enumerated_ids = {_state_id(state) for state in enumeration.states}
    observed_enumerated_ids = {
        item.get("id") for item in enumeration_document.get("states", [])
    }
    if expected_enumerated_ids != observed_enumerated_ids:
        failures.append("enumeration state inventory differs from authoritative H=2 graph")
    if (
        enumeration_document.get("status") != "EXACT"
        or enumeration_document.get("complete") is not True
        or enumeration_document.get("state_count") != 72
        or enumeration_document.get("state_count_by_depth") != [8, 16, 48]
        or enumeration_document.get("covered_state_count") != 192
        or enumeration_document.get("covered_state_ids")
        != list(coverage.covered_state_ids)
        or enumeration_document.get("build_coverage") != coverage_descriptor
        or enumeration_document.get("transition_kernel_sha256") != replay.kernel_hash
    ):
        failures.append("enumeration/coverage/kernel golden mismatch")
    for field, value in to_jsonable(replay.coverage_inventory).items():
        if enumeration_document.get(field) != value:
            failures.append(
                f"complete 192-state transition-closure inventory mismatch: {field}"
            )

    if replay.ground.selected is None:
        failures.append("authoritative J0 unexpectedly infeasible")
    else:
        selected = [item for item in j0_document.get("frontier", []) if item.get("selected")]
        if len(selected) != 1:
            failures.append("J0 artifact does not have one selected frontier point")
        else:
            _compare_exact(selected[0], "expected_reward", Fraction(3, 64), failures, "J0")
            _compare_exact(selected[0], "failure_probability", Fraction(99, 5000), failures, "J0")
    j0_identity = {
        "structural_id": structural_id,
        "build_id": build_id,
        "kernel_hash": replay.kernel_hash,
        "query_hash": query_id,
    }
    expected_j0_proof_id = object_id(
        {
            "identity": j0_identity,
            "status": "FEASIBLE",
            "frontier": j0_document.get("frontier"),
        },
        "j0-proof",
    )
    if (
        j0_document.get("proof_identity") != j0_identity
        or j0_document.get("exact_j0_proof_id") != expected_j0_proof_id
        or run.get("known_exact_j0_identity") != j0_identity
        or run.get("known_exact_j0_proof_id") != expected_j0_proof_id
        or run.get("known_exact_j0_structural_id") != structural_id
        or run.get("known_exact_j0_build_id") != build_id
        or run.get("known_exact_j0_kernel_hash") != replay.kernel_hash
        or run.get("known_exact_j0_query_hash") != query_id
    ):
        failures.append("J0 proof identity/linkage mismatch")

    expected_alias = to_jsonable(replay.alias_diagnostic)
    if documents["audit/alias_source_diagnostic.json"] != expected_alias:
        failures.append("alias-source/D4-orbit/action-mismatch diagnostic mismatch")

    for index, stage in enumerate(replay.stages):
        suffix = f"{index:02d}"
        partition_path = f"rapm/partition_{suffix}.json"
        nominal_path = f"rapm/nominal_{suffix}.json"
        envelope_path = f"rapm/envelope_{suffix}.json"
        audit_path = f"audit/audit_{suffix}.json"
        expected_partition_payload = _partition_document(
            stage.partition,
            len(coverage.covered_states),
        )
        expected_partition = to_jsonable(
            {
                **expected_partition_payload,
                "partition_id": object_id(expected_partition_payload, "partition"),
            }
        )
        if documents[partition_path] != expected_partition:
            failures.append(f"stage {index}: partition/lineage membership mismatch")
        expected_nominal_payload = _nominal_document(stage.models)
        expected_nominal = to_jsonable(
            {
                **expected_nominal_payload,
                "nominal_model_id": object_id(
                    expected_nominal_payload,
                    "nominal-model",
                ),
            }
        )
        if documents[nominal_path] != expected_nominal:
            failures.append(f"stage {index}: nominal model differs from independent rebuild")
        expected_envelope_payload = _envelope_document(stage.models, query)
        expected_envelope = to_jsonable(
            {
                **expected_envelope_payload,
                "envelope_id": object_id(expected_envelope_payload, "envelope"),
            }
        )
        if documents[envelope_path] != expected_envelope:
            failures.append(f"stage {index}: exact envelope differs from independent rebuild")
        audit_doc = documents[audit_path]
        audit_payload = {
            key: value for key, value in audit_doc.items() if key != "audit_id"
        }
        if audit_doc.get("audit_id") != object_id(audit_payload, "audit"):
            failures.append(f"stage {index}: audit content ID mismatch")
        expected_values = EXPECTED_STAGE_VALUES[index]
        for field, expected_value in zip(
            (
                "nominal_expected_reward",
                "nominal_failure_probability",
                "lifted_reward_lower",
                "lifted_failure_upper",
                "regret_upper",
            ),
            expected_values,
        ):
            _compare_exact(audit_doc, field, expected_value, failures, f"stage {index}")
        _compare_exact(
            audit_doc,
            "lifted_exact_reward",
            stage.lifted_evaluation.expected_reward,
            failures,
            f"stage {index}",
        )
        _compare_exact(
            audit_doc,
            "lifted_exact_failure_probability",
            stage.lifted_evaluation.failure_probability,
            failures,
            f"stage {index}",
        )
        if (
            audit_doc.get("stage_index") != index
            or audit_doc.get("combined_certified") != stage.combined_certified
            or audit_doc.get("nominal_feasible") != stage.nominal_feasible
        ):
            failures.append(f"stage {index}: certification/feasibility flags mismatch")
        observed_pointwise = audit_doc.get("pointwise", [])
        if to_jsonable(stage.pointwise) != observed_pointwise:
            failures.append(f"stage {index}: pointwise audit inventory mismatch")

    _verify_iteration_documents(bundle, replay, failures)

    final = replay.stages[-1]
    certificate_exact = {
        "abstract_reward_lower": Fraction(3, 64),
        "abstract_failure_upper": Fraction(397, 20000),
        "risk_tolerance": Fraction(1, 20),
        "risk_certificate_margin": Fraction(603, 20000),
        "regret_upper": Fraction(0),
        "lifted_exact_reward": Fraction(3, 64),
        "lifted_exact_failure_probability": Fraction(317, 16000),
        "ground_optimal_reward": Fraction(3, 64),
        "ground_optimal_failure_probability": Fraction(99, 5000),
        "reward_action_restriction_gap": Fraction(0),
        "lifted_risk_gap_to_j0": Fraction(1, 80000),
        "audit_conservatism": Fraction(3, 80000),
    }
    for field, value in certificate_exact.items():
        _compare_exact(certificate, field, value, failures, "certificate")
    iteration_documents = [
        load(
            bundle
            / "refinement"
            / "iterations"
            / f"{index:03d}"
            / "accepted_split.json"
        )
        for index in (1, 2)
    ]
    expected_iteration_ids = [
        document.get("iteration_record", {}).get("iteration_id")
        for document in iteration_documents
    ]
    expected_split_ids = [
        document.get("accepted_split_id") for document in iteration_documents
    ]
    final_partition_id = documents["rapm/partition_02.json"].get("partition_id")
    final_envelope_id = documents["rapm/envelope_02.json"].get("envelope_id")
    final_audit_id = documents["audit/audit_02.json"].get("audit_id")
    final_audit_proof_roots = documents["audit/audit_02.json"].get(
        "certificate_dependency_ids",
        [],
    )
    policy_graph_id = policy_graph.get("policy_graph_id")
    expected_certificate_dependencies = [
        expected_j0_proof_id,
        *expected_iteration_ids,
        final_partition_id,
        final_envelope_id,
        final_audit_id,
        *final_audit_proof_roots,
        policy_graph_id,
    ]
    certificate_payload = {
        key: value for key, value in certificate.items() if key != "certificate_id"
    }
    if (
        certificate.get("certificate_id")
        != object_id(certificate_payload, "certificate")
        or certificate.get("status") != "CERTIFIED"
        or certificate.get("profile_key") != PROFILE_KEY
        or certificate.get("profile_id") != profile_id
        or certificate.get("profile_hash") != profile_hash
        or certificate.get("query_id") != query_id
        or certificate.get("abstraction_source") != ABSTRACTION_SOURCE
        or certificate.get("claim_eligibility")
        != "action_frame_aliasing_cegar_only"
        or certificate.get("iteration_ids") != expected_iteration_ids
        or certificate.get("accepted_split_ids") != expected_split_ids
        or certificate.get("policy_graph_id") != policy_graph_id
        or certificate.get("certificate_dependency_ids")
        != expected_certificate_dependencies
        or certificate.get("final_audit_proof_root_ids")
        != final_audit_proof_roots
        or certificate.get("accepted_split_count") != 2
        or certificate.get("accepted_predicate_ids") != [TARGET_PREDICATE_ID] * 2
        or certificate.get("fallback_invocations") != 0
        or certificate.get("stop_reason")
        != "aggregate_and_every_initial_support_point_certified"
        or certificate.get("all_initial_support_points_certified") is not True
        or certificate.get("included_in_positive_claim") is not True
        or certificate.get("supported_claim") != EXPECTED_SUPPORTED_CLAIM
        or tuple(certificate.get("unsupported_claims", ())) != EXPECTED_UNSUPPORTED_CLAIMS
    ):
        failures.append("certificate status, linkage, or narrow claim boundary mismatch")
    if not final.combined_certified or len(final.pointwise) != 8 or not all(
        record["certified"] for record in final.pointwise
    ):
        failures.append("authoritative final replay lacks eight pointwise certificates")

    _verify_policy_document(policy_graph.get("abstract_policy"), failures, "abstract policy")
    _verify_policy_document(policy_graph.get("lifted_ground_policy"), failures, "lifted policy")
    state_ids = {
        state: _state_id(state) for state in replay.coverage.covered_states
    }
    expected_abstract_policy = to_jsonable(
        _policy_document_replay(
            final.proposal.policy,
            state_ids,
            level="abstract",
            transition_source=final.models.nominal,
        )
    )
    expected_lifted_policy = to_jsonable(
        _policy_document_replay(
            final.lifted_policy,
            state_ids,
            level="lifted_ground",
            transition_source=kernel,
        )
    )
    policy_graph_payload = {
        "query_id": query_id,
        "profile_id": profile_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "abstract_policy": expected_abstract_policy,
        "lifted_ground_policy": expected_lifted_policy,
        "concretizer": "deterministic_singleton_boundary_action",
    }
    if (
        policy_graph
        != {
            "policy_graph_id": object_id(policy_graph_payload, "policy-graph"),
            **policy_graph_payload,
        }
    ):
        failures.append("final abstract/lifted policy graph differs from independent replay")

    expected_metrics = {
        "status": "CERTIFIED",
        "evidence": "exact_sound",
        "finite_horizon_state_time_count": 72,
        "transition_closure_state_count": 192,
        "base_cell_count": 10,
        "final_cell_count": 12,
        "accepted_splits": 2,
        "candidate_evaluations_until_acceptance": 26,
        "grammar_candidate_materializations": 324,
        "separating_candidate_proposals": 184,
        "deduplicated_candidate_evaluations": 26,
        "witness_inventory_counts": [35, 19],
        "fallback_invocations": 0,
        "claim_eligibility": "action_frame_aliasing_cegar_only",
    }
    for field, value in expected_metrics.items():
        if metrics.get(field) != value:
            failures.append(f"metrics mismatch: {field}")
    expected_metric_series = {
        "stage_nominal_failures": [
            value[1] for value in EXPECTED_STAGE_VALUES
        ],
        "stage_audit_failure_uppers": [
            value[3] for value in EXPECTED_STAGE_VALUES
        ],
        "stage_regret_uppers": [value[4] for value in EXPECTED_STAGE_VALUES],
    }
    for field, values in expected_metric_series.items():
        if metrics.get(field) != to_jsonable(values):
            failures.append(f"metrics mismatch: {field}")
    for field, value in (
        ("incremental_rate_bits", Fraction(8)),
        ("final_lifted_failure", Fraction(317, 16000)),
        ("ground_optimal_failure", Fraction(99, 5000)),
        ("risk_gap_to_j0", Fraction(1, 80000)),
        ("audit_conservatism", Fraction(3, 80000)),
    ):
        _compare_exact(metrics, field, value, failures, "metrics")
    gate = metrics.get("gate", {})
    if gate.get("included_in_gate") is not True or not gate.get("checks") or not all(
        gate["checks"].values()
    ):
        failures.append("aliased positive-control gate is incomplete")

    expected_events = (
        "enumeration_complete",
        "j0_complete",
        "coarse_policy_uncertified",
        "counterexample_selected",
        "split_accepted",
        "replanned_uncertified",
        "counterexample_selected",
        "split_accepted",
        "CERTIFIED",
    )
    if tuple(event.get("event") for event in events) != expected_events or [
        event.get("sequence") for event in events
    ] != list(range(1, 10)):
        failures.append("event chain is not the frozen two-split zero-fallback sequence")
    if any("fallback" in str(event.get("event", "")).lower() for event in events):
        failures.append("fallback event is forbidden in the certified aliased run")
    if any("exact_d4" in json.dumps(document).lower() for document in (run, certificate, metrics)):
        failures.append("aliased bundle carries an exact-D4 result/source label")

    recomputed_hash = None
    if recompute and not failures:
        from acfqp.aliased_safe_chain import run_aliased_safe_chain

        with tempfile.TemporaryDirectory(prefix="acfqp-aliased-verify-") as temporary:
            summary = run_aliased_safe_chain(Path(temporary))
            recomputed_hash = summary["semantic_hash"]
        if recomputed_hash != run.get("semantic_hash"):
            failures.append("fresh-run semantic hash differs from stored bundle")

    return {
        "status": run.get("status"),
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_hash,
        "failures": failures,
        "verified": not failures,
    }


verify_bundle = verify_aliased_cegar
verify_aliased_safe_chain = verify_aliased_cegar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        type=Path,
        nargs="?",
        default=ROOT / "artifacts" / "aliased_cegar",
    )
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="also execute a fresh runner and compare its semantic hash",
    )
    arguments = parser.parse_args(argv)
    report = verify_aliased_cegar(arguments.bundle, recompute=arguments.recompute)
    print(json.dumps(to_jsonable(report), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
