"""Executable action-frame-aliasing CEGAR positive control.

This profile deliberately applies the order-sensitive ``canonical:first`` /
``canonical:last`` vocabulary to the frozen safe-chain kernel.  An exact
auditor extracts behavioural counterexamples, a finite current-state geometry
grammar is ranked without rollout/value features, and the ordinary CEGAR
contract refines until a sound constrained certificate is obtained.

The active histogram cells in this tiny fixture are already complete D4
orbits.  Consequently this module is intentionally *not* evidence of unknown
state-quotient or symmetry discovery; it is an action-semantics mismatch
regression with a pre-registered geometry grammar.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Hashable, Iterable

from acfqp.abstraction import Partition, QuotientModels, build_quotient_models
from acfqp.artifacts import (
    ALIASED_CEGAR_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.build_coverage import BuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import (
    D4_ELEMENTS,
    G2048ActionFrameGeometryAdapter,
    orbit,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.enumeration import EnumerationStatus, enumerate_reachable
from acfqp.phase05 import (
    Fixture,
    _audit_document,
    _cell_width,
    _enumeration_document,
    _envelope_document,
    _frontier_document,
    _nominal_document,
    _partition_document,
    _pointwise_audits,
    _policy_document,
    _realization_distance,
    _reference_manifest_hashes,
    _select_nominal_proposal,
    _source_tree_hash,
    _spec_hashes,
    _state_catalog,
)
from acfqp.planning import (
    FiniteHorizonPolicy,
    audit_abstract_policy,
    evaluate_ground_policy,
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
    refine_once,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_KEY = "g2048_select_safe_chain_aliased_partition_v0"
EXECUTION_PROFILE = "aliased_cegar_positive_control"
ABSTRACTION_SOURCE = "deliberately_aliased_boundary_actions"
GRAMMAR_ID = "g2048.action_frame_geometry.v1"
CONTRACT_VERSION = "0.5.0"
STATE_CAP = 50_000
INVARIANT_FAILURE = "ALIASED_CEGAR_INVARIANT_VIOLATION"

GEOMETRY_FEATURE_NAMES = (
    "first_survivor_adjacent_nonmerged_count",
    "first_pair_horizontal",
    "first_survivor_row",
    "first_survivor_column",
    "nonmerged_row",
    "nonmerged_column",
)
GEOMETRY_FEATURE_SEMANTICS = {
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
TARGET_PREDICATE_ID = (
    "first_survivor_adjacent_nonmerged_count|<=|1/2"
)


class AliasedCEGARInvariantViolation(RuntimeError):
    """Raised when the frozen positive-control construction is violated."""

    status = INVARIANT_FAILURE


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Stage:
    index: int
    partition: Partition
    models: QuotientModels
    nominal: Any
    proposal: Any
    audit: Any
    pointwise: tuple[dict[str, Any], ...]
    combined_certified: bool
    lifted_policy: FiniteHorizonPolicy[Any, Any]
    lifted_evaluation: Any


@dataclass(frozen=True)
class Witness:
    cell: Hashable
    action: Hashable
    remaining: int
    left: Any
    right: Any
    observed_gap: Fraction


@dataclass(frozen=True)
class WitnessRecord:
    witness: Witness
    witness_id: str
    document: dict[str, Any]


@dataclass(frozen=True)
class CandidateProbe:
    candidate_id: str
    cell: Hashable
    action: Hashable
    remaining: int
    predicate: Predicate
    canonical_witness_id: str
    supporting_witness_ids: tuple[str, ...]
    canonical_witness: Witness
    split_status: str
    ranked: RankedSplitCandidate | None
    parent_width: Fraction | None
    child_max_width: Fraction | None
    provisional_certified: bool | None
    provisional_failure_upper: Fraction | None
    provisional_regret_upper: Fraction | None
    child_signature: tuple[tuple[str, ...], ...] | None


def _histogram(state: Any) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for rank in state.board:
        if rank:
            counts[rank] = counts.get(rank, 0) + 1
    return tuple(sorted(counts.items()))


def base_cell_id(kernel: Any, state: Any) -> str:
    """Return the frozen ten-cell base encoder key."""

    if kernel.is_terminal(state):
        return "terminal:failure"
    return (
        f"active|empty={state.board.count(0)}|hist={_histogram(state)!r}"
    )


def build_initial_partition(kernel: Any, states: Iterable[Hashable]) -> Partition:
    """Build the profile-owned histogram base partition."""

    return Partition.from_mapping({state: base_cell_id(kernel, state) for state in states})


def geometry_feature_cache(
    adapter: G2048ActionFrameGeometryAdapter,
    kernel: Any,
    states: Iterable[Hashable],
) -> dict[Hashable, dict[str, Fraction]]:
    return {
        state: dict(adapter.features(kernel, state))
        for state in states
    }


def geometry_predicates(
    feature_cache: dict[Hashable, dict[str, Fraction]],
) -> tuple[Predicate, ...]:
    """Materialize the frozen six-atom binary threshold grammar."""

    return tuple(
        Predicate(
            name,
            "<=",
            Fraction(1, 2),
            lambda state, feature_name=name: feature_cache[state][feature_name],
        )
        for name in GEOMETRY_FEATURE_NAMES
    )


def _clone_tracker(tracker: RefinementTracker) -> RefinementTracker:
    return RefinementTracker(
        path_predicates=dict(tracker.path_predicates),
        evaluated_child_signatures={
            cell: set(signatures)
            for cell, signatures in tracker.evaluated_child_signatures.items()
        },
    )


def _failure_width(models: QuotientModels, cell: Hashable, action: Hashable) -> Fraction:
    realizations = models.envelope.realizations(cell, action)
    failures = tuple(realization.failure_probability for realization in realizations)
    return max(failures) - min(failures) if failures else Fraction(0)


def lift_boundary_policy(
    kernel: Any,
    query: Any,
    partition: Partition,
    abstract_policy: FiniteHorizonPolicy[Any, Any],
    adapter: G2048ActionFrameGeometryAdapter,
) -> FiniteHorizonPolicy[Any, Any]:
    """Lift the singleton boundary concretizer on its exact reachable graph."""

    pending = [
        (query.horizon, state)
        for probability, state in query.initial_distribution
        if probability > 0
    ]
    decisions: dict[tuple[int, Hashable], Hashable] = {}
    visited: set[tuple[int, Hashable]] = set()
    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or kernel.is_terminal(state):
            continue
        cell = partition.cell_of(state)
        semantic_action = abstract_policy.action(cell, remaining)
        distribution = tuple(adapter.concretize(kernel, state, semantic_action))
        if len(distribution) != 1 or distribution[0][0] != 1:
            raise AliasedCEGARInvariantViolation(
                "aliased profile requires a singleton deterministic concretizer"
            )
        ground_action = distribution[0][1]
        decisions[marker] = ground_action
        if remaining <= 1:
            continue
        for outcome in kernel.step(state, ground_action):
            if outcome.failure or outcome.terminal or kernel.is_terminal(outcome.next_state):
                continue
            pending.append((remaining - 1, outcome.next_state))
    return FiniteHorizonPolicy.from_mapping(decisions)


def build_stage(
    index: int,
    fixture: Fixture,
    states: tuple[Hashable, ...],
    partition: Partition,
    state_ids: dict[Hashable, str],
) -> Stage:
    models = build_quotient_models(
        fixture.kernel,
        states,
        partition,
        semantic_adapter=fixture.adapter,
    )
    nominal = solve_nominal_pareto(models.nominal, fixture.query)
    proposal = _select_nominal_proposal(nominal)
    audit = audit_abstract_policy(
        fixture.kernel,
        fixture.query,
        models.envelope,
        proposal.policy,
    )
    pointwise_records = _pointwise_audits(
        fixture,
        models,
        proposal.policy,
        state_ids,
    )
    if len(pointwise_records) != len(fixture.query.initial_distribution):
        raise AliasedCEGARInvariantViolation("pointwise audit support is incomplete")
    for record, (_, state) in zip(
        pointwise_records,
        fixture.query.initial_distribution,
    ):
        point_query = QuerySpec.from_state(
            state,
            horizon=fixture.query.horizon,
            reward_weights=fixture.query.reward_weights,
            goal=fixture.query.goal,
            delta=fixture.query.delta,
            normalizer=fixture.query.normalizer,
            normalizer_proof_id=fixture.query.normalizer_proof_id,
        )
        if object_id(point_query, "query") != record["point_query_id"]:
            raise AliasedCEGARInvariantViolation(
                "point-query payload does not resolve its recorded ID"
            )
        record["point_query"] = point_query
    pointwise = tuple(pointwise_records)
    combined = bool(audit.certified and all(item["certified"] for item in pointwise))
    lifted_policy = lift_boundary_policy(
        fixture.kernel,
        fixture.query,
        partition,
        proposal.policy,
        fixture.adapter,
    )
    lifted_evaluation = evaluate_ground_policy(
        fixture.kernel,
        fixture.query,
        lifted_policy,
    )
    return Stage(
        index,
        partition,
        models,
        nominal,
        proposal,
        audit,
        pointwise,
        combined,
        lifted_policy,
        lifted_evaluation,
    )


def enumerate_exact_witnesses(
    stage: Stage,
    weights: dict[str, Fraction],
) -> tuple[Witness, ...]:
    """Enumerate every positive exact gap on the audited reachable policy graph."""

    reachable = {
        (bound.cell, bound.remaining)
        for bound in stage.audit.reachable_bounds
        if bound.remaining > 0
    }
    witnesses: list[Witness] = []
    for cell, remaining in sorted(reachable, key=lambda item: (-item[1], repr(item[0]))):
        try:
            action = stage.proposal.policy.action(cell, remaining)
            realizations = stage.models.envelope.realizations(cell, action)
        except KeyError as error:
            raise AliasedCEGARInvariantViolation(
                "reachable audited pair lacks a policy action or envelope realization"
            ) from error
        for index, left in enumerate(realizations):
            for right in realizations[index + 1 :]:
                gap = _realization_distance(left, right, weights)
                if gap <= 0:
                    continue
                ordered = sorted((left, right), key=lambda item: repr(item.state))
                witnesses.append(
                    Witness(
                        cell,
                        action,
                        remaining,
                        ordered[0],
                        ordered[1],
                        gap,
                    )
                )
    if not witnesses:
        raise AliasedCEGARInvariantViolation(
            "uncertified stage has no positive exact behavioural counterexample"
        )
    return tuple(
        sorted(
            witnesses,
            key=lambda witness: (
                -witness.remaining,
                repr(witness.cell),
                repr(witness.action),
                repr(witness.left.state),
                repr(witness.right.state),
            ),
        )
    )


def materialize_witness_records(
    witnesses: tuple[Witness, ...],
    *,
    iteration: int,
    stage_index: int,
    state_ids: dict[Hashable, str],
    feature_cache: dict[Hashable, dict[str, Fraction]],
    reward_weights: dict[str, Fraction],
) -> tuple[WitnessRecord, ...]:
    """Assign content IDs and complete evidence records to exact witnesses."""

    records: list[WitnessRecord] = []
    for witness in witnesses:
        left_reward = sum(
            (
                reward_weights.get(name, Fraction(0)) * value
                for name, value in witness.left.reward_features
            ),
            Fraction(0),
        )
        right_reward = sum(
            (
                reward_weights.get(name, Fraction(0)) * value
                for name, value in witness.right.reward_features
            ),
            Fraction(0),
        )
        left_successors = dict(witness.left.successor_probabilities)
        right_successors = dict(witness.right.successor_probabilities)
        successor_cells = set(left_successors) | set(right_successors)
        reward_discrepancy = abs(left_reward - right_reward)
        failure_discrepancy = abs(
            witness.left.failure_probability
            - witness.right.failure_probability
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
        discrepancy_channels = tuple(
            name
            for name, value in (
                ("reward", reward_discrepancy),
                ("failure", failure_discrepancy),
                ("abstract_transition_total_variation", transition_discrepancy),
            )
            if value > 0
        )
        if (
            reward_discrepancy
            + failure_discrepancy
            + transition_discrepancy
            != witness.observed_gap
        ):
            raise AliasedCEGARInvariantViolation(
                "serialized witness discrepancy does not reproduce its exact gap"
            )
        payload = {
            "iteration": iteration,
            "derived_from_audit_stage": stage_index,
            "cell": str(witness.cell),
            "semantic_action": witness.action,
            "remaining_horizon": witness.remaining,
            "left_state": state_ids[witness.left.state],
            "right_state": state_ids[witness.right.state],
            "left_state_value": witness.left.state,
            "right_state_value": witness.right.state,
            "left_failure_probability": witness.left.failure_probability,
            "right_failure_probability": witness.right.failure_probability,
            "left_reward_features": witness.left.reward_features,
            "right_reward_features": witness.right.reward_features,
            "left_successor_probabilities": tuple(
                (str(cell), probability)
                for cell, probability in witness.left.successor_probabilities
            ),
            "right_successor_probabilities": tuple(
                (str(cell), probability)
                for cell, probability in witness.right.successor_probabilities
            ),
            "reward_discrepancy": reward_discrepancy,
            "failure_discrepancy": failure_discrepancy,
            "transition_total_variation": transition_discrepancy,
            "discrepancy_channels": discrepancy_channels,
            "left_geometry": {
                name: feature_cache[witness.left.state][name]
                for name in GEOMETRY_FEATURE_NAMES
            },
            "right_geometry": {
                name: feature_cache[witness.right.state][name]
                for name in GEOMETRY_FEATURE_NAMES
            },
            "observed_gap": witness.observed_gap,
            "independent_of_candidate_grammar": True,
        }
        witness_id = object_id(payload, "witness")
        records.append(
            WitnessRecord(
                witness,
                witness_id,
                {"witness_id": witness_id, **payload},
            )
        )
    return tuple(sorted(records, key=lambda record: record.witness_id))


def _joint_candidate_key(probe: CandidateProbe) -> tuple[Any, ...]:
    if probe.ranked is None:
        raise ValueError("only viable candidate probes can be ranked")
    candidate = probe.ranked
    return (
        -candidate.score,
        -candidate.newly_certified_pairs,
        -candidate.failure_width_reduction,
        candidate.rate_cost,
        candidate.predicate.canonical_id,
        probe.canonical_witness_id,
    )


def rank_joint_candidates(
    probes: Iterable[CandidateProbe],
) -> tuple[CandidateProbe, ...]:
    """Apply the frozen witness/predicate joint ordering."""

    return tuple(
        sorted(
            (probe for probe in probes if probe.ranked is not None),
            key=_joint_candidate_key,
        )
    )


def _quality_passes(probe: CandidateProbe) -> bool:
    candidate = probe.ranked
    return bool(
        candidate is not None
        and (
            candidate.newly_certified_pairs > 0
            or (
                probe.parent_width is not None
                and probe.parent_width > 0
                and candidate.audit_width_reduction * 5 >= probe.parent_width
            )
        )
    )


def evaluate_joint_candidates(
    fixture: Fixture,
    states: tuple[Hashable, ...],
    stage: Stage,
    witness_records: tuple[WitnessRecord, ...],
    predicates: tuple[Predicate, ...],
    tracker: RefinementTracker,
    state_ids: dict[Hashable, str],
) -> tuple[tuple[CandidateProbe, ...], tuple[CandidateProbe, ...], int]:
    """Evaluate and deduplicate all separating witness/predicate proposals."""

    weights = normalized_reward_weights(fixture.query)
    rate_cost = Fraction(1 + math.ceil(math.log2(len(GEOMETRY_FEATURE_NAMES))))
    previously_certified = sum(item["certified"] for item in stage.pointwise)
    record_by_id = {record.witness_id: record for record in witness_records}
    grouped: dict[tuple[Hashable, int, Hashable, str], dict[str, Any]] = {}
    separating_cross_products = 0
    for record in witness_records:
        witness = record.witness
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
            proposal = grouped.setdefault(
                key,
                {"predicate": predicate, "witness_ids": []},
            )
            proposal["witness_ids"].append(record.witness_id)

    probes: list[CandidateProbe] = []
    for key, proposal in sorted(
        grouped.items(),
        key=lambda item: (
            -item[0][1],
            repr(item[0][0]),
            repr(item[0][2]),
            item[0][3],
        ),
    ):
        cell, remaining, action, _ = key
        predicate = proposal["predicate"]
        supporting_ids = tuple(sorted(set(proposal["witness_ids"])))
        canonical_witness_id = supporting_ids[0]
        witness = record_by_id[canonical_witness_id].witness
        provisional = attempt_split(
            stage.partition,
            cell,
            predicate,
            _clone_tracker(tracker),
        )
        ranked: RankedSplitCandidate | None = None
        parent_width: Fraction | None = None
        child_max_width: Fraction | None = None
        provisional_certified: bool | None = None
        provisional_failure_upper: Fraction | None = None
        provisional_regret_upper: Fraction | None = None
        child_signature: tuple[tuple[str, ...], ...] | None = None
        if provisional.accepted:
            provisional_stage = build_stage(
                stage.index + 1,
                fixture,
                states,
                provisional.partition,
                state_ids,
            )
            children = (provisional.false_cell, provisional.true_cell)
            parent_width = _cell_width(stage.models, cell, action, weights)
            parent_failure_width = _failure_width(stage.models, cell, action)
            child_max_width = max(
                _cell_width(provisional_stage.models, child, action, weights)
                for child in children
                if child is not None
            )
            child_failure_width = max(
                _failure_width(provisional_stage.models, child, action)
                for child in children
                if child is not None
            )
            ranked = RankedSplitCandidate(
                predicate,
                audit_width_reduction=parent_width - child_max_width,
                newly_certified_pairs=max(
                    0,
                    sum(item["certified"] for item in provisional_stage.pointwise)
                    - previously_certified,
                ),
                failure_width_reduction=(
                    parent_failure_width - child_failure_width
                ),
                rate_cost=rate_cost,
            )
            provisional_certified = provisional_stage.combined_certified
            provisional_failure_upper = provisional_stage.audit.lifted_failure_upper
            provisional_regret_upper = provisional_stage.audit.regret_upper
            child_signature = tuple(
                sorted(
                    tuple(
                        sorted(
                            repr(state)
                            for state in provisional.partition.members(child)
                        )
                    )
                    for child in children
                    if child is not None
                )
            )
        candidate_payload = {
            "stage_index": stage.index,
            "cell": str(cell),
            "remaining_horizon": remaining,
            "semantic_action": action,
            "predicate_id": predicate.canonical_id,
            "child_signature_sha256": (
                canonical_sha256(child_signature)
                if child_signature is not None
                else None
            ),
            "supporting_witness_ids": supporting_ids,
        }
        probes.append(
            CandidateProbe(
                object_id(candidate_payload, "split-candidate"),
                cell,
                action,
                remaining,
                predicate,
                canonical_witness_id,
                supporting_ids,
                witness,
                provisional.status.value,
                ranked,
                parent_width,
                child_max_width,
                provisional_certified,
                provisional_failure_upper,
                provisional_regret_upper,
                child_signature,
            )
        )
    child_signature_keys = [
        (
            probe.cell,
            probe.remaining,
            probe.action,
            probe.child_signature,
        )
        for probe in probes
        if probe.child_signature is not None
    ]
    if len(set(child_signature_keys)) != len(child_signature_keys):
        raise AliasedCEGARInvariantViolation(
            "grammar proposals were not canonicalized to unique child signatures"
        )
    return tuple(probes), rank_joint_candidates(probes), separating_cross_products


def _stage_documents(
    stage: Stage,
    fixture: Fixture,
    state_ids: dict[Hashable, str],
    query_id: str,
    kernel_sha256: str,
) -> dict[str, Any]:
    suffix = f"{stage.index:02d}"
    envelope_path = f"rapm/envelope_{suffix}.json"
    policy_document = _policy_document(
        stage.proposal.policy,
        state_ids,
        level="abstract",
        transition_source=stage.models.nominal,
    )
    if policy_document is None:
        raise AliasedCEGARInvariantViolation("nominal stage proposal is missing")
    partition_document = _partition_document(
        stage.partition,
        state_ids,
        ground_state_count=len(state_ids),
    )
    partition_document["partition_id"] = object_id(
        partition_document,
        "partition",
    )
    nominal_document = _nominal_document(stage.models)
    nominal_document["nominal_model_id"] = object_id(
        nominal_document,
        "nominal-model",
    )
    envelope_document = _envelope_document(stage.models, state_ids, fixture.query)
    envelope_document["envelope_id"] = object_id(
        envelope_document,
        "envelope",
    )
    audit_document = _audit_document(
        stage.audit,
        list(stage.pointwise),
        query_id=query_id,
        policy_document=policy_document,
        envelope_document=envelope_document,
        envelope_artifact=envelope_path,
        kernel_sha256=kernel_sha256,
        audit_stage=f"aliased_cegar_stage_{suffix}",
    )
    audit_document.update(
        {
            "stage_index": stage.index,
            "combined_certified": stage.combined_certified,
            "nominal_feasible": stage.nominal.feasible,
            "nominal_expected_reward": stage.proposal.expected_reward,
            "nominal_failure_probability": stage.proposal.failure_probability,
            "lifted_exact_reward": stage.lifted_evaluation.expected_reward,
            "lifted_exact_failure_probability": (
                stage.lifted_evaluation.failure_probability
            ),
        }
    )
    audit_document["audit_id"] = object_id(audit_document, "audit")
    return {
        f"rapm/partition_{suffix}.json": partition_document,
        f"rapm/nominal_{suffix}.json": nominal_document,
        envelope_path: envelope_document,
        f"audit/audit_{suffix}.json": audit_document,
    }


def _alias_source_diagnostic(kernel: Any, states: tuple[Hashable, ...], adapter: Any) -> dict[str, Any]:
    base = build_initial_partition(kernel, states)
    active_cells = tuple(
        cell
        for cell in base.cell_ids
        if not all(kernel.is_terminal(state) for state in base.members(cell))
    )
    orbit_records = []
    for cell in active_cells:
        members = set(base.members(cell))
        representative = min(members, key=repr)
        d4_members = set(orbit(representative, kernel.size))
        orbit_records.append(
            {
                "cell": str(cell),
                "member_count": len(members),
                "d4_orbit_count": len(d4_members),
                "equals_one_complete_d4_orbit": members == d4_members,
            }
        )

    state_set = set(states)
    mismatch_count = 0
    checked = 0
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
                transformed_action = transform_action(
                    source_action, transform, kernel.size
                )
                if transformed_action != image_action:
                    mismatch_count += 1
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
        "semantic_action_equivariance_mismatches": mismatch_count,
        "mismatch_samples": samples,
        "counterexample_source": "non_equivariant_boundary_action_label_geometry_mismatch",
        "claim_exclusion": (
            "this profile does not discover an unknown state quotient or symmetry"
        ),
    }


def _coverage_inventory_document(
    kernel: Any,
    states: tuple[Hashable, ...],
    state_ids: dict[Hashable, str],
) -> dict[str, Any]:
    """Serialize the complete all-action transition closure used by the build."""

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
            record["transition_id"] = object_id(
                record,
                "coverage-transition",
            )
            transitions.append(record)
    payload = {
        "states": state_records,
        "transitions": transitions,
    }
    return {
        "covered_states": state_records,
        "covered_transitions": transitions,
        "covered_transition_count": len(transitions),
        "coverage_transition_kernel_sha256": canonical_sha256(payload),
    }


def _candidate_documents(
    probes: tuple[CandidateProbe, ...],
    ranked: tuple[CandidateProbe, ...],
    *,
    witness_cross_product_count: int,
    separating_cross_product_count: int,
    selected_candidate_id: str,
    rate_bits_before: Fraction,
    rate_budget_bits: Fraction,
) -> dict[str, Any]:
    ranking = {
        probe.candidate_id: index
        for index, probe in enumerate(ranked, start=1)
    }
    records = []
    for probe in probes:
        candidate = probe.ranked
        predicate_id = probe.predicate.canonical_id
        quality_passed = _quality_passes(probe)
        rate_passed = bool(
            candidate is not None
            and rate_bits_before + candidate.rate_cost <= rate_budget_bits
        )
        records.append(
            {
                "candidate_id": probe.candidate_id,
                "cell": str(probe.cell),
                "semantic_action": probe.action,
                "remaining_horizon": probe.remaining,
                "canonical_witness_id": probe.canonical_witness_id,
                "supporting_witness_ids": probe.supporting_witness_ids,
                "predicate_id": predicate_id,
                "feature_name": probe.predicate.feature_name,
                "operator": probe.predicate.operator,
                "threshold": probe.predicate.threshold,
                "all_supporting_witnesses_separated": True,
                "split_status": probe.split_status,
                "deterministic_rank": ranking.get(probe.candidate_id),
                "audit_width_reduction": (
                    candidate.audit_width_reduction if candidate else None
                ),
                "failure_width_reduction": (
                    candidate.failure_width_reduction if candidate else None
                ),
                "newly_certified_pairs": (
                    candidate.newly_certified_pairs if candidate else None
                ),
                "rate_cost": candidate.rate_cost if candidate else None,
                "score": candidate.score if candidate else None,
                "parent_width": probe.parent_width,
                "child_max_width": probe.child_max_width,
                "quality_threshold": Fraction(1, 5),
                "quality_threshold_passed": quality_passed,
                "rate_budget_passed": rate_passed,
                "structurally_valid": candidate is not None,
                "globally_ranked": candidate is not None,
                "provisional_certified": probe.provisional_certified,
                "provisional_failure_upper": probe.provisional_failure_upper,
                "provisional_regret_upper": probe.provisional_regret_upper,
                "child_signature_sha256": (
                    canonical_sha256(probe.child_signature)
                    if probe.child_signature is not None
                    else None
                ),
                "selected": probe.candidate_id == selected_candidate_id,
                "rejection_reason": (
                    None
                    if probe.candidate_id == selected_candidate_id
                    else (
                        probe.split_status
                        if candidate is None
                        else (
                            "quality_rule_failed"
                            if not quality_passed
                            else (
                                "rate_budget_failed"
                                if not rate_passed
                                else "lower_ranked_viable_candidate"
                            )
                        )
                    )
                ),
            }
        )
    return {
        "grammar_id": GRAMMAR_ID,
        "grammar_feature_count": len(GEOMETRY_FEATURE_NAMES),
        "complete_joint_inventory": True,
        "child_signature_deduplication_verified": True,
        "witness_predicate_cross_product_count": witness_cross_product_count,
        "separating_cross_product_count": separating_cross_product_count,
        "nonseparating_cross_product_count": (
            witness_cross_product_count - separating_cross_product_count
        ),
        "deduplicated_candidate_count": len(records),
        "charged_candidate_evaluation_count": len(records),
        "structurally_valid_candidate_count": len(ranked),
        "quality_passing_candidate_count": sum(
            _quality_passes(probe) for probe in ranked
        ),
        "rate_budget_passing_candidate_count": sum(
            bool(
                probe.ranked is not None
                and rate_bits_before + probe.ranked.rate_cost <= rate_budget_bits
            )
            for probe in ranked
        ),
        "viable_candidate_count": sum(
            bool(
                _quality_passes(probe)
                and probe.ranked is not None
                and rate_bits_before + probe.ranked.rate_cost <= rate_budget_bits
            )
            for probe in ranked
        ),
        "ranking_order": (
            "decreasing score, more newly-certified pairs, larger failure-width "
            "reduction, smaller rate, predicate ID, canonical witness ID"
        ),
        "selected_candidate_id": selected_candidate_id,
        "selected_predicate_id": next(
            probe.predicate.canonical_id
            for probe in probes
            if probe.candidate_id == selected_candidate_id
        ),
        "selected_witness_id": next(
            probe.canonical_witness_id
            for probe in probes
            if probe.candidate_id == selected_candidate_id
        ),
        "candidates": records,
    }


def run_aliased_safe_chain(output_dir: Path) -> dict[str, Any]:
    """Run the frozen two-iteration aliased-action CEGAR profile."""

    started = _utc_now()
    kernel, query = safe_chain_fixture()
    adapter = G2048ActionFrameGeometryAdapter()
    fixture = Fixture(
        "g2048_aliased_safe_chain",
        kernel,
        adapter,
        query,
        {},
        query.normalizer,
    )
    enumeration = enumerate_reachable(
        kernel,
        initial_distribution=query.initial_distribution,
        horizon=query.horizon,
        state_cap=STATE_CAP,
    )
    if enumeration.status is not EnumerationStatus.EXACT or not enumeration.complete:
        raise AliasedCEGARInvariantViolation("finite-horizon enumeration is incomplete")
    coverage = BuildCoverage.from_query(kernel, query, state_cap=STATE_CAP)
    states = coverage.covered_states
    state_ids = _state_catalog(states)
    enumeration_ids = _state_catalog(enumeration.states)

    query_payload = {
        "initial_distribution": query.initial_distribution,
        "initial_distribution_registration": "uniform eight-state D4 orbit of [[1,1],[2,0]]",
        "horizon": query.horizon,
        "reward_weights": query.reward_weights,
        "goal": query.goal,
        "delta": query.delta,
        "normalizer": query.normalizer,
        "normalizer_value": query.normalizer,
        "normalizer_proof_id": query.normalizer_proof_id,
        "normalizer_proof": "each normalized merge reward <=1 and total raw reward <=H",
    }
    query_id = object_id(query_payload, "query")
    query_document = {"query_id": query_id, **query_payload}
    structural_payload = {
        **kernel.structural_key(),
        "structural_identity_scope": "ground_transition_semantics_only",
    }
    structural_id = object_id(structural_payload, "ground-structure")
    structural_document = {"structural_id": structural_id, **structural_payload}
    budget = RefinementBudget.full_v0()
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
        "grammar_features": GEOMETRY_FEATURE_NAMES,
        "grammar_feature_semantics": GEOMETRY_FEATURE_SEMANTICS,
        "grammar_threshold": Fraction(1, 2),
        "per_split_rate_bits": Fraction(
            1 + math.ceil(math.log2(len(GEOMETRY_FEATURE_NAMES)))
        ),
        "budget": budget,
        "stop_rule": "stop immediately when aggregate and every rho0 support point certify",
        "fallback_allowed": True,
        "expected_fallback_for_canonical_run": False,
    }
    profile_id = object_id(profile_payload, "profile")
    profile_hash = canonical_sha256(profile_payload)
    profile_document = {
        "profile_id": profile_id,
        "profile_hash": profile_hash,
        **profile_payload,
    }

    enumeration_document = _enumeration_document(
        enumeration, enumeration_ids, kernel
    )
    enumeration_document.update(
        {
            "covered_state_ids": list(coverage.covered_state_ids),
            "covered_state_count": coverage.covered_state_count,
            "build_coverage": coverage.descriptor(),
            **_coverage_inventory_document(kernel, states, state_ids),
        }
    )
    kernel_sha256 = enumeration_document["transition_kernel_sha256"]
    ground = solve_ground_pareto(kernel, query)
    if ground.selected is None:
        raise AliasedCEGARInvariantViolation("safe-chain J0 unexpectedly infeasible")
    j0_document = _frontier_document(
        ground,
        state_ids,
        "ground_j0",
        query_id=query_id,
        transition_source=kernel,
        oracle_accounting={
            "ordinal": 1,
            "purpose": "J0_constrained_baseline",
            "same_query": True,
            "cache_hit": False,
            "composed_candidate_count": ground.composed_candidate_count,
        },
    )

    partition = build_initial_partition(kernel, states)
    if len(partition.cell_ids) != 10:
        raise AliasedCEGARInvariantViolation(
            f"base partition must have 10 cells, got {len(partition.cell_ids)}"
        )
    feature_cache = geometry_feature_cache(adapter, kernel, states)
    predicates = geometry_predicates(feature_cache)
    tracker = RefinementTracker()
    counters = RefinementCounters(leaves=len(partition.cell_ids))
    weights = normalized_reward_weights(query)
    stages = [build_stage(0, fixture, states, partition, state_ids)]
    iterations: list[dict[str, Any]] = []

    while not stages[-1].combined_certified:
        if len(iterations) >= 2:
            raise AliasedCEGARInvariantViolation(
                "canonical profile did not certify within two exact refinements"
            )
        stage = stages[-1]
        iteration_index = len(iterations) + 1
        witness_records = materialize_witness_records(
            enumerate_exact_witnesses(stage, weights),
            iteration=iteration_index,
            stage_index=stage.index,
            state_ids=state_ids,
            feature_cache=feature_cache,
            reward_weights=weights,
        )
        expected_witness_counts = (35, 19)
        if len(witness_records) != expected_witness_counts[stage.index]:
            raise AliasedCEGARInvariantViolation(
                "complete positive-gap witness inventory changed"
            )
        probes, ranked, separating_cross_products = evaluate_joint_candidates(
            fixture,
            states,
            stage,
            witness_records,
            predicates,
            tracker,
            state_ids,
        )
        expected_candidate_counts = ((120, 16), (64, 10))
        if (
            separating_cross_products,
            len(probes),
        ) != expected_candidate_counts[stage.index]:
            raise AliasedCEGARInvariantViolation(
                "joint separating-candidate inventory changed"
            )
        if not ranked:
            raise AliasedCEGARInvariantViolation(
                "finite geometry grammar has no viable witness separator"
            )
        selected_probe = next(
            (
                probe
                for probe in ranked
                if _quality_passes(probe)
                and probe.ranked is not None
                and counters.rate_bits + probe.ranked.rate_cost
                <= budget.rate_budget_bits
            ),
            None,
        )
        if selected_probe is None:
            raise AliasedCEGARInvariantViolation(
                "joint candidate inventory has no quality- and rate-admissible split"
            )
        witness = selected_probe.canonical_witness
        witness_id = selected_probe.canonical_witness_id
        witness_payload = {
            "iteration": iteration_index,
            "derived_from_audit_stage": stage.index,
            "inventory_complete": True,
            "selection_rule": (
                "canonical supporting witness of the globally highest-ranked "
                "deduplicated witness/predicate proposal"
            ),
            "positive_gap_pair_count": len(witness_records),
            "witness_ids": tuple(record.witness_id for record in witness_records),
            "selected_witness_id": witness_id,
            "witnesses": tuple(record.document for record in witness_records),
        }
        witness_inventory_id = object_id(witness_payload, "witness-inventory")
        witness_document = {
            "witness_inventory_id": witness_inventory_id,
            **witness_payload,
        }
        counters_before = counters
        if (
            counters.candidate_evaluations + len(probes)
            > budget.max_candidate_evaluations
        ):
            raise AliasedCEGARInvariantViolation(
                "complete joint candidate evaluation exceeds the full-V0 budget"
            )
        precharged_counters = RefinementCounters(
            leaves=counters.leaves,
            accepted_splits=counters.accepted_splits,
            rate_bits=counters.rate_bits,
            candidate_evaluations=(
                counters.candidate_evaluations + len(probes) - 1
            ),
            fallback_invocations=counters.fallback_invocations,
        )
        parent_width = _cell_width(stage.models, witness.cell, witness.action, weights)
        refinement = refine_once(
            stage.partition,
            witness.cell,
            (selected_probe.ranked,),
            tracker,
            budget,
            precharged_counters,
            current_audit_width=parent_width,
            witness=(witness.left.state, witness.right.state),
            already_certified=False,
            query_feasible=True,
        )
        if refinement.status is not CEGARStatus.SPLIT_ACCEPTED or refinement.split is None:
            raise AliasedCEGARInvariantViolation(
                f"expected an accepted exact split, got {refinement.status.value}"
            )
        selected_predicate_id = refinement.split.predicate_id
        if selected_predicate_id != TARGET_PREDICATE_ID:
            raise AliasedCEGARInvariantViolation(
                f"candidate ranking selected {selected_predicate_id}, expected {TARGET_PREDICATE_ID}"
            )
        candidates_document = _candidate_documents(
            probes,
            ranked,
            witness_cross_product_count=len(witness_records) * len(predicates),
            separating_cross_product_count=separating_cross_products,
            selected_candidate_id=selected_probe.candidate_id,
            rate_bits_before=counters_before.rate_bits,
            rate_budget_bits=budget.rate_budget_bits,
        )
        candidate_inventory_id = object_id(
            candidates_document,
            "candidate-inventory",
        )
        candidates_document = {
            "candidate_inventory_id": candidate_inventory_id,
            **candidates_document,
        }
        selected_record = next(
            record for record in candidates_document["candidates"] if record["selected"]
        )
        split = refinement.split
        children = []
        for branch, child in (("false", split.false_cell), ("true", split.true_cell)):
            if child is None:
                raise AliasedCEGARInvariantViolation("accepted split lacks a child cell")
            member_ids = sorted(state_ids[state] for state in refinement.partition.members(child))
            children.append(
                {
                    "branch": branch,
                    "cell_id": str(child),
                    "member_state_ids": member_ids,
                    "member_count": len(member_ids),
                    "member_signature_sha256": canonical_sha256(member_ids),
                    "path_predicates": list(tracker.predicate_path(child)),
                }
            )
        split_document = {
            "iteration": iteration_index,
            "status": refinement.status,
            "witness_id": witness_id,
            "witness_inventory_id": witness_inventory_id,
            "candidate_inventory_id": candidate_inventory_id,
            "accepted_candidate_id": selected_record["candidate_id"],
            "accepted_rank": selected_record["deterministic_rank"],
            "predicate_id": selected_predicate_id,
            "parent_cell": str(split.parent_cell),
            "parent_width": parent_width,
            "child_max_width": selected_record["child_max_width"],
            "audit_width_reduction": selected_record["audit_width_reduction"],
            "quality_threshold": Fraction(1, 5),
            "quality_threshold_passed": (
                selected_record["audit_width_reduction"] * 5 >= parent_width
            ),
            "witness_separated": True,
            "children": children,
            "partition_before_signature_sha256": canonical_sha256(
                stage.partition.signature()
            ),
            "partition_after_signature_sha256": canonical_sha256(
                refinement.partition.signature()
            ),
            "budget": budget,
            "counters_before": counters_before,
            "counters_after": refinement.counters,
            "considered_predicates": refinement.considered_predicates,
            "global_considered_candidate_ids": tuple(
                probe.candidate_id
                for probe in ranked
                if _joint_candidate_key(probe)
                <= _joint_candidate_key(selected_probe)
            ),
            "input_stage": stage.index,
            "output_stage": stage.index + 1,
            "input_partition_artifact": f"rapm/partition_{stage.index:02d}.json",
            "input_audit_artifact": f"audit/audit_{stage.index:02d}.json",
            "output_partition_artifact": f"rapm/partition_{stage.index + 1:02d}.json",
            "output_audit_artifact": f"audit/audit_{stage.index + 1:02d}.json",
        }
        counters = refinement.counters
        next_stage = build_stage(
            stage.index + 1,
            fixture,
            states,
            refinement.partition,
            state_ids,
        )
        iterations.append(
            {
                "witness": witness_document,
                "candidates": candidates_document,
                "split": split_document,
            }
        )
        stages.append(next_stage)

    if len(iterations) != 2 or len(stages) != 3:
        raise AliasedCEGARInvariantViolation("canonical run must stop after exactly two splits")
    final = stages[-1]
    if counters.fallback_invocations != 0:
        raise AliasedCEGARInvariantViolation("canonical aliased run must not use fallback")

    expected_stage_values = (
        (Fraction(201, 6400), Fraction(5059, 8000), Fraction(51, 3200), Fraction(19999, 20000), Fraction(99, 3200)),
        (Fraction(3, 64), Fraction(21187, 80000), Fraction(3, 64), Fraction(5099, 10000), Fraction(0)),
        (Fraction(3, 64), Fraction(317, 16000), Fraction(3, 64), Fraction(397, 20000), Fraction(0)),
    )
    for stage, expected in zip(stages, expected_stage_values):
        observed = (
            stage.proposal.expected_reward,
            stage.proposal.failure_probability,
            stage.audit.lifted_reward_lower,
            stage.audit.lifted_failure_upper,
            stage.audit.regret_upper,
        )
        if observed != expected:
            raise AliasedCEGARInvariantViolation(
                f"stage {stage.index} golden mismatch: {observed!r} != {expected!r}"
            )
    if ground.selected.expected_reward != Fraction(3, 64) or ground.selected.failure_probability != Fraction(99, 5000):
        raise AliasedCEGARInvariantViolation("J0 safe-chain golden mismatch")
    if final.lifted_evaluation.failure_probability != Fraction(317, 16000):
        raise AliasedCEGARInvariantViolation("final lifted-risk golden mismatch")
    if not all(
        item["certified"]
        and item["regret_upper"] == 0
        and item["lifted_failure_upper"] == Fraction(397, 20000)
        for item in final.pointwise
    ):
        raise AliasedCEGARInvariantViolation("pointwise initial-support gate failed")

    alias_diagnostic = _alias_source_diagnostic(kernel, states, adapter)
    if not alias_diagnostic["all_active_histogram_cells_equal_complete_d4_orbits"]:
        raise AliasedCEGARInvariantViolation("active histogram/D4 diagnostic changed")
    if alias_diagnostic["semantic_action_equivariance_mismatches"] <= 0:
        raise AliasedCEGARInvariantViolation("boundary action mismatch was not exercised")

    coverage_spec = coverage.descriptor()
    coverage_id = object_id(coverage_spec, "coverage")
    source_hash = _source_tree_hash()
    build_id = object_id(
        {
            "structural_id": structural_id,
            "profile_id": profile_id,
            "coverage": coverage_spec,
            "coverage_transition_kernel_sha256": enumeration_document[
                "coverage_transition_kernel_sha256"
            ],
            "source": source_hash,
        },
        "build",
    )
    j0_identity = {
        "structural_id": structural_id,
        "build_id": build_id,
        "kernel_hash": kernel_sha256,
        "query_hash": query_id,
    }
    j0_proof_id = object_id(
        {
            "identity": j0_identity,
            "status": "FEASIBLE",
            "frontier": j0_document["frontier"],
        },
        "j0-proof",
    )
    j0_document.update(
        {
            "known_exact_j0_status": "FEASIBLE",
            "exact_j0_proof_id": j0_proof_id,
            "proof_identity": j0_identity,
        }
    )

    stage_documents: dict[str, Any] = {}
    for stage in stages:
        stage_documents.update(
            _stage_documents(stage, fixture, state_ids, query_id, kernel_sha256)
        )
    iteration_ids: list[str] = []
    accepted_split_ids: list[str] = []
    for index, iteration in enumerate(iterations, start=1):
        input_suffix = f"{index - 1:02d}"
        output_suffix = f"{index:02d}"
        links = {
            "input_partition_id": stage_documents[
                f"rapm/partition_{input_suffix}.json"
            ]["partition_id"],
            "input_audit_id": stage_documents[f"audit/audit_{input_suffix}.json"][
                "audit_id"
            ],
            "input_nominal_model_id": stage_documents[
                f"rapm/nominal_{input_suffix}.json"
            ]["nominal_model_id"],
            "input_envelope_id": stage_documents[
                f"rapm/envelope_{input_suffix}.json"
            ]["envelope_id"],
            "output_partition_id": stage_documents[
                f"rapm/partition_{output_suffix}.json"
            ]["partition_id"],
            "output_audit_id": stage_documents[f"audit/audit_{output_suffix}.json"][
                "audit_id"
            ],
            "output_nominal_model_id": stage_documents[
                f"rapm/nominal_{output_suffix}.json"
            ]["nominal_model_id"],
            "output_envelope_id": stage_documents[
                f"rapm/envelope_{output_suffix}.json"
            ]["envelope_id"],
        }
        iteration["split"].update(links)
        iteration["split"]["accepted_split_id_scope"] = (
            "this document excluding accepted_split_id and iteration_record"
        )
        accepted_split_id = object_id(iteration["split"], "accepted-split")
        iteration["split"]["accepted_split_id"] = accepted_split_id
        accepted_split_ids.append(accepted_split_id)
        iteration_payload = {
            "index": index,
            **links,
            "witness_inventory_id": iteration["witness"]["witness_inventory_id"],
            "complete_witness_ids": iteration["witness"]["witness_ids"],
            "candidate_inventory_id": iteration["candidates"][
                "candidate_inventory_id"
            ],
            "complete_ranked_candidate_ids": tuple(
                record["candidate_id"]
                for record in sorted(
                    (
                        record
                        for record in iteration["candidates"]["candidates"]
                        if record["deterministic_rank"] is not None
                    ),
                    key=lambda record: record["deterministic_rank"],
                )
            ),
            "accepted_split_id": accepted_split_id,
            "leaves_before": iteration["split"]["counters_before"].leaves,
            "leaves_after": iteration["split"]["counters_after"].leaves,
            "rate_before": iteration["split"]["counters_before"].rate_bits,
            "rate_after": iteration["split"]["counters_after"].rate_bits,
        }
        iteration_id = object_id(iteration_payload, "refinement-iteration")
        iteration_ids.append(iteration_id)
        iteration["split"]["iteration_record"] = {
            "iteration_id": iteration_id,
            **iteration_payload,
        }

    risk_gap = final.lifted_evaluation.failure_probability - ground.selected.failure_probability
    audit_conservatism = final.audit.lifted_failure_upper - final.lifted_evaluation.failure_probability
    final_policy_document = _policy_document(
        final.proposal.policy,
        state_ids,
        level="abstract",
        transition_source=final.models.nominal,
    )
    lifted_policy_document = _policy_document(
        final.lifted_policy,
        state_ids,
        level="lifted_ground",
        transition_source=kernel,
    )
    if final_policy_document is None or lifted_policy_document is None:
        raise AliasedCEGARInvariantViolation("final policy documents are missing")
    policy_graph_payload = {
        "query_id": query_id,
        "profile_id": profile_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "abstract_policy": final_policy_document,
        "lifted_ground_policy": lifted_policy_document,
        "concretizer": "deterministic_singleton_boundary_action",
    }
    policy_graph_document = {
        "policy_graph_id": object_id(policy_graph_payload, "policy-graph"),
        **policy_graph_payload,
    }
    certificate_dependency_ids = (
        j0_proof_id,
        *iteration_ids,
        stage_documents["rapm/partition_02.json"]["partition_id"],
        stage_documents["rapm/envelope_02.json"]["envelope_id"],
        stage_documents["audit/audit_02.json"]["audit_id"],
        *stage_documents["audit/audit_02.json"]["certificate_dependency_ids"],
        policy_graph_document["policy_graph_id"],
    )
    certificate_payload = {
        "status": CEGARStatus.CERTIFIED,
        "profile_key": PROFILE_KEY,
        "profile_id": profile_id,
        "profile_hash": profile_hash,
        "query_id": query_id,
        "abstraction_source": ABSTRACTION_SOURCE,
        "claim_eligibility": "action_frame_aliasing_cegar_only",
        "iteration_ids": tuple(iteration_ids),
        "accepted_split_ids": tuple(accepted_split_ids),
        "policy_graph_id": policy_graph_document["policy_graph_id"],
        "certificate_dependency_ids": certificate_dependency_ids,
        "final_audit_proof_root_ids": tuple(
            stage_documents["audit/audit_02.json"]["certificate_dependency_ids"]
        ),
        "accepted_split_count": counters.accepted_splits,
        "accepted_predicate_ids": [
            iteration["split"]["predicate_id"] for iteration in iterations
        ],
        "stop_reason": "aggregate_and_every_initial_support_point_certified",
        "fallback_invocations": 0,
        "abstract_reward_lower": final.audit.lifted_reward_lower,
        "abstract_failure_upper": final.audit.lifted_failure_upper,
        "risk_tolerance": query.delta,
        "risk_certificate_margin": query.delta - final.audit.lifted_failure_upper,
        "regret_upper": final.audit.regret_upper,
        "lifted_exact_reward": final.lifted_evaluation.expected_reward,
        "lifted_exact_failure_probability": final.lifted_evaluation.failure_probability,
        "ground_optimal_reward": ground.selected.expected_reward,
        "ground_optimal_failure_probability": ground.selected.failure_probability,
        "reward_action_restriction_gap": ground.selected.expected_reward - final.lifted_evaluation.expected_reward,
        "lifted_risk_gap_to_j0": risk_gap,
        "audit_conservatism": audit_conservatism,
        "all_initial_support_points_certified": all(item["certified"] for item in final.pointwise),
        "included_in_positive_claim": True,
        "supported_claim": (
            "exact CEGAR selected and applied a preregistered current-state geometry atom "
            "to repair an action-label/geometry mismatch and obtained a sound constrained certificate"
        ),
        "unsupported_claims": (
            "automatic predicate invention",
            "unknown symmetry discovery",
            "state quotient discovery beyond D4",
            "exact J0 risk or policy preservation",
            "shared cross-domain strategic coordinates",
        ),
    }
    certificate = {
        "certificate_id": object_id(certificate_payload, "certificate"),
        **certificate_payload,
    }

    semantic_payload = {
        "structural_id": structural_id,
        "profile_id": profile_id,
        "query_id": query_id,
        "coverage_state_ids": coverage.covered_state_ids,
        "alias_diagnostic": alias_diagnostic,
        "stage_partitions": [stage.partition.signature() for stage in stages],
        "stage_values": [
            {
                "nominal_reward": stage.proposal.expected_reward,
                "nominal_failure": stage.proposal.failure_probability,
                "audit_lower": stage.audit.lifted_reward_lower,
                "audit_failure_upper": stage.audit.lifted_failure_upper,
                "regret_upper": stage.audit.regret_upper,
                "combined_certified": stage.combined_certified,
            }
            for stage in stages
        ],
        "iterations": iterations,
        "certificate": certificate,
        "policy_signature": final.proposal.policy.signature(),
        "lifted_policy_signature": final.lifted_policy.signature(),
    }
    semantic_hash = object_id(semantic_payload, "semantic")
    run_id = object_id(
        {
            "profile_key": PROFILE_KEY,
            "semantic_hash": semantic_hash,
            "source_hash": source_hash,
            "contract_hashes": _spec_hashes(),
        },
        "run",
    )
    run_document = {
        "schema_version": "aliased_cegar.v1",
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "fixture_id": structural_id,
        "structural_id": structural_id,
        "ground_structural_id": structural_id,
        "ground_structural_key": kernel.fixture_key,
        "structural_key": kernel.fixture_key,
        "profile_id": profile_id,
        "profile_hash": profile_hash,
        "profile_key": PROFILE_KEY,
        "base_encoder_id": base_encoder_id,
        "semantic_adapter_id": semantic_adapter_id,
        "grammar_id": GRAMMAR_ID,
        "execution_profile": EXECUTION_PROFILE,
        "abstraction_source": ABSTRACTION_SOURCE,
        "benchmark_role": "nontrivial_safe_planning_and_quotient_certificate",
        "domain": "g2048_safe_chain",
        "build_id": build_id,
        "build_coverage": coverage_spec,
        "coverage_id": coverage_id,
        "coverage_transition_kernel_sha256": enumeration_document[
            "coverage_transition_kernel_sha256"
        ],
        "query_id": query_id,
        "known_exact_j0_status": "FEASIBLE",
        "known_exact_j0_proof_id": j0_proof_id,
        "known_exact_j0_identity": j0_identity,
        "known_exact_j0_structural_id": structural_id,
        "known_exact_j0_build_id": build_id,
        "known_exact_j0_kernel_hash": kernel_sha256,
        "known_exact_j0_query_hash": query_id,
        "phase05_test_override": False,
        "status": CEGARStatus.CERTIFIED,
        "evidence": "exact_sound",
        "claim_eligibility": "action_frame_aliasing_cegar_only",
        "included_in_positive_claim": True,
        "refinement_enabled": True,
        "fallback_enabled": True,
        "semantic_hash": semantic_hash,
        "source_tree_sha256": source_hash,
        "dirty_state_digest": source_hash,
        "command": "PYTHONPATH=src python3 -m acfqp.aliased_safe_chain --output artifacts/aliased_cegar",
        "vcs": "none",
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor() or "unreported",
        "worker_count": 1,
        "dependency_lock": {
            "runtime_dependencies": "stdlib_only",
            "pyproject_sha256": sha256_file(PROJECT_ROOT / "pyproject.toml"),
        },
        "seed_ledger": {"seed_ids": [], "deterministic": True},
        "random_tapes": {
            "tape_ids": ["tape-none-exact-rational-enumeration"]
        },
        "determinism_environment": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "unset; canonical ordering enforced")
        },
        "spec_hashes": _spec_hashes(),
        "reference_manifest_hashes": _reference_manifest_hashes(),
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
    }
    metrics = {
        "status": CEGARStatus.CERTIFIED,
        "evidence": "exact_sound",
        "finite_horizon_state_time_count": enumeration.state_count,
        "transition_closure_state_count": len(states),
        "base_cell_count": len(stages[0].partition.cell_ids),
        "final_cell_count": len(final.partition.cell_ids),
        "accepted_splits": counters.accepted_splits,
        "candidate_evaluations_until_acceptance": counters.candidate_evaluations,
        "grammar_candidate_materializations": sum(
            iteration["candidates"]["witness_predicate_cross_product_count"]
            for iteration in iterations
        ),
        "separating_candidate_proposals": sum(
            iteration["candidates"]["separating_cross_product_count"]
            for iteration in iterations
        ),
        "deduplicated_candidate_evaluations": sum(
            iteration["candidates"]["deduplicated_candidate_count"]
            for iteration in iterations
        ),
        "witness_inventory_counts": [
            iteration["witness"]["positive_gap_pair_count"]
            for iteration in iterations
        ],
        "incremental_rate_bits": counters.rate_bits,
        "fallback_invocations": counters.fallback_invocations,
        "stage_nominal_failures": [stage.proposal.failure_probability for stage in stages],
        "stage_audit_failure_uppers": [stage.audit.lifted_failure_upper for stage in stages],
        "stage_regret_uppers": [stage.audit.regret_upper for stage in stages],
        "final_lifted_failure": final.lifted_evaluation.failure_probability,
        "ground_optimal_failure": ground.selected.failure_probability,
        "risk_gap_to_j0": risk_gap,
        "audit_conservatism": audit_conservatism,
        "claim_eligibility": "action_frame_aliasing_cegar_only",
        "gate": {
            "included_in_gate": True,
            "checks": {
                "exact_enumeration": enumeration.status is EnumerationStatus.EXACT,
                "closure_192": len(states) == 192,
                "base_cells_10": len(stages[0].partition.cell_ids) == 10,
                "two_exact_splits": counters.accepted_splits == 2,
                "final_cells_12": len(final.partition.cell_ids) == 12,
                "sound_certificate": final.combined_certified,
                "zero_fallback": counters.fallback_invocations == 0,
                "claim_boundary_recorded": not alias_diagnostic["state_aliasing_beyond_d4_present"],
            },
        },
    }

    documents: dict[str, Any] = {
        "run.json": run_document,
        "config/structural.json": structural_document,
        "config/profile.json": profile_document,
        "config/query.json": query_document,
        "ground/enumeration.json": enumeration_document,
        "ground/j0_frontier.json": j0_document,
        "audit/alias_source_diagnostic.json": alias_diagnostic,
        **stage_documents,
        "refinement/iterations/001/witness.json": iterations[0]["witness"],
        "refinement/iterations/001/candidates.json": iterations[0]["candidates"],
        "refinement/iterations/001/accepted_split.json": iterations[0]["split"],
        "refinement/iterations/002/witness.json": iterations[1]["witness"],
        "refinement/iterations/002/candidates.json": iterations[1]["candidates"],
        "refinement/iterations/002/accepted_split.json": iterations[1]["split"],
        "result/policy_graph.json": policy_graph_document,
        "result/cegar_certificate.json": certificate,
        "metrics.json": metrics,
        "events.jsonl": [
            {"sequence": 1, "event": "enumeration_complete"},
            {"sequence": 2, "event": "j0_complete", "status": "FEASIBLE"},
            {"sequence": 3, "event": "coarse_policy_uncertified"},
            {"sequence": 4, "event": "counterexample_selected", "iteration": 1},
            {"sequence": 5, "event": "split_accepted", "iteration": 1},
            {"sequence": 6, "event": "replanned_uncertified", "iteration": 1},
            {"sequence": 7, "event": "counterexample_selected", "iteration": 2},
            {"sequence": 8, "event": "split_accepted", "iteration": 2},
            {"sequence": 9, "event": "CERTIFIED"},
        ],
    }
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        required_paths=ALIASED_CEGAR_REQUIRED_PATHS,
    )
    failures = verify_artifact_bundle(output_dir)
    if failures:
        raise AliasedCEGARInvariantViolation(
            f"aliased artifact integrity failure: {failures!r}"
        )
    return {
        "status": CEGARStatus.CERTIFIED.value,
        "run_id": run_id,
        "semantic_hash": semantic_hash,
        "bundle_sha256": manifest["bundle_sha256"],
        "transition_closure_states": len(states),
        "cells_before": len(stages[0].partition.cell_ids),
        "cells_after": len(final.partition.cell_ids),
        "accepted_splits": counters.accepted_splits,
        "lifted_failure_probability": final.lifted_evaluation.failure_probability,
        "sound_failure_upper": final.audit.lifted_failure_upper,
        "ground_optimal_failure_probability": ground.selected.failure_probability,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "aliased_cegar",
    )
    arguments = parser.parse_args(argv)
    try:
        summary = run_aliased_safe_chain(arguments.output.resolve())
    except AliasedCEGARInvariantViolation as error:
        print(
            json.dumps(
                {"status": error.status, "detail": str(error)},
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
