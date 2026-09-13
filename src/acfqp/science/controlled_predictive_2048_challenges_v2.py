"""Proposed public mechanism challenges and their bounded discovery records.

These constructed dense boards are not a natural-play distribution. Spatial
pairs share their generator source and split. Source seeds are assigned without
looking at exact characterization or candidate performance. Discovery seeds are
separate, exposed development data and are never returned by the final roster.
Both discovery recipes failed to exhibit a strict H3 root-query switch. The
24-case proposed roster is therefore deferred; its existence is not evidence
that the comparison cohort ran or that the required challenge is established.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_quotient_v1 import (
    Query,
    audit_policy,
    compile_full_state,
    plan,
)


FAMILIES = ("cross_axis_pairs", "gradient_bottleneck", "near_goal_corridor")
FAILURE_PENALTIES = (0.0, 0.05, 0.2, 1.0, 5.0)
SPLIT_SOURCE_SEEDS = (
    ("TRAIN_DEVELOPMENT", 831101),
    ("TRAIN_DEVELOPMENT", 831201),
    ("CALIBRATION", 832101),
    ("EVALUATION", 833101),
)
DISCOVERY_SEEDS = (830001, 830011, 830021, 830031)
ROUND2_FAMILIES = ("single_pair_spawn", "sparse_cross_axis", "immediate_goal_detour")
ROUND2_DISCOVERY_SEEDS = tuple(834001 + 10 * index for index in range(8))


@dataclass(frozen=True)
class ChallengeCase:
    name: str
    group: str
    split: str
    board: tuple[int, ...]
    family: str
    seed: int
    variant: str = "identity"


def _source_board(family: str, seed: int) -> tuple[int, ...]:
    """Build a supported rank board directly; perform no performance filtering."""
    rng = random.Random(seed)
    if family == "cross_axis_pairs":
        board = [rng.randint(4, 9) for _ in range(16)]
        board[0] = board[1] = rng.choice((1, 2, 3))
        board[4] = board[8] = rng.choice((5, 6, 7))
        board[12], board[15] = 1, 2
    elif family == "gradient_bottleneck":
        peak = rng.choice((7, 8, 9))
        board = [peak - row - col for row in range(4) for col in range(4)]
        board[1] = board[0]
        board[14] = board[15] = rng.choice((1, 2))
        board[7] = rng.choice((2, 3, 4))
        board[11] = rng.choice((2, 3, 4))
    elif family == "near_goal_corridor":
        board = [rng.randint(3, 8) for _ in range(16)]
        board[0] = board[1] = 9
        board[4] = 10
        board[5] = board[9] = rng.choice((4, 5, 6))
        board[12], board[15] = 1, 2
    else:
        raise ValueError(f"unknown challenge family: {family}")
    return tuple(board)


def _rotate_quarter_turn(board: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(board[(3 - col) * 4 + row] for row in range(4) for col in range(4))


def _source_board_round2(family: str, seed: int) -> tuple[int, ...]:
    """Avoid accidental background merges before injecting the declared pairs."""
    rng = random.Random(seed)
    ranks = range(1, 6) if family == "single_pair_spawn" else range(3, 10)
    board: list[int] = []
    for cell in range(16):
        excluded = {board[cell - 1]} if cell % 4 else set()
        if cell >= 4:
            excluded.add(board[cell - 4])
        board.append(rng.choice([rank for rank in ranks if rank not in excluded]))
    if family == "single_pair_spawn":
        board[5] = board[6] = rng.choice((1, 2, 3))
    elif family == "sparse_cross_axis":
        board[0] = board[1] = rng.choice((1, 2))
        board[4] = board[8] = rng.choice((4, 5, 6))
        board[12], board[15] = 1, 2
    elif family == "immediate_goal_detour":
        board[0] = board[1] = 10
        board[4] = board[8] = rng.choice((8, 9))
        board[rng.choice((6, 10, 13))] = 10
        board[12], board[15] = 1, 2
    else:
        raise ValueError(f"unknown round2 challenge family: {family}")
    return tuple(board)


def generate_round2_discovery_cases() -> tuple[ChallengeCase, ...]:
    """The second and last bounded recipe round; all 24 are exposed data."""
    return tuple(
        ChallengeCase(
            name=f"discovery_round2_{family}_{seed + family_index}",
            group=f"discovery_round2_{family}_source_{seed + family_index}",
            split="EXPOSED_GENERATOR_DISCOVERY",
            board=_source_board_round2(family, seed + family_index),
            family=family, seed=seed + family_index,
        )
        for family_index, family in enumerate(ROUND2_FAMILIES)
        for seed in ROUND2_DISCOVERY_SEEDS
    )


def generate_challenge_cases() -> tuple[ChallengeCase, ...]:
    """Return the 24 proposed, deferred candidates without evaluating them.

    The family is shared across splits, while each source group (its unrotated
    board and clockwise rotation) belongs to exactly one split. A runner must
    also inspect cross-split raw-board closure overlap before making any claim
    about unseen states; generator-source separation alone is insufficient.
    """
    cases = []
    for family_index, family in enumerate(FAMILIES):
        for split, base_seed in SPLIT_SOURCE_SEEDS:
            seed = base_seed + family_index
            group = f"{family}_source_{seed}"
            source = _source_board(family, seed)
            for variant, board in (("identity", source), ("rotate90", _rotate_quarter_turn(source))):
                cases.append(ChallengeCase(
                    name=f"{group}_{variant}", group=group, split=split,
                    board=board, family=family, seed=seed, variant=variant,
                ))
    return tuple(cases)


def generate_discovery_cases() -> tuple[ChallengeCase, ...]:
    """Twelve bounded recipe probes, all retained and permanently exposed."""
    return tuple(
        ChallengeCase(
            name=f"discovery_{family}_{seed + family_index}",
            group=f"discovery_{family}_source_{seed + family_index}",
            split="EXPOSED_GENERATOR_DISCOVERY",
            board=_source_board(family, seed + family_index),
            family=family, seed=seed + family_index,
        )
        for family_index, family in enumerate(FAMILIES)
        for seed in DISCOVERY_SEEDS
    )


def characterize_exact_case(
    case: ChallengeCase, *, max_nodes: int = 30_000,
) -> dict[str, Any]:
    """Exact H1/H3 query characterization for development recipe inspection.

    No empirical model or candidate quotient is fitted here. An action switch
    requires disjoint optimal-action sets, not different numerical tie breaks.
    A complete-closure budget failure is retained and never resampled.
    """
    result: dict[str, Any] = {
        "name": case.name, "group": case.group, "split": case.split,
        "family": case.family, "seed": case.seed, "variant": case.variant,
        "board": list(case.board), "horizons": {},
    }
    for horizon in (1, 3):
        try:
            closure = build_development_closure(
                horizon=horizon, max_nodes=max_nodes, boards={case.name: case.board},
            )
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            result["horizons"][str(horizon)] = {"status": "BUDGET_EXCEEDED", "error": str(error)}
            continue
        compiled = compile_full_state(closure.model)
        root = compiled.roots[0]
        queries = {}
        query_specs = [(str(penalty), Query(1.0, penalty, 0.0)) for penalty in FAILURE_PENALTIES]
        query_specs.append(("goal_1_risk_1", Query(1.0, 1.0, 1.0)))
        for query_name, query in query_specs:
            solution = plan(compiled, query)
            action_values = {
                action: math.fsum(
                    outcome.probability * (outcome.reward + solution.values[outcome.next_state])
                    for outcome in outcomes
                )
                for (state, action), outcomes in compiled.rows.items() if state == root
            }
            optimum = max(action_values.values())
            queries[query_name] = {
                "reward_weight": query.reward_weight,
                "failure_penalty": query.failure_penalty,
                "goal_bonus": query.goal_bonus,
                "root_action_values": action_values,
                "optimal_actions": sorted(
                    action for action, value in action_values.items()
                    if abs(value - optimum) <= 1e-10
                ),
                "chosen_action": solution.policy[root],
                "metrics": audit_policy(closure.model, compiled, solution, query).root_metrics[
                    closure.model.roots[0]
                ],
            }
        pairs = [
            [left, right] for index, left in enumerate(queries)
            for right in tuple(queries)[index + 1:]
            if set(queries[left]["optimal_actions"]).isdisjoint(queries[right]["optimal_actions"])
        ]
        result["horizons"][str(horizon)] = {
            "status": "COMPLETE", "counts": closure.counts,
            "queries": queries, "strict_query_switch_pairs": pairs,
        }
    h1, h3 = result["horizons"]["1"], result["horizons"]["3"]
    result["strict_horizon_switch_queries"] = [
        penalty for penalty in h1.get("queries", {})
        if penalty in h3.get("queries", {}) and set(h1["queries"][penalty]["optimal_actions"]).isdisjoint(
            h3["queries"][penalty]["optimal_actions"]
        )
    ]
    result["strict_horizon_switch_penalties"] = [
        query for query in result["strict_horizon_switch_queries"] if query != "goal_1_risk_1"
    ]
    return result
