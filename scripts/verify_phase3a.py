#!/usr/bin/env python3
"""Independently verify the Phase-3A oracle-quotient construction slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Hashable, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.abstraction import (  # noqa: E402
    ExactBehavioralQuotient,
    Partition,
    QuotientModels,
    build_exact_behavioral_quotient,
)
from acfqp.abstraction.oracle import (  # noqa: E402
    GroundOracleTable,
    OraclePartitionSelection,
    build_ground_oracle_table,
    select_oracle_partition,
)
from acfqp.artifacts import (  # noqa: E402
    PHASE3A_DOCUMENT_CONTRACTS,
    PHASE3A_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
)
from acfqp.build_coverage import SuiteBuildCoverage  # noqa: E402
from acfqp.core import QuerySpec  # noqa: E402
from acfqp.domains import (  # noqa: E402
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
from acfqp.domains.g2048 import SAFE_CHAIN_BASE_STATE  # noqa: E402
from acfqp.domains.matching_buffer import (  # noqa: E402
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.planning import (  # noqa: E402
    SemanticKernelView,
    audit_abstract_policy,
    lift_semantic_policy,
    solve_ground_pareto,
    solve_nominal_pareto,
)
from acfqp.symmetry import (  # noqa: E402
    enumerate_lmb_automorphisms,
    lmb_orbit,
    transform_lmb_action,
    transform_lmb_state,
)


PROFILE_KEY = "phase3a_true_state_alias_oracle_control_v0"
EXECUTION_PROFILE = "phase3a_true_state_alias_oracle_control"
CONTRACT_VERSION = "0.6.0"
SLICE_PASS = "PHASE3A_SLICE_PASS"
FULL_GATE_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"
STATE_CAP = 50_000
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
EXPECTED_SELECTED_ATOMS = (
    "h1:maximum_normalized_reward",
    "h1:selected_semantic_action@delta",
)
EXPECTED_EVENTS = (
    "suite_registry_frozen",
    "train_union_coverage_complete",
    "ground_oracle_tables_complete",
    "train_only_quotients_constructed",
    "heldout_queries_released",
    "exact_audit_ladder_complete",
    SLICE_PASS,
    FULL_GATE_NOT_RUN,
)
SUPPORTED_CLAIMS = (
    "exact-model/oracle access can construct audited state-alias cells containing states from multiple complete known-automorphism orbits",
    "across the registered two-domain held-out suite, the G2048 RAPM preserves the registered initial-support/horizon changes and the LMB RAPM preserves the registered reward-basis/horizon/risk changes",
)
UNSUPPORTED_CLAIMS = (
    "automatic human-readable predicate or feature invention",
    "oracle-free quotient discovery",
    "complete Phase-3 60/20/40 aggregate Gate",
    "shared cross-domain grammar or coordinate system",
    "Phase-4 CEGAR recovery from a coarse partition",
    "Phase-5 dynamic multiresolution or option-level strategic planning",
    "large-scale, POMDP, visual, or learned-world-model generality",
    "end-to-end single-query acceleration",
)


@dataclass(frozen=True, slots=True)
class NamedQuery:
    query_key: str
    split: str
    query: QuerySpec[Any]


@dataclass(frozen=True, slots=True)
class Evaluation:
    domain: str
    named: NamedQuery
    ground: Any
    restricted: Any
    proposal: Any
    audit: Any
    lift: Any


@dataclass(frozen=True, slots=True)
class ReplayDomain:
    domain: str
    kernel: Any
    coverage: SuiteBuildCoverage[Any]
    train: tuple[NamedQuery, ...]
    heldout: tuple[NamedQuery, ...]
    partition: Partition
    models: QuotientModels
    adapter: Any
    construction: Any
    symmetry: dict[str, Any]
    evaluations: tuple[Evaluation, ...]


@dataclass(frozen=True, slots=True)
class AuthoritativeReplay:
    g2048: ReplayDomain
    lmb: ReplayDomain
    automorphism_failures: tuple[str, ...]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[Any]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _source_tree_hash() -> str:
    digest = hashlib.sha256()
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
    for name in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = ROOT / name
        if path.is_file():
            paths.append(path)
    for path in sorted(set(paths)):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted((ROOT / "specs").glob("*.md"))
    }


def _normalizer_proof(domain: str) -> str:
    return {
        "g2048": "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
        "lmb": "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    }[domain]


def _g2048_suite() -> tuple[tuple[NamedQuery, ...], tuple[NamedQuery, ...]]:
    kernel, train_query = safe_chain_fixture()
    rank2_base = G2048State((2, 2, 3, 0))
    rank2_orbit = orbit(rank2_base, kernel.size)
    if len(rank2_orbit) != 8:
        raise AssertionError("rank-2 support no longer has eight D4 images")

    def query(distribution: Any, horizon: int) -> QuerySpec[Any]:
        return QuerySpec(
            tuple(distribution),
            horizon,
            (("merge", Fraction(1)),),
            "default",
            Fraction(1, 20),
            Fraction(horizon),
            _normalizer_proof("g2048"),
        )

    heldout = (
        NamedQuery(
            "g2048.rank2_uniform.h2",
            "heldout",
            query(tuple((Fraction(1, 8), state) for state in rank2_orbit), 2),
        ),
        NamedQuery(
            "g2048.mixed_points.h2",
            "heldout",
            query(
                (
                    (Fraction(1, 2), SAFE_CHAIN_BASE_STATE),
                    (Fraction(1, 2), rank2_base),
                ),
                2,
            ),
        ),
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
        raise AssertionError("G2048 bridge orbit sizes changed")
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
    return (
        (
            NamedQuery("g2048.rank1_uniform.h2", "train", train_query),
            NamedQuery(
                "g2048.strict_cross_d4_bridge.h1",
                "train",
                query(bridge_distribution, 1),
            ),
        ),
        heldout,
    )


def _lmb_suite(kernel: Any) -> tuple[tuple[NamedQuery, ...], tuple[NamedQuery, ...]]:
    states = tuple(
        LMBState(mask, buffer, LMBStatus.ACTIVE)
        for mask, buffer in LMB_TRAIN_SUPPORT
    )
    rho = tuple((Fraction(1, 9), state) for state in states)

    def query(
        horizon: int,
        weights: tuple[tuple[str, Fraction], ...],
        delta: Fraction,
        normalizer: int,
        normalizer_proof_id: str,
    ) -> QuerySpec[Any]:
        return QuerySpec(
            rho,
            horizon,
            weights,
            "default",
            delta,
            Fraction(normalizer),
            normalizer_proof_id,
        )

    train = (
        NamedQuery(
            "lmb.alias9.canonical.h3",
            "train",
            query(
                3,
                (("match", Fraction(1)), ("terminal_clear", Fraction(1))),
                Fraction(1, 20),
                4,
                _normalizer_proof("lmb"),
            ),
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
    return train, heldout


def _proposal(result: Any) -> Any:
    if result.selected is not None:
        return result.selected
    if not result.frontier:
        raise AssertionError("nominal replay has no proposal")
    return min(
        result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def _evaluate(
    domain: str,
    kernel: Any,
    partition: Partition,
    models: QuotientModels,
    adapter: Any,
    queries: tuple[NamedQuery, ...],
) -> tuple[Evaluation, ...]:
    semantic_kernel = SemanticKernelView(kernel, adapter)
    records = []
    for named in queries:
        ground = solve_ground_pareto(kernel, named.query)
        restricted = solve_ground_pareto(semantic_kernel, named.query)
        proposal = _proposal(solve_nominal_pareto(models.nominal, named.query))
        audit = audit_abstract_policy(
            kernel,
            named.query,
            models.envelope,
            proposal.policy,
            regret_tolerance=Fraction(1, 100),
        )
        lift = lift_semantic_policy(
            kernel,
            named.query,
            partition,
            proposal.policy,
            adapter,
        )
        if ground.selected is None or restricted.selected is None or not audit.certified:
            raise AssertionError(f"fresh replay did not certify {named.query_key}")
        records.append(
            Evaluation(domain, named, ground, restricted, proposal, audit, lift)
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
        orbit_representatives = _ordered(set(orbit_key(state) for state in states))
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
                        for representative in orbit_representatives
                    )
                ),
                "reached_state_count": len(set(states)),
                "reached_physical_orbit_count": len(orbit_representatives),
                "cross_automorphism": len(orbit_representatives) > 1,
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
        raise AssertionError(
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
        in {
            state
            for mass, state in evaluation.query.initial_distribution
            if mass > 0
        }
        and witness[1]
        in {
            state
            for mass, state in evaluation.query.initial_distribution
            if mass > 0
        }
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
        raise AssertionError(
            "G2048 bridge witness is not jointly policy-reachable in one cross-D4 cell"
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


def _lmb_orbit_key(kernel: Any, automorphisms: tuple[Any, ...], state: Any) -> Any:
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
    orbit_key = lambda state: _lmb_orbit_key(kernel, automorphisms, state)
    total_orbit_count = len(
        {orbit_key(state) for state in coverage.covered_states}
    )
    mixed = tuple(
        cell
        for cell in active_cells
        if len({orbit_key(state) for state in quotient.partition.members(cell)}) > 1
    )
    reachability_record, lifted = _training_policy_reachability(
        kernel,
        train_query,
        quotient.partition,
        train_policy,
        quotient.semantic_adapter,
        orbit_key,
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
    explicit_pair_same_cell = (
        quotient.partition.cell_of(explicit_pair[0])
        == quotient.partition.cell_of(explicit_pair[1])
    )
    explicit_pair_same_known_orbit = (
        orbit_key(explicit_pair[0]) == orbit_key(explicit_pair[1])
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
        raise AssertionError(
            "LMB witness is not jointly policy-reachable in one cross-orbit cell"
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
        "known_symmetry_state_orbits": len({orbit_key(state) for state in active}),
        "known_symmetry_state_action_orbits": len(state_action_orbits),
        "candidate_active_cells": len(active_cells),
        "active_state_compression": Fraction(len(active), len(active_cells)),
        "mixed_active_cell_count": len(mixed),
        "mixed_active_cells": tuple(str(cell) for cell in mixed),
        "policy_reachable_mixed_cell_count": len(reachable_mixed),
        "policy_reachable_mixed_cells": reachable_mixed,
        "training_policy_reached_orbits": (reachability_record,),
        "symmetry_normalized_active_compression": Fraction(
            len({orbit_key(state) for state in active}), len(active_cells)
        ),
        "ground_state_action_pairs": len(ground_pairs),
        "abstract_state_action_pairs": len(quotient.quotient_models.envelope.entries),
        "explicit_nonorbit_pair": explicit_pair,
        "explicit_pair_same_behavioral_cell": explicit_pair_same_cell,
        "explicit_pair_same_known_automorphism_orbit": explicit_pair_same_known_orbit,
        "explicit_pair_both_policy_reachable": explicit_pair_both_policy_reachable,
        "explicit_pair_semantic_actions": explicit_pair_actions,
        "explicit_pair_same_semantic_action": explicit_pair_same_semantic_action,
        "explicit_pair_cell": quotient.partition.cell_of(explicit_pair[0]),
    }


def _outcome_distribution(
    outcomes: Iterable[Any],
    transform: Any | None = None,
) -> dict[tuple[Any, ...], Fraction]:
    distribution: dict[tuple[Any, ...], Fraction] = {}
    for outcome in outcomes:
        next_state = transform(outcome.next_state) if transform is not None else outcome.next_state
        key = (
            next_state,
            tuple(outcome.reward_features),
            bool(outcome.failure),
            bool(outcome.terminal),
        )
        distribution[key] = distribution.get(key, Fraction(0)) + Fraction(
            outcome.probability
        )
    return distribution


def _g2048_automorphism_failures(domain: ReplayDomain) -> list[str]:
    kernel = domain.kernel
    adapter = domain.adapter
    covered = set(domain.coverage.covered_states)
    failures: list[str] = []
    for state in domain.coverage.covered_states:
        for element in D4_ELEMENTS:
            image = transform_state(state, element, kernel.size)
            if image not in covered:
                failures.append("G2048 train closure is not D4 invariant")
                return failures
            if domain.partition.cell_of(image) != domain.partition.cell_of(state):
                failures.append("G2048 oracle partition is not D4 invariant")
                return failures
            if kernel.is_terminal(state):
                continue
            if tuple(adapter.labels(kernel, image)) != tuple(adapter.labels(kernel, state)):
                failures.append("G2048 semantic labels are not D4 equivariant")
                return failures
            for label in adapter.labels(kernel, state):
                expected = {
                    transform_action(action, element, kernel.size): Fraction(probability)
                    for probability, action in adapter.concretize(kernel, state, label)
                }
                observed = {
                    action: Fraction(probability)
                    for probability, action in adapter.concretize(kernel, image, label)
                }
                if expected != observed:
                    failures.append("G2048 concretizer is not D4 equivariant")
                    return failures
            for action in kernel.actions(state):
                image_action = transform_action(action, element, kernel.size)
                expected_outcomes = _outcome_distribution(
                    kernel.step(state, action),
                    lambda successor: transform_state(successor, element, kernel.size),
                )
                if expected_outcomes != _outcome_distribution(
                    kernel.step(image, image_action)
                ):
                    failures.append("G2048 kernel is not D4 equivariant")
                    return failures
    return failures


def _lmb_automorphism_failures(domain: ReplayDomain) -> list[str]:
    kernel = domain.kernel
    quotient: ExactBehavioralQuotient = domain.construction
    adapter = quotient.semantic_adapter
    automorphisms = enumerate_lmb_automorphisms(kernel)
    covered = set(domain.coverage.covered_states)
    failures: list[str] = []
    for state in domain.coverage.covered_states:
        for element in automorphisms:
            image = transform_lmb_state(kernel, state, element)
            if image not in covered:
                failures.append("LMB train closure is not automorphism invariant")
                return failures
            if domain.partition.cell_of(image) != domain.partition.cell_of(state):
                failures.append("LMB behavioural partition is not automorphism invariant")
                return failures
            if kernel.is_terminal(state):
                continue
            for action in kernel.actions(state):
                image_action = transform_lmb_action(kernel, action, element)
                source_label = next(
                    assignment.semantic_action
                    for assignment in adapter.assignments
                    if assignment.state == state and assignment.ground_action == action
                )
                image_label = next(
                    assignment.semantic_action
                    for assignment in adapter.assignments
                    if assignment.state == image and assignment.ground_action == image_action
                )
                if source_label != image_label:
                    failures.append("LMB semantic action signatures are not equivariant")
                    return failures
                expected_outcomes = _outcome_distribution(
                    kernel.step(state, action),
                    lambda successor: transform_lmb_state(kernel, successor, element),
                )
                if expected_outcomes != _outcome_distribution(
                    kernel.step(image, image_action)
                ):
                    failures.append("LMB kernel is not equivariant")
                    return failures
    return failures


@lru_cache(maxsize=1)
def _authoritative_replay() -> AuthoritativeReplay:
    g_kernel, _ = safe_chain_fixture()
    g_train, g_heldout = _g2048_suite()
    g_coverage = SuiteBuildCoverage.from_queries(
        g_kernel,
        tuple(item.query for item in g_train),
        state_cap=STATE_CAP,
    )
    for item in g_heldout:
        g_coverage.validate_query_coverage(item.query)
    g_adapter = G2048RelativeSurvivorAdapter()
    g_exact = build_exact_behavioral_quotient(g_kernel, g_coverage.covered_states)
    g_table = build_ground_oracle_table(
        g_kernel,
        g_coverage.covered_states,
        g_adapter,
        max_horizon=2,
        reward_weights=g_train[0].query.reward_weights,
        goal=g_train[0].query.goal,
        delta=g_train[0].query.delta,
    )
    g_selection = select_oracle_partition(
        g_kernel,
        g_coverage.covered_states,
        g_adapter,
        g_table,
        tuple(item.query for item in g_train),
        regret_tolerance=Fraction(1, 100),
        minimum_compression=Fraction(5),
        orbit_key=lambda state: canonicalize_state(state, g_kernel.size)[0],
        require_reachable_mixed_cell=True,
    )
    g_evaluations = _evaluate(
        "g2048",
        g_kernel,
        g_selection.partition,
        g_selection.quotient_models,
        g_adapter,
        g_train + g_heldout,
    )
    g_domain = ReplayDomain(
        "g2048",
        g_kernel,
        g_coverage,
        g_train,
        g_heldout,
        g_selection.partition,
        g_selection.quotient_models,
        g_adapter,
        (g_table, g_selection, g_exact),
        _g2048_symmetry(g_kernel, g_coverage, g_selection, g_adapter),
        g_evaluations,
    )

    l_kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    l_train, l_heldout = _lmb_suite(l_kernel)
    l_coverage = SuiteBuildCoverage.from_queries(
        l_kernel,
        tuple(item.query for item in l_train),
        state_cap=STATE_CAP,
    )
    for item in l_heldout:
        l_coverage.validate_query_coverage(item.query)
    l_quotient = build_exact_behavioral_quotient(l_kernel, l_coverage.covered_states)
    l_evaluations = _evaluate(
        "lmb",
        l_kernel,
        l_quotient.partition,
        l_quotient.quotient_models,
        l_quotient.semantic_adapter,
        l_train + l_heldout,
    )
    l_domain = ReplayDomain(
        "lmb",
        l_kernel,
        l_coverage,
        l_train,
        l_heldout,
        l_quotient.partition,
        l_quotient.quotient_models,
        l_quotient.semantic_adapter,
        l_quotient,
        _lmb_symmetry(
            l_kernel,
            l_coverage,
            l_quotient,
            l_train[0].query,
            l_evaluations[0].proposal.policy,
        ),
        l_evaluations,
    )
    failures = _g2048_automorphism_failures(g_domain)
    failures.extend(_lmb_automorphism_failures(l_domain))
    return AuthoritativeReplay(g_domain, l_domain, tuple(failures))


def _state_ids(states: Iterable[Hashable]) -> dict[Hashable, str]:
    return {state: object_id(state, "state") for state in states}


def _coverage_document(domain: ReplayDomain) -> dict[str, Any]:
    state_ids = _state_ids(domain.coverage.covered_states)
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
                for outcome in domain.kernel.step(state, action)
            ),
        }
        for state in domain.coverage.covered_states
        for action in domain.kernel.actions(state)
    )
    payload = {
        "descriptor": domain.coverage.descriptor(),
        "declared_support_states": tuple(
            {"state_id": state_ids[state], "state": state}
            for state in domain.coverage.declared_support_states
        ),
        "covered_states": tuple(
            {
                "state_id": state_ids[state],
                "state": state,
                "terminal": domain.kernel.is_terminal(state),
            }
            for state in domain.coverage.covered_states
        ),
        "transitions": transitions,
    }
    return {
        "coverage_id": object_id(payload, "suite-coverage"),
        "transition_kernel_sha256": canonical_sha256(transitions),
        **payload,
    }


def _rapm_document(domain: ReplayDomain) -> dict[str, Any]:
    state_ids = _state_ids(domain.coverage.covered_states)
    partition = {
        "cells": tuple(
            {
                "cell": cell,
                "member_state_ids": tuple(
                    sorted(state_ids[state] for state in domain.partition.members(cell))
                ),
            }
            for cell in domain.partition.cell_ids
        ),
        "ground_state_count": len(domain.partition.states),
        "cell_count": len(domain.partition.cell_ids),
        "compression": Fraction(len(domain.partition.states), len(domain.partition.cell_ids)),
        "partition_signature": domain.partition.signature(),
    }
    nominal = tuple(
        {"cell": entry.cell, "semantic_action": entry.action, "model": entry.model}
        for entry in domain.models.nominal.entries
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
        for entry in domain.models.envelope.entries
    )
    payload = {
        "domain": domain.domain,
        "partition": partition,
        "nominal_entries": nominal,
        "envelope_entries": envelope,
    }
    return {"rapm_id": object_id(payload, "rapm"), **payload}


def _evaluation_row(
    evaluation: Evaluation,
    policy_graph_id: str,
) -> dict[str, Any]:
    ground = evaluation.ground.selected
    restricted = evaluation.restricted.selected
    if ground is None or restricted is None:
        raise AssertionError("fresh evaluation lost a comparator")
    lifted = evaluation.lift.evaluation
    audit = evaluation.audit
    return {
        "domain": evaluation.domain,
        "query_key": evaluation.named.query_key,
        "split": evaluation.named.split,
        "query_id": object_id(evaluation.named.query, "query"),
        "policy_graph_id": policy_graph_id,
        "j0_expected_reward": ground.expected_reward,
        "j0_failure_probability": ground.failure_probability,
        "j_kappa_expected_reward": restricted.expected_reward,
        "j_kappa_failure_probability": restricted.failure_probability,
        "j2_nominal_expected_reward": evaluation.proposal.expected_reward,
        "j2_nominal_failure_probability": evaluation.proposal.failure_probability,
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


def _policy_graph(evaluation: Evaluation, domain: ReplayDomain) -> dict[str, Any]:
    semantic_kernel = SemanticKernelView(domain.kernel, domain.adapter)
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
        "query_key": evaluation.named.query_key,
        "query_id": object_id(evaluation.named.query, "query"),
        "selector_class": "deterministic_finite_horizon_markov",
        "concretizer_class": "fixed_exact_distinct_action_distribution",
        "abstract_policy_signature": evaluation.proposal.policy.signature(),
        "lifted_semantic_policy_signature": evaluation.lift.lifted_semantic_policy.signature(),
        "reachable_concretizations": distributions,
    }
    return {"policy_graph_id": object_id(payload, "policy-graph"), **payload}


def _query_registry(domains: tuple[ReplayDomain, ReplayDomain]) -> dict[str, Any]:
    return {
        "construction_inputs": "train queries only",
        "heldout_queries_used_in_partition_selection": False,
        "records": tuple(
            {
                "domain": domain.domain,
                "query_key": named.query_key,
                "split": named.split,
                "query_id": object_id(named.query, "query"),
                "query": named.query,
            }
            for domain in domains
            for named in domain.train + domain.heldout
        ),
    }


def _expected_documents(replay: AuthoritativeReplay) -> dict[str, Any]:
    domains = (replay.g2048, replay.lmb)
    coverage = {domain.domain: _coverage_document(domain) for domain in domains}
    rapm = {domain.domain: _rapm_document(domain) for domain in domains}
    indexed_evaluations = tuple(
        (domain, evaluation)
        for domain in domains
        for evaluation in domain.evaluations
    )
    graphs = tuple(
        _policy_graph(evaluation, domain)
        for domain, evaluation in indexed_evaluations
    )
    rows = tuple(
        _evaluation_row(evaluation, graph["policy_graph_id"])
        for (_, evaluation), graph in zip(
            indexed_evaluations,
            graphs,
            strict=True,
        )
    )
    g_table, g_selection, g_exact = replay.g2048.construction
    l_quotient: ExactBehavioralQuotient = replay.lmb.construction
    g_oracle = {
        "construction_split": "train_only",
        "heldout_query_count_seen": 0,
        "selected_atom_ids": tuple(atom.atom_id for atom in g_selection.selected_atoms),
        "candidate_trace": g_selection.candidate_trace,
        "training_audits": tuple(
            evaluation.audit for evaluation in g_selection.training_evaluations
        ),
        "partition_signature": g_selection.partition.signature(),
        "exact_behavioral_baseline_cells": g_exact.cell_count,
        "exact_behavioral_trace": g_exact.refinement_trace,
    }
    l_oracle = {
        "construction": "exact_model_behavioral_partition_refinement",
        "query_values_used": False,
        "refinement_trace": l_quotient.refinement_trace,
        "partition_signature": l_quotient.partition.signature(),
        "cell_sizes": tuple(
            len(l_quotient.partition.members(cell))
            for cell in l_quotient.partition.cell_ids
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
        for graph in graphs
    }
    symmetry: dict[str, Any] = {}
    for domain in domains:
        symmetry_record = dict(domain.symmetry)
        reachability_records = []
        for record in symmetry_record["training_policy_reached_orbits"]:
            key = (
                domain.domain,
                record["query_id"],
                record["lifted_semantic_policy_signature"],
            )
            if key not in graph_ids:
                raise AssertionError(
                    "fresh reachability record does not resolve a policy graph"
                )
            reachability_records.append(
                {"policy_graph_id": graph_ids[key], **record}
            )
        symmetry_record["training_policy_reached_orbits"] = tuple(
            reachability_records
        )
        symmetry[domain.domain] = symmetry_record
    reuse = {
        domain.domain: {
            "coverage_id": coverage[domain.domain]["coverage_id"],
            "rapm_id": rapm[domain.domain]["rapm_id"],
            "train_query_count": len(domain.train),
            "heldout_query_count": len(domain.heldout),
            "same_partition_for_every_query": True,
            "all_heldout_supports_within_train_build": True,
            "heldout_used_for_construction": False,
        }
        for domain in domains
    }
    domain_checks = {
        domain.domain: {
            "active_state_compression_at_least_5x": (
                domain.symmetry["active_state_compression"] >= 5
            ),
            "strict_state_action_compression": (
                domain.symmetry["ground_state_action_pairs"]
                > domain.symmetry["abstract_state_action_pairs"]
            ),
            "reachable_cross_automorphism_cell": (
                domain.symmetry["policy_reachable_mixed_cell_count"] >= 1
            ),
            "all_queries_certified": all(item.audit.certified for item in domain.evaluations),
            "all_action_restriction_reward_gaps_zero": all(
                item.ground.selected.expected_reward
                == item.restricted.selected.expected_reward
                for item in domain.evaluations
            ),
            "all_action_restriction_failure_gaps_zero": all(
                item.ground.selected.failure_probability
                == item.restricted.selected.failure_probability
                for item in domain.evaluations
            ),
            "all_state_alias_reward_gaps_zero": all(
                item.restricted.selected.expected_reward
                == item.lift.evaluation.expected_reward
                for item in domain.evaluations
            ),
            "all_state_alias_failure_gaps_zero": all(
                item.restricted.selected.failure_probability
                == item.lift.evaluation.failure_probability
                for item in domain.evaluations
            ),
            "all_exact_reward_gaps_zero": all(
                item.ground.selected.expected_reward == item.lift.evaluation.expected_reward
                for item in domain.evaluations
            ),
            "all_exact_failure_gaps_zero": all(
                item.lift.evaluation.failure_probability
                == item.ground.selected.failure_probability
                for item in domain.evaluations
            ),
        }
        for domain in domains
    }
    report_payload = {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "profile_key": PROFILE_KEY,
        "domain_checks": domain_checks,
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
    }
    report = {
        "report_id": object_id(report_payload, "phase3a-report"),
        **report_payload,
    }
    benchmark_registry = {
        "benchmarks": (
            {
                "domain": "g2048",
                "ground_structural_key": replay.g2048.kernel.fixture_key,
                "construction": "train_only_ground_oracle_signature_subset",
                "semantic_action_system": "g2048.relative_survivor.d4_equivariant.v1",
            },
            {
                "domain": "lmb",
                "ground_structural_key": "lmb_generated_n6_t2_k3_d2_seed0_v0",
                "kernel": {
                    "tile_types": replay.lmb.kernel.tile_types,
                    "blockers": replay.lmb.kernel.blockers,
                    "type_count": replay.lmb.kernel.type_count,
                    "capacity": replay.lmb.kernel.capacity,
                    "max_layers": replay.lmb.kernel.max_layers,
                },
                "construction": "query_independent_exact_behavioral_minimization",
                "semantic_action_system": "exact_behavioral_signature.v1",
            },
        )
    }
    query_registry = _query_registry(domains)
    seed_ledger = {
        "preregistered_fixture_seeds": {"lmb": 0, "g2048": None},
        "train_test_split_frozen_before_heldout_evaluation": True,
        "random_runtime_seeds": (),
        "deterministic": True,
    }
    metrics = {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "domains": {
            domain.domain: {
                "covered_states": len(domain.coverage.covered_states),
                "quotient_cells": len(domain.partition.cell_ids),
                "state_compression": Fraction(
                    len(domain.coverage.covered_states), len(domain.partition.cell_ids)
                ),
                "active_state_compression": domain.symmetry[
                    "active_state_compression"
                ],
                "ground_state_action_pairs": domain.symmetry["ground_state_action_pairs"],
                "abstract_state_action_pairs": domain.symmetry["abstract_state_action_pairs"],
                "policy_reachable_mixed_cell_count": domain.symmetry[
                    "policy_reachable_mixed_cell_count"
                ],
                "query_count": len(domain.evaluations),
            }
            for domain in domains
        },
    }
    events = tuple(
        {"sequence": index, "event": event}
        for index, event in enumerate(EXPECTED_EVENTS, start=1)
    )
    return {
        "suite/benchmark_registry.json": benchmark_registry,
        "suite/query_registry.json": query_registry,
        "suite/split_and_seed_ledger.json": seed_ledger,
        "coverage/g2048.json": coverage["g2048"],
        "coverage/lmb.json": coverage["lmb"],
        "ground/g2048_oracle_table.json": {
            "oracle_table_id": object_id(g_table, "ground-oracle-table"),
            "table": g_table,
        },
        "oracle/g2048_partition_construction.json": g_oracle,
        "oracle/lmb_behavioral_construction.json": l_oracle,
        "rapm/g2048.json": rapm["g2048"],
        "rapm/lmb.json": rapm["lmb"],
        "evaluation/j0_jkappa_j2_rows.jsonl": rows,
        "evaluation/policy_graphs.json": {"policy_graphs": graphs},
        "evaluation/symmetry_nontriviality.json": symmetry,
        "evaluation/reuse.json": reuse,
        "result/phase3a_slice_report.json": report,
        "metrics.json": metrics,
        "events.jsonl": events,
    }


def _semantic_payload(documents: dict[str, Any]) -> dict[str, Any]:
    graphs = documents["evaluation/policy_graphs.json"]["policy_graphs"]
    return {
        "profile_key": PROFILE_KEY,
        "benchmark_registry": documents["suite/benchmark_registry.json"],
        "query_registry": documents["suite/query_registry.json"],
        "coverage_ids": {
            domain: documents[f"coverage/{domain}.json"]["coverage_id"]
            for domain in ("g2048", "lmb")
        },
        "rapm_ids": {
            domain: documents[f"rapm/{domain}.json"]["rapm_id"]
            for domain in ("g2048", "lmb")
        },
        "g2048_oracle": documents["oracle/g2048_partition_construction.json"],
        "lmb_oracle": documents["oracle/lmb_behavioral_construction.json"],
        "rows": documents["evaluation/j0_jkappa_j2_rows.jsonl"],
        "policy_graph_ids": tuple(graph["policy_graph_id"] for graph in graphs),
        "symmetry": documents["evaluation/symmetry_nontriviality.json"],
        "reuse": documents["evaluation/reuse.json"],
        "report": documents["result/phase3a_slice_report.json"],
    }


def _load_documents(bundle: Path) -> dict[str, Any]:
    documents: dict[str, Any] = {}
    for path in PHASE3A_REQUIRED_PATHS:
        if path == "run.json":
            continue
        full_path = bundle / path
        documents[path] = (
            load_jsonl(full_path) if path.endswith(".jsonl") else load(full_path)
        )
    return documents


def _append_document_mismatch(
    path: str,
    failures: list[str],
) -> None:
    if path.startswith("suite/") or path.startswith("coverage/"):
        failures.append(f"train/test isolation or suite coverage mismatch: {path}")
    elif path == "evaluation/symmetry_nontriviality.json":
        failures.append("automorphism/nontriviality artifact mismatch")
    elif path.startswith("evaluation/j0_") or path == "evaluation/policy_graphs.json":
        failures.append(f"fresh evaluation/golden mismatch: {path}")
    elif path.startswith("result/"):
        failures.append("Phase3A narrow slice report/claim mismatch")
    else:
        failures.append(f"fresh authoritative artifact mismatch: {path}")


def verify_phase3a(bundle: Path, *, recompute: bool = True) -> dict[str, Any]:
    """Verify integrity, frozen semantics, isolation, and exact fresh goldens."""

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
    required = set(PHASE3A_REQUIRED_PATHS)
    if set(manifest.get("required_paths", ())) != required:
        failures.append("manifest does not declare the complete Phase3A artifact set")
    if set(records) != required:
        failures.append("manifest file inventory is not exactly the Phase3A contract")
    for path, (role, schema) in PHASE3A_DOCUMENT_CONTRACTS.items():
        record = records.get(path)
        if not record:
            failures.append(f"required Phase3A artifact absent: {path}")
        elif (
            record.get("role") != role
            or record.get("schema") != schema
            or record.get("required") is not True
        ):
            failures.append(f"Phase3A role/schema contract mismatch: {path}")

    try:
        run = load(bundle / "run.json")
        documents = _load_documents(bundle)
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot load complete Phase3A artifact set: {error}")
        return {
            "status": None,
            "semantic_hash": None,
            "recomputed_semantic_hash": None,
            "failures": failures,
            "verified": False,
        }

    expected_run_fields = {
        "schema_version": "phase3a.v1",
        "contract_version": CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_GATE_NOT_RUN,
        "evidence": "exact_sound",
        "worker_count": 1,
    }
    for field, expected in expected_run_fields.items():
        if run.get(field) != expected:
            failures.append(f"run identity/status mismatch: {field}")
    if run.get("full_phase3_gate_status") == "PASS":
        failures.append("Phase3A slice falsely claims the aggregate Phase-3 Gate")

    source_hash = _source_tree_hash()
    spec_hashes = _spec_hashes()
    if run.get("source_tree_sha256") != source_hash:
        failures.append("run source-tree parent hash is stale")
    if run.get("spec_hashes") != spec_hashes:
        failures.append("run spec parent hashes are stale or incomplete")
    dependency = run.get("dependency_lock", {})
    if (
        dependency.get("runtime_dependencies") != "stdlib_only"
        or dependency.get("pyproject_sha256") != sha256_file(ROOT / "pyproject.toml")
    ):
        failures.append("run dependency lock mismatch")

    stored_semantic_hash = None
    try:
        stored_semantic_hash = object_id(_semantic_payload(documents), "semantic")
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"cannot recompute semantic hash from stored documents: {error}")
    if run.get("semantic_hash") != stored_semantic_hash:
        failures.append("stored semantic payload hash mismatch")
    expected_run_id = object_id(
        {
            "semantic_hash": run.get("semantic_hash"),
            "source_tree_sha256": source_hash,
            "spec_hashes": spec_hashes,
        },
        "run",
    )
    if run.get("run_id") != expected_run_id:
        failures.append("run ID does not bind semantic/source/spec parents")

    events = documents["events.jsonl"]
    if (
        tuple(event.get("event") for event in events) != EXPECTED_EVENTS
        or [event.get("sequence") for event in events] != list(range(1, 9))
    ):
        failures.append("train/heldout release event ordering mismatch")

    query_registry = documents["suite/query_registry.json"]
    records_by_split = query_registry.get("records", [])
    if (
        query_registry.get("construction_inputs") != "train queries only"
        or query_registry.get("heldout_queries_used_in_partition_selection") is not False
        or sum(record.get("split") == "train" for record in records_by_split) != 3
        or sum(record.get("split") == "heldout" for record in records_by_split) != 6
    ):
        failures.append("train/test isolation registry mismatch")
    if (
        documents["oracle/g2048_partition_construction.json"].get(
            "construction_split"
        )
        != "train_only"
        or documents["oracle/g2048_partition_construction.json"].get(
            "heldout_query_count_seen"
        )
        != 0
        or documents["oracle/lmb_behavioral_construction.json"].get(
            "query_values_used"
        )
        is not False
    ):
        failures.append("heldout/query values leaked into quotient construction")
    reuse = documents["evaluation/reuse.json"]
    for domain in ("g2048", "lmb"):
        record = reuse.get(domain, {})
        if (
            record.get("same_partition_for_every_query") is not True
            or record.get("all_heldout_supports_within_train_build") is not True
            or record.get("heldout_used_for_construction") is not False
        ):
            failures.append(f"train/test reuse isolation mismatch: {domain}")

    evaluation_rows = documents["evaluation/j0_jkappa_j2_rows.jsonl"]
    policy_graphs = documents["evaluation/policy_graphs.json"].get(
        "policy_graphs", []
    )
    graph_by_id = {
        graph.get("policy_graph_id"): graph
        for graph in policy_graphs
        if isinstance(graph, dict) and graph.get("policy_graph_id")
    }
    if (
        len(graph_by_id) != len(policy_graphs)
        or len(evaluation_rows) != len(policy_graphs)
    ):
        failures.append("policy graph IDs are missing or non-unique")
    zero = {"numerator": 0, "denominator": 1}
    gap_fields = (
        "action_restriction_reward_gap",
        "state_alias_selector_reward_gap",
        "full_reward_gap",
        "action_restriction_failure_gap",
        "state_alias_selector_failure_gap",
        "full_failure_gap",
    )
    for row in evaluation_rows:
        graph = graph_by_id.get(row.get("policy_graph_id"))
        if graph is None:
            failures.append("evaluation row does not resolve its policy_graph_id")
        elif (
            graph.get("query_id") != row.get("query_id")
            or graph.get("domain") != row.get("domain")
            or graph.get("query_key") != row.get("query_key")
        ):
            failures.append("evaluation row/policy graph identity mismatch")
        if any(row.get(field) != zero for field in gap_fields):
            failures.append(
                "evaluation row has a nonzero or missing J0/Jkappa/J2 segment gap"
            )

    symmetry_document = documents["evaluation/symmetry_nontriviality.json"]
    for domain in ("g2048", "lmb"):
        covered_state_ids = {
            record.get("state_id")
            for record in documents[f"coverage/{domain}.json"].get(
                "covered_states", []
            )
        }
        train_query_ids = {
            record.get("query_id")
            for record in records_by_split
            if record.get("domain") == domain and record.get("split") == "train"
        }
        symmetry_record = symmetry_document.get(domain, {})
        reachability_records = symmetry_record.get(
            "training_policy_reached_orbits", []
        )
        if {
            record.get("query_id")
            for record in reachability_records
            if isinstance(record, dict)
        } != train_query_ids:
            failures.append(
                f"per-training-policy reached-orbit query inventory mismatch: {domain}"
            )
        cross_cells: set[str] = set()
        for policy_record in reachability_records:
            graph = graph_by_id.get(policy_record.get("policy_graph_id"))
            if graph is None or (
                graph.get("domain") != domain
                or graph.get("query_id") != policy_record.get("query_id")
                or graph.get("abstract_policy_signature")
                != policy_record.get("abstract_policy_signature")
                or graph.get("lifted_semantic_policy_signature")
                != policy_record.get("lifted_semantic_policy_signature")
            ):
                failures.append(
                    f"training reached-orbit record/policy graph mismatch: {domain}"
                )
                graph = None
            reached_nodes: set[tuple[int, str]] = set()
            for cell in policy_record.get("cells", []):
                orbit_ids = cell.get("reached_physical_orbit_ids", [])
                orbit_count = cell.get("reached_physical_orbit_count")
                cross = cell.get("cross_automorphism")
                cell_nodes = {
                    (node.get("remaining"), node.get("state_id"))
                    for node in cell.get("reached_state_time_nodes", [])
                }
                reached_nodes.update(cell_nodes)
                if (
                    {state_id for _, state_id in cell_nodes}
                    != set(cell.get("reached_state_ids", []))
                    or not set(cell.get("reached_state_ids", [])).issubset(
                        covered_state_ids
                    )
                ):
                    failures.append(
                        f"per-policy reached state inventory mismatch: {domain}"
                    )
                expected_cross = isinstance(orbit_count, int) and orbit_count > 1
                if orbit_count != len(set(orbit_ids)) or cross is not expected_cross:
                    failures.append(
                        f"per-policy reached-orbit cell is internally inconsistent: {domain}"
                    )
                if cross:
                    cross_cells.add(canonical_sha256(cell.get("cell")))
            if graph is not None:
                graph_nodes = {
                    (
                        node.get("remaining"),
                        object_id(node.get("state"), "state"),
                    )
                    for node in graph.get("reachable_concretizations", [])
                }
                if reached_nodes != graph_nodes:
                    failures.append(
                        f"training reached-orbit nodes do not match policy graph: {domain}"
                    )
        summary_cells = {
            canonical_sha256(cell)
            for cell in symmetry_record.get("policy_reachable_mixed_cells", [])
        }
        if cross_cells != summary_cells or len(cross_cells) != symmetry_record.get(
            "policy_reachable_mixed_cell_count"
        ):
            failures.append(
                f"per-policy reached-orbit summary mismatch: {domain}"
            )

    recomputed_hash = None
    if recompute:
        try:
            replay = _authoritative_replay()
            expected_documents = _expected_documents(replay)
        except Exception as error:  # pragma: no cover - surfaced as verifier failure
            failures.append(
                f"fresh authoritative Phase3A recomputation failed: "
                f"{type(error).__name__}: {error}"
            )
        else:
            if replay.automorphism_failures:
                failures.extend(replay.automorphism_failures)
            for path, expected in expected_documents.items():
                if documents.get(path) != to_jsonable(expected):
                    _append_document_mismatch(path, failures)
            recomputed_hash = object_id(
                _semantic_payload(to_jsonable(expected_documents)),
                "semantic",
            )
            if run.get("semantic_hash") != recomputed_hash:
                failures.append("fresh recomputation semantic hash differs from bundle")

            g_table, g_selection, g_exact = replay.g2048.construction
            l_quotient: ExactBehavioralQuotient = replay.lmb.construction
            selected_atoms = tuple(
                sorted(atom.atom_id for atom in g_selection.selected_atoms)
            )
            g_symmetry = replay.g2048.symmetry
            if (
                len(replay.g2048.coverage.covered_states) != 192
                or len(g_selection.partition.cell_ids) != 8
                or g_exact.cell_count != 10
                or selected_atoms != EXPECTED_SELECTED_ATOMS
                or len(g_table.records) != 136
                or len(g_table.action_frontiers) != 288
                or g_symmetry["known_symmetry_total_state_orbits"] != 28
                or g_symmetry["known_symmetry_state_orbits"] != 9
                or g_symmetry["candidate_total_cells"] != 8
                or g_symmetry["candidate_active_cells"] != 7
                or g_symmetry["known_symmetry_state_action_orbits"] != 18
                or g_symmetry["abstract_state_action_pairs"] != 14
            ):
                failures.append("G2048 Phase3A construction golden mismatch")
            bridge = next(
                evaluation
                for evaluation in replay.g2048.evaluations
                if evaluation.named.query_key
                == "g2048.strict_cross_d4_bridge.h1"
            )
            bridge_ground = bridge.ground.selected
            if (
                bridge_ground is None
                or bridge_ground.expected_reward != Fraction(13, 400)
                or bridge_ground.failure_probability != Fraction(199, 5000)
                or bridge.lift.evaluation.expected_reward != Fraction(13, 400)
                or bridge.lift.evaluation.failure_probability
                != Fraction(199, 5000)
                or bridge.audit.lifted_reward_lower != Fraction(13, 400)
                or bridge.audit.lifted_failure_upper != Fraction(1, 25)
                or bridge.audit.regret_upper != 0
            ):
                failures.append("G2048 strict bridge evaluation golden mismatch")
            if (
                len(replay.lmb.coverage.covered_states) != 25
                or len(l_quotient.partition.cell_ids) != 5
                or tuple(step.cell_count for step in l_quotient.refinement_trace)
                != (3, 5, 5)
                or len(enumerate_lmb_automorphisms(replay.lmb.kernel)) != 4
                or replay.lmb.symmetry["known_symmetry_total_state_orbits"] != 13
                or replay.lmb.symmetry["known_symmetry_state_orbits"] != 10
                or replay.lmb.symmetry["candidate_active_cells"] != 3
            ):
                failures.append("LMB Phase3A construction golden mismatch")
            for domain in (replay.g2048, replay.lmb):
                if (
                    domain.symmetry["mixed_active_cell_count"] < 1
                    or domain.symmetry["policy_reachable_mixed_cell_count"] < 1
                    or not all(item.audit.certified for item in domain.evaluations)
                    or not all(
                        item.ground.selected.expected_reward
                        == item.restricted.selected.expected_reward
                        for item in domain.evaluations
                    )
                    or not all(
                        item.ground.selected.failure_probability
                        == item.restricted.selected.failure_probability
                        for item in domain.evaluations
                    )
                    or not all(
                        item.restricted.selected.expected_reward
                        == item.lift.evaluation.expected_reward
                        for item in domain.evaluations
                    )
                    or not all(
                        item.restricted.selected.failure_probability
                        == item.lift.evaluation.failure_probability
                        for item in domain.evaluations
                    )
                ):
                    failures.append(
                        f"{domain.domain} cross-automorphism/exact-evaluation golden mismatch"
                    )

    return {
        "status": run.get("status"),
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_hash,
        "failures": failures,
        "verified": not failures,
    }


verify_bundle = verify_phase3a


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        type=Path,
        nargs="?",
        default=ROOT / "artifacts" / "phase3a",
    )
    parser.add_argument(
        "--no-recompute",
        action="store_true",
        help="skip the expensive fresh oracle/model/evaluation replay",
    )
    arguments = parser.parse_args(argv)
    report = verify_phase3a(
        arguments.bundle,
        recompute=not arguments.no_recompute,
    )
    print(json.dumps(to_jsonable(report), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
