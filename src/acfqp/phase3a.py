"""Phase-3A true-state-alias oracle-quotient construction slice.

This executable is deliberately stronger than the Phase-0.5 action-frame
aliasing control and deliberately narrower than the eventual statistical
Phase-3 Gate.  It constructs one query-independent G2048 decision-oracle
partition and one exact LMB behavioural quotient, evaluates train and held-out
queries on the same RAPMs, and audits compression beyond each kernel's known
automorphism orbits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Hashable, Iterable

from acfqp.abstraction import (
    ExactBehavioralQuotient,
    Partition,
    QuotientModels,
    build_exact_behavioral_quotient,
)
from acfqp.abstraction.oracle import (
    GroundOracleTable,
    OraclePartitionSelection,
    build_ground_oracle_table,
    select_oracle_partition,
)
from acfqp.artifacts import (
    PHASE3A_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import (
    D4_ELEMENTS,
    G2048RelativeSurvivorAdapter,
    G2048State,
    LMBState,
    canonicalize_state,
    orbit,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.domains.g2048 import SAFE_CHAIN_BASE_STATE
from acfqp.domains.matching_buffer import (
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.planning import (
    SemanticKernelView,
    audit_abstract_policy,
    lift_semantic_policy,
    solve_ground_pareto,
    solve_nominal_pareto,
)
from acfqp.symmetry import (
    enumerate_lmb_automorphisms,
    lmb_orbit,
    transform_lmb_action,
    transform_lmb_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_KEY = "phase3a_true_state_alias_oracle_control_v0"
EXECUTION_PROFILE = "phase3a_true_state_alias_oracle_control"
CONTRACT_VERSION = "0.6.0"
STATE_CAP = 50_000
SLICE_PASS = "PHASE3A_SLICE_PASS"
FULL_GATE_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"

LMB_TRAIN_SUPPORT = (
    (11, (1, 2)),
    (13, (2, 1)),
    (19, (1, 2)),
    (21, (2, 1)),
    (25, (1, 2)),
    (35, (2, 1)),
    (41, (2, 1)),
    (49, (2, 1)),
    (7, (2, 1)),
)

G2048_BRIDGE_T_WITNESS = G2048State((0, 2, 2, 2))
G2048_BRIDGE_U_WITNESS = G2048State((0, 2, 4, 2))


class Phase3AInvariantViolation(RuntimeError):
    status = "PHASE3A_INVARIANT_VIOLATION"


@dataclass(frozen=True, slots=True)
class NamedQuery:
    query_key: str
    split: str
    query: QuerySpec[Any]


@dataclass(frozen=True, slots=True)
class QueryEvaluation:
    domain: str
    query_key: str
    split: str
    query_id: str
    ground: Any
    restricted: Any
    nominal_proposal: Any
    audit: Any
    lift: Any


@dataclass(frozen=True, slots=True)
class DomainConstruction:
    domain: str
    kernel: Any
    coverage: SuiteBuildCoverage[Any]
    train_queries: tuple[NamedQuery, ...]
    heldout_queries: tuple[NamedQuery, ...]
    partition: Partition
    models: QuotientModels
    adapter: Any
    construction: Any
    symmetry: dict[str, Any]
    evaluations: tuple[QueryEvaluation, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _source_tree_hash() -> str:
    digest = hashlib.sha256()
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
    for name in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    for path in sorted(set(paths)):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted((PROJECT_ROOT / "specs").glob("*.md"))
    }


def _normalizer_proof(domain: str) -> str:
    return {
        "g2048": "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
        "lmb": "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    }[domain]


def _g2048_query_suite() -> tuple[tuple[NamedQuery, ...], tuple[NamedQuery, ...]]:
    kernel, train_query = safe_chain_fixture()
    rank2_base = G2048State((2, 2, 3, 0))
    rank2_orbit = orbit(rank2_base, kernel.size)
    if len(rank2_orbit) != 8:
        raise Phase3AInvariantViolation("rank-2 held-out support must have eight D4 images")

    def query(
        distribution: tuple[tuple[Fraction, G2048State], ...],
        horizon: int,
    ) -> QuerySpec[G2048State]:
        return QuerySpec(
            distribution,
            horizon,
            (("merge", Fraction(1)),),
            "default",
            Fraction(1, 20),
            Fraction(horizon),
            _normalizer_proof("g2048"),
        )

    rank2_uniform = tuple((Fraction(1, 8), state) for state in rank2_orbit)
    mixed_points = (
        (Fraction(1, 2), SAFE_CHAIN_BASE_STATE),
        (Fraction(1, 2), rank2_base),
    )
    heldout = (
        NamedQuery("g2048.rank2_uniform.h2", "heldout", query(rank2_uniform, 2)),
        NamedQuery("g2048.mixed_points.h2", "heldout", query(mixed_points, 2)),
        NamedQuery(
            "g2048.rank1_point.h2",
            "heldout",
            query(((Fraction(1), SAFE_CHAIN_BASE_STATE),), 2),
        ),
        NamedQuery(
            "g2048.rank1_uniform.h1",
            "heldout",
            query(train_query.initial_distribution, 1),
        ),
    )
    bridge_safe = orbit(SAFE_CHAIN_BASE_STATE, kernel.size)
    bridge_t = orbit(G2048State((2, 2, 2, 0)), kernel.size)
    bridge_u = orbit(G2048State((2, 2, 4, 0)), kernel.size)
    if (len(bridge_safe), len(bridge_t), len(bridge_u)) != (8, 4, 8):
        raise Phase3AInvariantViolation("G2048 bridge orbit sizes changed")
    bridge_distribution = tuple(
        sorted(
            (
                *((Fraction(3, 25), state) for state in bridge_safe),
                *((Fraction(1, 200), state) for state in bridge_t),
                *((Fraction(1, 400), state) for state in bridge_u),
            ),
            key=lambda item: (item[1].board, item[1].status.value),
        )
    )
    if sum((mass for mass, _ in bridge_distribution), Fraction(0)) != 1:
        raise AssertionError("G2048 bridge initial distribution must have unit mass")
    bridge_query = query(bridge_distribution, 1)
    return (
        (
            NamedQuery("g2048.rank1_uniform.h2", "train", train_query),
            NamedQuery(
                "g2048.strict_cross_d4_bridge.h1",
                "train",
                bridge_query,
            ),
        ),
        heldout,
    )


def _lmb_query_suite(kernel: Any) -> tuple[tuple[NamedQuery, ...], tuple[NamedQuery, ...]]:
    states = tuple(
        LMBState(mask, buffer, LMBStatus.ACTIVE)
        for mask, buffer in LMB_TRAIN_SUPPORT
    )
    for state in states:
        if kernel.is_terminal(state) or not kernel.actions(state):
            raise Phase3AInvariantViolation("registered LMB train support is not active")
    rho = tuple((Fraction(1, 9), state) for state in states)

    def query(
        horizon: int,
        weights: tuple[tuple[str, Fraction], ...],
        delta: Fraction,
        normalizer: int,
        normalizer_proof_id: str,
    ) -> QuerySpec[LMBState]:
        return QuerySpec(
            rho,
            horizon,
            weights,
            "default",
            delta,
            Fraction(normalizer),
            normalizer_proof_id,
        )

    train = NamedQuery(
        "lmb.alias9.canonical.h3",
        "train",
        query(
            3,
            (("match", Fraction(1)), ("terminal_clear", Fraction(1))),
            Fraction(1, 20),
            4,
            _normalizer_proof("lmb"),
        ),
    )
    heldout = (
        NamedQuery(
            "lmb.alias9.match_only.h3",
            "heldout",
            query(
                3,
                (("match", Fraction(1)), ("terminal_clear", Fraction(0))),
                Fraction(0),
                2,
                "lmb.match_only.matches_le_n_over_3.v1",
            ),
        ),
        NamedQuery(
            "lmb.alias9.canonical.h2",
            "heldout",
            query(
                2,
                (("match", Fraction(1)), ("terminal_clear", Fraction(1))),
                Fraction(0),
                4,
                _normalizer_proof("lmb"),
            ),
        ),
    )
    return (train,), heldout


def _proposal(result: Any) -> Any:
    if result.selected is not None:
        return result.selected
    if not result.frontier:
        raise Phase3AInvariantViolation("nominal planner returned no proposal")
    return min(
        result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def _evaluate_queries(
    domain: str,
    kernel: Any,
    partition: Partition,
    models: QuotientModels,
    adapter: Any,
    queries: tuple[NamedQuery, ...],
) -> tuple[QueryEvaluation, ...]:
    semantic_kernel = SemanticKernelView(kernel, adapter)
    records: list[QueryEvaluation] = []
    for named in queries:
        ground = solve_ground_pareto(kernel, named.query)
        restricted = solve_ground_pareto(semantic_kernel, named.query)
        nominal_proposal = _proposal(solve_nominal_pareto(models.nominal, named.query))
        audit = audit_abstract_policy(
            kernel,
            named.query,
            models.envelope,
            nominal_proposal.policy,
            regret_tolerance=Fraction(1, 100),
        )
        lift = lift_semantic_policy(
            kernel,
            named.query,
            partition,
            nominal_proposal.policy,
            adapter,
        )
        if ground.selected is None or restricted.selected is None:
            raise Phase3AInvariantViolation(
                f"positive-control query is infeasible: {named.query_key}"
            )
        if not audit.certified:
            raise Phase3AInvariantViolation(
                f"Phase3A query failed exact audit: {named.query_key}"
            )
        records.append(
            QueryEvaluation(
                domain,
                named.query_key,
                named.split,
                object_id(named.query, "query"),
                ground,
                restricted,
                nominal_proposal,
                audit,
                lift,
            )
        )
    return tuple(records)


def _training_policy_reachability(
    kernel: Any,
    query: QuerySpec[Any],
    partition: Partition,
    abstract_policy: Any,
    adapter: Any,
    orbit_key: Any,
) -> tuple[dict[str, Any], Any]:
    """Materialize the physical orbits actually reached by one policy graph."""

    lifted = lift_semantic_policy(
        kernel,
        query,
        partition,
        abstract_policy,
        adapter,
    ).lifted_semantic_policy
    decisions_by_cell: dict[Hashable, set[tuple[Hashable, int]]] = {}
    for decision in lifted.decisions:
        cell = partition.cell_of(decision.state)
        decisions_by_cell.setdefault(cell, set()).add(
            (decision.state, decision.remaining)
        )

    cells: list[dict[str, Any]] = []
    for cell in _ordered(decisions_by_cell):
        state_time_nodes = tuple(
            sorted(decisions_by_cell[cell], key=lambda item: (repr(item[0]), item[1]))
        )
        states = _ordered(state for state, _ in state_time_nodes)
        orbit_representatives = _ordered(orbit_key(state) for state in states)
        distinct_orbit_representatives = _ordered(set(orbit_representatives))
        cells.append(
            {
                "cell": cell,
                "reached_state_time_nodes": tuple(
                    {
                        "state_id": object_id(state, "state"),
                        "remaining": remaining,
                    }
                    for state, remaining in state_time_nodes
                ),
                "reached_state_ids": tuple(
                    sorted({object_id(state, "state") for state in states})
                ),
                "reached_physical_orbit_ids": tuple(
                    sorted(
                        object_id(representative, "physical-orbit")
                        for representative in distinct_orbit_representatives
                    )
                ),
                "reached_state_count": len(set(states)),
                "reached_physical_orbit_count": len(
                    distinct_orbit_representatives
                ),
                "cross_automorphism": len(distinct_orbit_representatives) > 1,
            }
        )
    return (
        {
            "query_id": object_id(query, "query"),
            "abstract_policy_signature": abstract_policy.signature(),
            "lifted_semantic_policy_signature": lifted.signature(),
            "cells": tuple(cells),
        },
        lifted,
    )


def _g2048_symmetry(
    kernel: Any,
    coverage: SuiteBuildCoverage[Any],
    selection: OraclePartitionSelection,
    adapter: Any,
) -> dict[str, Any]:
    active = tuple(state for state in coverage.covered_states if not kernel.is_terminal(state))
    orbit_key = lambda state: canonicalize_state(state, kernel.size)[0]
    total_orbit_count = len({orbit_key(state) for state in coverage.covered_states})
    active_cells = tuple(
        cell
        for cell in selection.partition.cell_ids
        if not all(kernel.is_terminal(state) for state in selection.partition.members(cell))
    )
    mixed = tuple(
        cell
        for cell in active_cells
        if len({orbit_key(state) for state in selection.partition.members(cell)}) > 1
    )
    training_reachability = tuple(
        _training_policy_reachability(
            kernel,
            evaluation.query,
            selection.partition,
            evaluation.abstract_policy,
            adapter,
            orbit_key,
        )[0]
        for evaluation in selection.training_evaluations
    )
    reachable_mixed = _ordered(
        {
            cell_record["cell"]
            for policy_record in training_reachability
            for cell_record in policy_record["cells"]
            if cell_record["cross_automorphism"]
        }
    )
    if set(reachable_mixed) != set(selection.reachable_mixed_cells):
        raise Phase3AInvariantViolation(
            "G2048 selected reachability summary differs from policy-graph audit"
        )
    ground_pairs = tuple(
        (state, action)
        for state in active
        for action in kernel.actions(state)
    )
    state_action_orbits = {
        min(
            (
                transform_state(state, element, kernel.size),
                transform_action(action, element, kernel.size),
            )
            for element in D4_ELEMENTS
        )
        for state, action in ground_pairs
    }
    witness = (G2048_BRIDGE_T_WITNESS, G2048_BRIDGE_U_WITNESS)
    witness_cell = selection.partition.cell_of(witness[0])
    witness_same_cell = witness_cell == selection.partition.cell_of(witness[1])
    witness_same_orbit = orbit_key(witness[0]) == orbit_key(witness[1])
    bridge_evaluation = next(
        evaluation
        for evaluation in selection.training_evaluations
        if evaluation.query.horizon == 1
        and witness[0]
        in {state for mass, state in evaluation.query.initial_distribution if mass > 0}
        and witness[1]
        in {state for mass, state in evaluation.query.initial_distribution if mass > 0}
    )
    bridge_lift = lift_semantic_policy(
        kernel,
        bridge_evaluation.query,
        selection.partition,
        bridge_evaluation.abstract_policy,
        adapter,
    ).lifted_semantic_policy
    reachable_witnesses = {decision.state for decision in bridge_lift.decisions}
    witness_both_policy_reachable = all(
        state in reachable_witnesses for state in witness
    )
    witness_actions = tuple(
        bridge_lift.action(state, bridge_evaluation.query.horizon)
        for state in witness
    )
    witness_same_semantic_action = witness_actions[0] == witness_actions[1]
    if (
        not witness_same_cell
        or witness_same_orbit
        or not witness_both_policy_reachable
        or not witness_same_semantic_action
        or witness_cell not in reachable_mixed
    ):
        raise Phase3AInvariantViolation(
            "G2048 bridge witness must be jointly policy-reachable in one cross-D4 cell"
        )
    return {
        "known_automorphism_group": "D4",
        "automorphism_count": 8,
        "covered_ground_states": len(coverage.covered_states),
        "known_symmetry_total_state_orbits": total_orbit_count,
        "candidate_total_cells": len(selection.partition.cell_ids),
        "symmetry_normalized_total_compression": Fraction(
            total_orbit_count, len(selection.partition.cell_ids)
        ),
        "active_ground_states": len(active),
        "known_symmetry_state_orbits": len({orbit_key(state) for state in active}),
        "candidate_active_cells": len(active_cells),
        "active_state_compression": Fraction(len(active), len(active_cells)),
        "mixed_active_cell_count": len(mixed),
        "mixed_active_cells": tuple(str(cell) for cell in mixed),
        "policy_reachable_mixed_cell_count": len(reachable_mixed),
        "policy_reachable_mixed_cells": reachable_mixed,
        "training_policy_reached_orbits": training_reachability,
        "symmetry_normalized_active_compression": Fraction(
            len({orbit_key(state) for state in active}), len(active_cells)
        ),
        "ground_state_action_pairs": len(ground_pairs),
        "known_symmetry_state_action_orbits": len(state_action_orbits),
        "abstract_state_action_pairs": len(selection.quotient_models.envelope.entries),
        "explicit_nonorbit_pair": witness,
        "explicit_pair_same_oracle_cell": witness_same_cell,
        "explicit_pair_same_known_automorphism_orbit": witness_same_orbit,
        "explicit_pair_both_policy_reachable": witness_both_policy_reachable,
        "explicit_pair_semantic_actions": witness_actions,
        "explicit_pair_same_semantic_action": witness_same_semantic_action,
        "explicit_pair_cell": witness_cell,
    }


def _lmb_state_orbit_key(kernel: Any, automorphisms: tuple[Any, ...], state: Any) -> Any:
    return min(lmb_orbit(kernel, state, automorphisms), key=repr)


def _lmb_state_action_orbit_key(
    kernel: Any,
    automorphisms: tuple[Any, ...],
    state: Any,
    action: Any,
) -> tuple[Any, Any]:
    return min(
        (
            transform_lmb_state(kernel, state, element),
            transform_lmb_action(kernel, action, element),
        )
        for element in automorphisms
    )


def _lmb_symmetry(
    kernel: Any,
    coverage: SuiteBuildCoverage[Any],
    quotient: ExactBehavioralQuotient,
    train_query: QuerySpec[Any],
    train_policy: Any,
) -> dict[str, Any]:
    automorphisms = enumerate_lmb_automorphisms(kernel)
    active = tuple(state for state in coverage.covered_states if not kernel.is_terminal(state))
    active_cells = tuple(
        cell
        for cell in quotient.partition.cell_ids
        if not all(kernel.is_terminal(state) for state in quotient.partition.members(cell))
    )
    state_orbit_key = lambda state: _lmb_state_orbit_key(kernel, automorphisms, state)
    total_orbit_count = len(
        {state_orbit_key(state) for state in coverage.covered_states}
    )
    mixed = tuple(
        cell
        for cell in active_cells
        if len({state_orbit_key(state) for state in quotient.partition.members(cell)}) > 1
    )
    reachability_record, lifted = _training_policy_reachability(
        kernel,
        train_query,
        quotient.partition,
        train_policy,
        quotient.semantic_adapter,
        state_orbit_key,
    )
    reachable_states = {decision.state for decision in lifted.decisions}
    reachable_mixed = tuple(
        cell_record["cell"]
        for cell_record in reachability_record["cells"]
        if cell_record["cross_automorphism"] and cell_record["cell"] in mixed
    )
    ground_pairs = tuple(
        (state, action)
        for state in active
        for action in kernel.actions(state)
    )
    state_action_orbits = {
        _lmb_state_action_orbit_key(kernel, automorphisms, state, action)
        for state, action in ground_pairs
    }
    explicit_pair = (
        LMBState(11, (1, 2), LMBStatus.ACTIVE),
        LMBState(13, (2, 1), LMBStatus.ACTIVE),
    )
    if any(state not in coverage.covered_states for state in explicit_pair):
        raise Phase3AInvariantViolation(
            "registered LMB non-orbit witness left train coverage"
        )
    explicit_pair_same_cell = (
        quotient.partition.cell_of(explicit_pair[0])
        == quotient.partition.cell_of(explicit_pair[1])
    )
    explicit_pair_same_known_orbit = (
        state_orbit_key(explicit_pair[0]) == state_orbit_key(explicit_pair[1])
    )
    explicit_pair_both_policy_reachable = all(
        state in reachable_states for state in explicit_pair
    )
    explicit_pair_actions = tuple(
        lifted.action(state, train_query.horizon) for state in explicit_pair
    )
    explicit_pair_same_semantic_action = (
        explicit_pair_actions[0] == explicit_pair_actions[1]
    )
    if (
        not explicit_pair_same_cell
        or explicit_pair_same_known_orbit
        or not explicit_pair_both_policy_reachable
        or not explicit_pair_same_semantic_action
    ):
        raise Phase3AInvariantViolation(
            "LMB witness must be jointly policy-reachable in one cross-orbit cell"
        )
    return {
        "known_automorphism_group": "complete_tile_and_type_relabelling_group",
        "automorphism_count": len(automorphisms),
        "covered_ground_states": len(coverage.covered_states),
        "known_symmetry_total_state_orbits": total_orbit_count,
        "candidate_total_cells": len(quotient.partition.cell_ids),
        "symmetry_normalized_total_compression": Fraction(
            total_orbit_count, len(quotient.partition.cell_ids)
        ),
        "active_ground_states": len(active),
        "known_symmetry_state_orbits": len({state_orbit_key(state) for state in active}),
        "known_symmetry_state_action_orbits": len(state_action_orbits),
        "candidate_active_cells": len(active_cells),
        "active_state_compression": Fraction(len(active), len(active_cells)),
        "mixed_active_cell_count": len(mixed),
        "mixed_active_cells": tuple(str(cell) for cell in mixed),
        "policy_reachable_mixed_cell_count": len(reachable_mixed),
        "policy_reachable_mixed_cells": reachable_mixed,
        "training_policy_reached_orbits": (reachability_record,),
        "symmetry_normalized_active_compression": Fraction(
            len({state_orbit_key(state) for state in active}), len(active_cells)
        ),
        "ground_state_action_pairs": len(ground_pairs),
        "abstract_state_action_pairs": len(
            quotient.quotient_models.envelope.entries
        ),
        "explicit_nonorbit_pair": explicit_pair,
        "explicit_pair_same_behavioral_cell": explicit_pair_same_cell,
        "explicit_pair_same_known_automorphism_orbit": (
            explicit_pair_same_known_orbit
        ),
        "explicit_pair_both_policy_reachable": (
            explicit_pair_both_policy_reachable
        ),
        "explicit_pair_semantic_actions": explicit_pair_actions,
        "explicit_pair_same_semantic_action": (
            explicit_pair_same_semantic_action
        ),
        "explicit_pair_cell": quotient.partition.cell_of(explicit_pair[0]),
    }


def _construct_g2048() -> DomainConstruction:
    kernel, _ = safe_chain_fixture()
    train, heldout = _g2048_query_suite()
    coverage = SuiteBuildCoverage.from_queries(
        kernel,
        tuple(named.query for named in train),
        state_cap=STATE_CAP,
    )
    for named in heldout:
        coverage.validate_query_coverage(named.query)
    adapter = G2048RelativeSurvivorAdapter()
    exact_behavioral = build_exact_behavioral_quotient(kernel, coverage.covered_states)
    if exact_behavioral.cell_count != 10:
        raise Phase3AInvariantViolation("G2048 exact behavioural baseline changed")
    table = build_ground_oracle_table(
        kernel,
        coverage.covered_states,
        adapter,
        max_horizon=2,
        reward_weights=train[0].query.reward_weights,
        goal=train[0].query.goal,
        delta=train[0].query.delta,
    )
    selection = select_oracle_partition(
        kernel,
        coverage.covered_states,
        adapter,
        table,
        tuple(named.query for named in train),
        regret_tolerance=Fraction(1, 100),
        minimum_compression=Fraction(5),
        orbit_key=lambda state: canonicalize_state(state, kernel.size)[0],
        require_reachable_mixed_cell=True,
    )
    expected_atoms = (
        "h1:maximum_normalized_reward",
        "h1:selected_semantic_action@delta",
    )
    if tuple(sorted(atom.atom_id for atom in selection.selected_atoms)) != expected_atoms:
        raise Phase3AInvariantViolation("G2048 oracle atom selection changed")
    if len(selection.partition.cell_ids) != 8:
        raise Phase3AInvariantViolation("G2048 oracle quotient must have eight cells")
    evaluations = _evaluate_queries(
        "g2048",
        kernel,
        selection.partition,
        selection.quotient_models,
        adapter,
        train + heldout,
    )
    symmetry = _g2048_symmetry(kernel, coverage, selection, adapter)
    if symmetry["policy_reachable_mixed_cell_count"] < 1:
        raise Phase3AInvariantViolation("G2048 quotient lacks a reachable cross-D4 cell")
    construction = {
        "oracle_table": table,
        "selection": selection,
        "exact_behavioral_baseline_cells": exact_behavioral.cell_count,
        "exact_behavioral_trace": exact_behavioral.refinement_trace,
    }
    return DomainConstruction(
        "g2048",
        kernel,
        coverage,
        train,
        heldout,
        selection.partition,
        selection.quotient_models,
        adapter,
        construction,
        symmetry,
        evaluations,
    )


def _construct_lmb() -> DomainConstruction:
    kernel, evidence = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    train, heldout = _lmb_query_suite(kernel)
    coverage = SuiteBuildCoverage.from_queries(
        kernel,
        tuple(named.query for named in train),
        state_cap=STATE_CAP,
    )
    for named in heldout:
        coverage.validate_query_coverage(named.query)
    quotient = build_exact_behavioral_quotient(kernel, coverage.covered_states)
    if len(coverage.covered_states) != 25 or quotient.cell_count != 5:
        raise Phase3AInvariantViolation("LMB behavioural 25-to-5 golden changed")
    if tuple(step.cell_count for step in quotient.refinement_trace) != (3, 5, 5):
        raise Phase3AInvariantViolation("LMB behavioural refinement trace changed")
    evaluations = _evaluate_queries(
        "lmb",
        kernel,
        quotient.partition,
        quotient.quotient_models,
        quotient.semantic_adapter,
        train + heldout,
    )
    symmetry = _lmb_symmetry(
        kernel,
        coverage,
        quotient,
        train[0].query,
        evaluations[0].nominal_proposal.policy,
    )
    if symmetry["automorphism_count"] != 4:
        raise Phase3AInvariantViolation("LMB complete automorphism group changed")
    if symmetry["policy_reachable_mixed_cell_count"] < 1:
        raise Phase3AInvariantViolation("LMB quotient lacks a reachable cross-orbit cell")
    construction = {
        "quotient": quotient,
        "generation_evidence": evidence,
    }
    return DomainConstruction(
        "lmb",
        kernel,
        coverage,
        train,
        heldout,
        quotient.partition,
        quotient.quotient_models,
        quotient.semantic_adapter,
        construction,
        symmetry,
        evaluations,
    )


def compute_phase3a_slice() -> tuple[DomainConstruction, DomainConstruction]:
    """Build both domain controls with train/test construction isolation."""

    return _construct_g2048(), _construct_lmb()


def _state_ids(states: Iterable[Hashable]) -> dict[Hashable, str]:
    return {state: object_id(state, "state") for state in states}


def _coverage_document(construction: DomainConstruction) -> dict[str, Any]:
    kernel = construction.kernel
    state_ids = _state_ids(construction.coverage.covered_states)
    transitions = tuple(
        {
            "state_id": state_ids[state],
            "action": action,
            "outcomes": tuple(
                {
                    "probability": outcome.probability,
                    "next_state_id": state_ids[outcome.next_state],
                    "reward_features": outcome.reward_features,
                    "failure": outcome.failure,
                    "terminal": outcome.terminal,
                }
                for outcome in kernel.step(state, action)
            ),
        }
        for state in construction.coverage.covered_states
        for action in kernel.actions(state)
    )
    payload = {
        "descriptor": construction.coverage.descriptor(),
        "declared_support_states": tuple(
            {
                "state_id": state_ids[state],
                "state": state,
            }
            for state in construction.coverage.declared_support_states
        ),
        "covered_states": tuple(
            {
                "state_id": state_ids[state],
                "state": state,
                "terminal": kernel.is_terminal(state),
            }
            for state in construction.coverage.covered_states
        ),
        "transitions": transitions,
    }
    return {
        "coverage_id": object_id(payload, "suite-coverage"),
        "transition_kernel_sha256": canonical_sha256(transitions),
        **payload,
    }


def _rapm_document(construction: DomainConstruction) -> dict[str, Any]:
    state_ids = _state_ids(construction.coverage.covered_states)
    partition = {
        "cells": tuple(
            {
                "cell": cell,
                "member_state_ids": tuple(
                    sorted(state_ids[state] for state in construction.partition.members(cell))
                ),
            }
            for cell in construction.partition.cell_ids
        ),
        "ground_state_count": len(construction.partition.states),
        "cell_count": len(construction.partition.cell_ids),
        "compression": Fraction(
            len(construction.partition.states), len(construction.partition.cell_ids)
        ),
        "partition_signature": construction.partition.signature(),
    }
    nominal = tuple(
        {
            "cell": entry.cell,
            "semantic_action": entry.action,
            "model": entry.model,
        }
        for entry in construction.models.nominal.entries
    )
    envelope = tuple(
        {
            "cell": entry.cell,
            "semantic_action": entry.action,
            "realizations": tuple(
                {
                    "state_id": state_ids[realization.state],
                    "reward_features": realization.reward_features,
                    "failure_probability": realization.failure_probability,
                    "termination_probability": realization.termination_probability,
                    "successor_probabilities": realization.successor_probabilities,
                }
                for realization in entry.realizations
            ),
        }
        for entry in construction.models.envelope.entries
    )
    payload = {
        "domain": construction.domain,
        "partition": partition,
        "nominal_entries": nominal,
        "envelope_entries": envelope,
    }
    return {"rapm_id": object_id(payload, "rapm"), **payload}


def _evaluation_row(
    evaluation: QueryEvaluation,
    policy_graph_id: str,
) -> dict[str, Any]:
    ground = evaluation.ground.selected
    restricted = evaluation.restricted.selected
    if ground is None or restricted is None:
        raise Phase3AInvariantViolation("evaluation row lost a feasible comparator")
    lifted = evaluation.lift.evaluation
    audit = evaluation.audit
    return {
        "domain": evaluation.domain,
        "query_key": evaluation.query_key,
        "split": evaluation.split,
        "query_id": evaluation.query_id,
        "policy_graph_id": policy_graph_id,
        "j0_expected_reward": ground.expected_reward,
        "j0_failure_probability": ground.failure_probability,
        "j_kappa_expected_reward": restricted.expected_reward,
        "j_kappa_failure_probability": restricted.failure_probability,
        "j2_nominal_expected_reward": evaluation.nominal_proposal.expected_reward,
        "j2_nominal_failure_probability": evaluation.nominal_proposal.failure_probability,
        "j2_lifted_expected_reward": lifted.expected_reward,
        "j2_lifted_failure_probability": lifted.failure_probability,
        "action_restriction_reward_gap": ground.expected_reward - restricted.expected_reward,
        "state_alias_selector_reward_gap": restricted.expected_reward - lifted.expected_reward,
        "full_reward_gap": ground.expected_reward - lifted.expected_reward,
        "action_restriction_failure_gap": (
            restricted.failure_probability - ground.failure_probability
        ),
        "state_alias_selector_failure_gap": (
            lifted.failure_probability - restricted.failure_probability
        ),
        "full_failure_gap": (
            lifted.failure_probability - ground.failure_probability
        ),
        "lifted_risk_gap_to_j0": lifted.failure_probability - ground.failure_probability,
        "audit_reward_lower": audit.lifted_reward_lower,
        "audit_failure_upper": audit.lifted_failure_upper,
        "audit_regret_upper": audit.regret_upper,
        "audit_conservatism": (
            audit.lifted_failure_upper - lifted.failure_probability
            if audit.lifted_failure_upper is not None
            else None
        ),
        "certified": audit.certified,
        "ground_candidate_work": evaluation.ground.composed_candidate_count,
        "restricted_candidate_work": evaluation.restricted.composed_candidate_count,
    }


def _policy_graph(evaluation: QueryEvaluation, construction: DomainConstruction) -> dict[str, Any]:
    semantic_kernel = SemanticKernelView(construction.kernel, construction.adapter)
    distributions = tuple(
        {
            "remaining": decision.remaining,
            "state": decision.state,
            "semantic_action": decision.action,
            "ground_action_distribution": semantic_kernel.concretizer_distribution(
                decision.state, decision.action
            ),
        }
        for decision in evaluation.lift.lifted_semantic_policy.decisions
    )
    payload = {
        "domain": evaluation.domain,
        "query_key": evaluation.query_key,
        "query_id": evaluation.query_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "concretizer_class": "fixed_exact_distinct_action_distribution",
        "abstract_policy_signature": evaluation.nominal_proposal.policy.signature(),
        "lifted_semantic_policy_signature": (
            evaluation.lift.lifted_semantic_policy.signature()
        ),
        "reachable_concretizations": distributions,
    }
    return {"policy_graph_id": object_id(payload, "policy-graph"), **payload}


def _query_registry(constructions: tuple[DomainConstruction, ...]) -> dict[str, Any]:
    records = tuple(
        {
            "domain": construction.domain,
            "query_key": named.query_key,
            "split": named.split,
            "query_id": object_id(named.query, "query"),
            "query": named.query,
        }
        for construction in constructions
        for named in construction.train_queries + construction.heldout_queries
    )
    return {
        "construction_inputs": "train queries only",
        "heldout_queries_used_in_partition_selection": False,
        "records": records,
    }


def build_phase3a_documents(
    constructions: tuple[DomainConstruction, DomainConstruction],
    *,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    g2048, lmb = constructions
    coverage_documents = {
        construction.domain: _coverage_document(construction)
        for construction in constructions
    }
    rapm_documents = {
        construction.domain: _rapm_document(construction)
        for construction in constructions
    }
    indexed_evaluations = tuple(
        (construction, evaluation)
        for construction in constructions
        for evaluation in construction.evaluations
    )
    policy_graphs = tuple(
        _policy_graph(evaluation, construction)
        for construction, evaluation in indexed_evaluations
    )
    rows = tuple(
        _evaluation_row(evaluation, graph["policy_graph_id"])
        for (_, evaluation), graph in zip(
            indexed_evaluations,
            policy_graphs,
            strict=True,
        )
    )
    oracle_table: GroundOracleTable = g2048.construction["oracle_table"]
    selection: OraclePartitionSelection = g2048.construction["selection"]
    lmb_quotient: ExactBehavioralQuotient = lmb.construction["quotient"]
    g2048_oracle_document = {
        "construction_split": "train_only",
        "heldout_query_count_seen": 0,
        "selected_atom_ids": tuple(atom.atom_id for atom in selection.selected_atoms),
        "candidate_trace": selection.candidate_trace,
        "training_audits": tuple(
            evaluation.audit for evaluation in selection.training_evaluations
        ),
        "partition_signature": selection.partition.signature(),
        "exact_behavioral_baseline_cells": g2048.construction[
            "exact_behavioral_baseline_cells"
        ],
        "exact_behavioral_trace": g2048.construction["exact_behavioral_trace"],
    }
    lmb_oracle_document = {
        "construction": "exact_model_behavioral_partition_refinement",
        "query_values_used": False,
        "refinement_trace": lmb_quotient.refinement_trace,
        "partition_signature": lmb_quotient.partition.signature(),
        "cell_sizes": tuple(
            len(lmb_quotient.partition.members(cell))
            for cell in lmb_quotient.partition.cell_ids
        ),
        "semantic_action_rule": (
            "exact reward/failure/termination/successor-cell signature; "
            "uniform over distinct equal-signature actions"
        ),
    }
    graph_ids = {
        (
            graph["domain"],
            graph["query_id"],
            graph["lifted_semantic_policy_signature"],
        ): graph["policy_graph_id"]
        for graph in policy_graphs
    }
    symmetry_document: dict[str, Any] = {}
    for construction in constructions:
        symmetry_record = dict(construction.symmetry)
        reachability_records = []
        for record in symmetry_record["training_policy_reached_orbits"]:
            key = (
                construction.domain,
                record["query_id"],
                record["lifted_semantic_policy_signature"],
            )
            if key not in graph_ids:
                raise Phase3AInvariantViolation(
                    "training reachability record does not resolve a policy graph"
                )
            reachability_records.append(
                {"policy_graph_id": graph_ids[key], **record}
            )
        symmetry_record["training_policy_reached_orbits"] = tuple(
            reachability_records
        )
        symmetry_document[construction.domain] = symmetry_record
    reuse_document = {
        construction.domain: {
            "coverage_id": coverage_documents[construction.domain]["coverage_id"],
            "rapm_id": rapm_documents[construction.domain]["rapm_id"],
            "train_query_count": len(construction.train_queries),
            "heldout_query_count": len(construction.heldout_queries),
            "same_partition_for_every_query": True,
            "all_heldout_supports_within_train_build": True,
            "heldout_used_for_construction": False,
        }
        for construction in constructions
    }
    domain_checks = {
        construction.domain: {
            "active_state_compression_at_least_5x": (
                construction.symmetry["active_state_compression"] >= 5
            ),
            "strict_state_action_compression": (
                construction.symmetry["ground_state_action_pairs"]
                > construction.symmetry["abstract_state_action_pairs"]
            ),
            "reachable_cross_automorphism_cell": (
                construction.symmetry["policy_reachable_mixed_cell_count"] >= 1
            ),
            "all_queries_certified": all(
                evaluation.audit.certified for evaluation in construction.evaluations
            ),
            "all_action_restriction_reward_gaps_zero": all(
                evaluation.ground.selected.expected_reward
                == evaluation.restricted.selected.expected_reward
                for evaluation in construction.evaluations
                if evaluation.ground.selected is not None
                and evaluation.restricted.selected is not None
            ),
            "all_action_restriction_failure_gaps_zero": all(
                evaluation.ground.selected.failure_probability
                == evaluation.restricted.selected.failure_probability
                for evaluation in construction.evaluations
                if evaluation.ground.selected is not None
                and evaluation.restricted.selected is not None
            ),
            "all_state_alias_reward_gaps_zero": all(
                evaluation.restricted.selected.expected_reward
                == evaluation.lift.evaluation.expected_reward
                for evaluation in construction.evaluations
                if evaluation.restricted.selected is not None
            ),
            "all_state_alias_failure_gaps_zero": all(
                evaluation.restricted.selected.failure_probability
                == evaluation.lift.evaluation.failure_probability
                for evaluation in construction.evaluations
                if evaluation.restricted.selected is not None
            ),
            "all_exact_reward_gaps_zero": all(
                evaluation.ground.selected.expected_reward
                == evaluation.lift.evaluation.expected_reward
                for evaluation in construction.evaluations
                if evaluation.ground.selected is not None
            ),
            "all_exact_failure_gaps_zero": all(
                evaluation.lift.evaluation.failure_probability
                == evaluation.ground.selected.failure_probability
                for evaluation in construction.evaluations
                if evaluation.ground.selected is not None
            ),
        }
        for construction in constructions
    }
    slice_pass = all(all(checks.values()) for checks in domain_checks.values())
    if not slice_pass:
        raise Phase3AInvariantViolation("Phase3A slice checks did not all pass")
    report_payload = {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "profile_key": PROFILE_KEY,
        "domain_checks": domain_checks,
        "supported_claims": (
            "exact-model/oracle access can construct audited state-alias cells containing states from multiple complete known-automorphism orbits",
            "across the registered two-domain held-out suite, the G2048 RAPM preserves the registered initial-support/horizon changes and the LMB RAPM preserves the registered reward-basis/horizon/risk changes",
        ),
        "unsupported_claims": (
            "automatic human-readable predicate or feature invention",
            "oracle-free quotient discovery",
            "complete Phase-3 60/20/40 aggregate Gate",
            "shared cross-domain grammar or coordinate system",
            "Phase-4 CEGAR recovery from a coarse partition",
            "Phase-5 dynamic multiresolution or option-level strategic planning",
            "large-scale, POMDP, visual, or learned-world-model generality",
            "end-to-end single-query acceleration",
        ),
    }
    report = {
        "report_id": object_id(report_payload, "phase3a-report"),
        **report_payload,
    }
    benchmark_registry = {
        "benchmarks": (
            {
                "domain": "g2048",
                "ground_structural_key": g2048.kernel.fixture_key,
                "construction": "train_only_ground_oracle_signature_subset",
                "semantic_action_system": "g2048.relative_survivor.d4_equivariant.v1",
            },
            {
                "domain": "lmb",
                "ground_structural_key": "lmb_generated_n6_t2_k3_d2_seed0_v0",
                "kernel": {
                    "tile_types": lmb.kernel.tile_types,
                    "blockers": lmb.kernel.blockers,
                    "type_count": lmb.kernel.type_count,
                    "capacity": lmb.kernel.capacity,
                    "max_layers": lmb.kernel.max_layers,
                },
                "construction": "query_independent_exact_behavioral_minimization",
                "semantic_action_system": "exact_behavioral_signature.v1",
            },
        )
    }
    query_registry = _query_registry(constructions)
    seed_ledger = {
        "preregistered_fixture_seeds": {"lmb": 0, "g2048": None},
        "train_test_split_frozen_before_heldout_evaluation": True,
        "random_runtime_seeds": (),
        "deterministic": True,
    }
    semantic_payload = {
        "profile_key": PROFILE_KEY,
        "benchmark_registry": benchmark_registry,
        "query_registry": query_registry,
        "coverage_ids": {
            domain: document["coverage_id"]
            for domain, document in coverage_documents.items()
        },
        "rapm_ids": {
            domain: document["rapm_id"] for domain, document in rapm_documents.items()
        },
        "g2048_oracle": g2048_oracle_document,
        "lmb_oracle": lmb_oracle_document,
        "rows": rows,
        "policy_graph_ids": tuple(graph["policy_graph_id"] for graph in policy_graphs),
        "symmetry": symmetry_document,
        "reuse": reuse_document,
        "report": report,
    }
    semantic_hash = object_id(semantic_payload, "semantic")
    source_hash = _source_tree_hash()
    run_id = object_id(
        {
            "semantic_hash": semantic_hash,
            "source_tree_sha256": source_hash,
            "spec_hashes": _spec_hashes(),
        },
        "run",
    )
    run = {
        "schema_version": "phase3a.v1",
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "evidence": "exact_sound",
        "semantic_hash": semantic_hash,
        "source_tree_sha256": source_hash,
        "spec_hashes": _spec_hashes(),
        "command": "PYTHONPATH=src python3 -m acfqp.phase3a --output artifacts/phase3a",
        "python": sys.version,
        "platform": platform.platform(),
        "worker_count": 1,
        "dependency_lock": {
            "runtime_dependencies": "stdlib_only",
            "pyproject_sha256": sha256_file(PROJECT_ROOT / "pyproject.toml"),
        },
        "determinism_environment": {
            "PYTHONHASHSEED": os.environ.get(
                "PYTHONHASHSEED", "unset; canonical ordering enforced"
            )
        },
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
    }
    metrics = {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "domains": {
            construction.domain: {
                "covered_states": len(construction.coverage.covered_states),
                "quotient_cells": len(construction.partition.cell_ids),
                "state_compression": Fraction(
                    len(construction.coverage.covered_states),
                    len(construction.partition.cell_ids),
                ),
                "active_state_compression": construction.symmetry[
                    "active_state_compression"
                ],
                "ground_state_action_pairs": construction.symmetry[
                    "ground_state_action_pairs"
                ],
                "abstract_state_action_pairs": construction.symmetry[
                    "abstract_state_action_pairs"
                ],
                "policy_reachable_mixed_cell_count": construction.symmetry[
                    "policy_reachable_mixed_cell_count"
                ],
                "query_count": len(construction.evaluations),
            }
            for construction in constructions
        },
    }
    events = (
        {"sequence": 1, "event": "suite_registry_frozen"},
        {"sequence": 2, "event": "train_union_coverage_complete"},
        {"sequence": 3, "event": "ground_oracle_tables_complete"},
        {"sequence": 4, "event": "train_only_quotients_constructed"},
        {"sequence": 5, "event": "heldout_queries_released"},
        {"sequence": 6, "event": "exact_audit_ladder_complete"},
        {"sequence": 7, "event": "PHASE3A_SLICE_PASS"},
        {"sequence": 8, "event": "PHASE3_AGGREGATE_NOT_RUN"},
    )
    return {
        "run.json": run,
        "suite/benchmark_registry.json": benchmark_registry,
        "suite/query_registry.json": query_registry,
        "suite/split_and_seed_ledger.json": seed_ledger,
        "coverage/g2048.json": coverage_documents["g2048"],
        "coverage/lmb.json": coverage_documents["lmb"],
        "ground/g2048_oracle_table.json": {
            "oracle_table_id": object_id(oracle_table, "ground-oracle-table"),
            "table": oracle_table,
        },
        "oracle/g2048_partition_construction.json": g2048_oracle_document,
        "oracle/lmb_behavioral_construction.json": lmb_oracle_document,
        "rapm/g2048.json": rapm_documents["g2048"],
        "rapm/lmb.json": rapm_documents["lmb"],
        "evaluation/j0_jkappa_j2_rows.jsonl": rows,
        "evaluation/policy_graphs.json": {"policy_graphs": policy_graphs},
        "evaluation/symmetry_nontriviality.json": symmetry_document,
        "evaluation/reuse.json": reuse_document,
        "result/phase3a_slice_report.json": report,
        "metrics.json": metrics,
        "events.jsonl": events,
    }


def run_phase3a(output_dir: Path) -> dict[str, Any]:
    started = _utc_now()
    constructions = compute_phase3a_slice()
    documents = build_phase3a_documents(
        constructions,
        started_at=started,
        finished_at=_utc_now(),
    )
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        required_paths=PHASE3A_REQUIRED_PATHS,
    )
    failures = verify_artifact_bundle(output_dir)
    if failures:
        raise Phase3AInvariantViolation(f"artifact integrity failure: {failures!r}")
    run = documents["run.json"]
    metrics = documents["metrics.json"]
    return {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "run_id": run["run_id"],
        "semantic_hash": run["semantic_hash"],
        "bundle_sha256": manifest["bundle_sha256"],
        "domains": metrics["domains"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "phase3a",
    )
    arguments = parser.parse_args(argv)
    try:
        summary = run_phase3a(arguments.output.resolve())
    except Phase3AInvariantViolation as error:
        print(
            json.dumps(
                {"status": error.status, "detail": str(error)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
