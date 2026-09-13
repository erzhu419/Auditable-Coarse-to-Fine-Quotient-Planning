"""Finite-horizon 2048 abstraction by certified nonparticipating tile ranks.

The rule is synthesized once at the root. Anonymous tiles retain their location
and movement, but cannot merge. Both experimental arms use this same local
mechanics implementation; neither builder imports the ground environment.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from time import perf_counter

from .controlled_predictive_quotient_v1 import FiniteModel, Outcome


ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT")
ANONYMOUS = -1
GOAL_RANK = 11
StateKey = tuple[int, tuple[int, ...] | str]


@dataclass(frozen=True)
class ForgettingRule:
    horizon: int
    forgotten_ranks: tuple[int, ...]
    partner_upper_bounds: dict[int, int]
    counts: dict[str, int]
    certified: bool = True


@dataclass(frozen=True)
class Build:
    model: FiniteModel
    boards: dict[int, tuple[int, ...]]
    state_index: dict[StateKey, int]
    rule: ForgettingRule
    counts: dict[str, int]
    elapsed_seconds: float


def _line_cells(action: str, index: int) -> tuple[int, ...]:
    if action == "UP":
        return tuple(4 * row + index for row in range(4))
    if action == "DOWN":
        return tuple(4 * row + index for row in range(3, -1, -1))
    if action == "LEFT":
        return tuple(4 * index + col for col in range(4))
    if action == "RIGHT":
        return tuple(4 * index + col for col in range(3, -1, -1))
    raise ValueError("unknown swipe action")


def swipe(
    board: tuple[int, ...], action: str, work: Counter | None = None,
) -> tuple[tuple[int, ...], int, bool]:
    """Slide all four lines, merging equal positive ranks once per swipe."""
    if work is not None:
        work["kernel_swipe_calls"] += 1
        work["kernel_line_transforms"] += 4
    result = list(board)
    score = 0
    for line in range(4):
        cells = _line_cells(action, line)
        occupied = [board[cell] for cell in cells if board[cell] != 0]
        output = []
        index = 0
        while index < len(occupied):
            rank = occupied[index]
            if rank > 0 and index + 1 < len(occupied) and occupied[index + 1] == rank:
                rank += 1
                score += 1 << rank
                index += 2
            else:
                index += 1
            output.append(rank)
        output.extend([0] * (4 - len(output)))
        for cell, rank in zip(cells, output):
            result[cell] = rank
    moved = tuple(result)
    return moved, score, moved != board


def _classify(board: tuple[int, ...], work: Counter | None = None):
    if work is not None:
        work["kernel_terminal_checks"] += 1
    if max(board) >= GOAL_RANK:
        return "WON", ()
    moves = []
    for action in ACTION_ORDER:
        moved, score, changed = swipe(board, action, work)
        if changed:
            moves.append((action, moved, score))
    return ("ACTIVE", tuple(moves)) if moves else ("LOST", ())


def terminal_status(board: tuple[int, ...], work: Counter | None = None) -> str:
    return _classify(board, work)[0]


def _check_root(board: tuple[int, ...], horizon: int) -> None:
    if len(board) != 16 or any(type(rank) is not int or not 0 <= rank <= 19 for rank in board):
        raise ValueError("root must have sixteen supported nonnegative ranks")
    if type(horizon) is not int or horizon < 1:
        raise ValueError("horizon must be a positive integer")


def synthesize_rule(board: tuple[int, ...], horizon: int) -> ForgettingRule:
    """Prove that a singleton rank has no possible partner within H+1 steps.

    U retains every old tile and adds all possible pair products synchronously.
    Adding both spawn ranks each step further overestimates availability. This
    ignores geometry and consumes no parents, so a zero count is a sufficient
    impossibility certificate, while a positive count establishes nothing.
    The additional step conservatively includes final-state legal-action tests.
    """
    _check_root(board, horizon)
    work = Counter(rule_synthesis_calls=1)
    if terminal_status(board, work) != "ACTIVE":
        return ForgettingRule(horizon, (), {}, dict(work))
    multiplicities = Counter(rank for rank in board if rank > 0)
    bounds = {}
    for rank in sorted(multiplicities):
        if multiplicities[rank] != 1:
            continue
        work["rule_rank_candidates"] += 1
        upper = [0] * (rank + 1)
        for lower in range(1, rank + 1):
            upper[lower] = multiplicities[lower] - int(lower == rank)
        for _ in range(horizon + 1):
            previous = upper
            upper = [0] * (rank + 1)
            for lower in range(1, rank + 1):
                upper[lower] = (previous[lower] + previous[lower - 1] // 2
                                + int(lower in (1, 2)))
                work["rule_upper_bound_updates"] += 1
            work["rule_transition_steps"] += 1
        bounds[rank] = upper[rank]
    forgotten = tuple(rank for rank, partner_count in bounds.items() if partner_count == 0)
    work["rule_forgotten_ranks"] = len(forgotten)
    return ForgettingRule(horizon, forgotten, bounds, dict(work))


def encode_key(board: tuple[int, ...], h: int, rule: ForgettingRule) -> StateKey:
    """Map a covered concrete board to its fixed-rule abstract model key."""
    symbolic = tuple(ANONYMOUS if rank in rule.forgotten_ranks else rank for rank in board)
    status = terminal_status(symbolic)
    if status == "ACTIVE" and h == 0:
        status = "CUTOFF"
    return (h, symbolic) if status == "ACTIVE" else (h, status)


def build_model(
    board: tuple[int, ...], horizon: int, variant: str, max_states: int = 30_000,
) -> Build:
    """Expand distinct symbolic states directly, with identical terminal folding.

    BASELINE retains all ranks. CAUSAL erases only certified singleton ranks
    once, before expansion. No concrete descendant board or encoding table is
    available to the causal transition loop.
    """
    started = perf_counter()
    _check_root(board, horizon)
    if variant not in {"BASELINE", "CAUSAL", "UNSAFE"}:
        raise ValueError("variant must be BASELINE, CAUSAL, or UNSAFE")
    if type(max_states) is not int or max_states < 1:
        raise ValueError("max_states must be positive")
    if variant == "CAUSAL":
        rule = synthesize_rule(board, horizon)
    elif variant == "UNSAFE":
        unsafe_work = Counter(rule_synthesis_calls=1)
        counts = Counter(board)
        forgotten = (tuple(sorted(rank for rank, count in counts.items() if 0 < rank < 11 and count == 1))
                     if terminal_status(board, unsafe_work) == "ACTIVE" else ())
        unsafe_work["rule_forgotten_ranks"] = len(forgotten)
        rule = ForgettingRule(horizon, forgotten, {}, dict(unsafe_work), certified=False)
    else:
        rule = ForgettingRule(horizon, (), {}, {})
    work = Counter(rule.counts)
    work["root_tiles_encoded"] = 16
    work["root_tiles_forgotten"] = sum(rank in rule.forgotten_ranks for rank in board)
    root_board = tuple(ANONYMOUS if rank in rule.forgotten_ranks else rank for rank in board)
    state_index: dict[StateKey, int] = {}
    boards: dict[int, tuple[int, ...]] = {}
    layers: dict[int, int] = {}
    statuses: dict[int, str] = {}
    queue = []
    rows = {}

    def register(symbolic: tuple[int, ...], remaining: int) -> int:
        active_key = (remaining, symbolic)
        if active_key in state_index:
            work["existing_active_state_visits"] += 1
            return state_index[active_key]
        status, moves = _classify(symbolic, work)
        if status == "ACTIVE" and remaining == 0:
            status = "CUTOFF"
        key = active_key if status == "ACTIVE" else (remaining, status)
        if key in state_index:
            work["existing_terminal_state_visits"] += 1
            return state_index[key]
        if len(state_index) >= max_states:
            raise ValueError(f"complete symbolic model exceeds max_states={max_states}")
        state_id = len(state_index)
        state_index[key] = state_id
        layers[state_id] = remaining
        statuses[state_id] = status
        if status == "ACTIVE":
            boards[state_id] = symbolic
            queue.append((state_id, remaining, moves))
        return state_id

    root = register(root_board, horizon)
    for state_id, remaining, moves in queue:
        for action, moved, score in moves:
            moved = tuple(ANONYMOUS if rank in rule.forgotten_ranks else rank for rank in moved)
            empties = [cell for cell, rank in enumerate(moved) if rank == 0]
            mass = defaultdict(list)
            for cell in empties:
                for rank, spawn_probability in ((1, 0.9), (2, 0.1)):
                    successor = list(moved)
                    successor[cell] = ANONYMOUS if rank in rule.forgotten_ranks else rank
                    target = register(tuple(successor), remaining - 1)
                    mass[target].append(spawn_probability / len(empties))
                    work["spawn_support_entries"] += 1
            rows[state_id, action] = tuple(
                Outcome(math.fsum(parts), target, score / 2048.0)
                for target, parts in sorted(mass.items())
            )
            work["model_transition_rows"] += 1
            work["model_successor_entries"] += len(mass)
    model = FiniteModel(layers, statuses, rows, (root,))
    work["registered_states"] = len(layers)
    work["active_states"] = len(boards)
    work["terminal_states"] = len(layers) - len(boards)
    work["coalesced_outcomes"] = work["spawn_support_entries"] - work["model_successor_entries"]
    return Build(model, boards, state_index, rule, dict(work), perf_counter() - started)
