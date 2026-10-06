"""Sampled natural 2048 episodes and observed, policy-conditioned consequences.

The environment draws one spawn per action.  It never enumerates the transition
support, and the consequence records never query the environment or a model.
"""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter
from typing import Callable

from acfqp.domains import standard_2048 as ground


def _spawn(board: tuple[int, ...], rng: random.Random, work: Counter):
    empty = [cell for cell, rank in enumerate(board) if rank == 0]
    cell_draw, rank_draw = rng.random(), rng.random()
    work["environment_random_draws"] += 2
    cell = empty[int(cell_draw * len(empty))]
    rank = 1 if rank_draw < 0.9 else 2
    result = list(board)
    result[cell] = rank
    return tuple(result), cell, rank


def _status(board: tuple[int, ...], work: Counter) -> str:
    work["ground_state_status_calls"] += 1
    # state_from_board_v1 checks every direction unless the goal is present.
    internal_swipes = 0 if max(board) >= ground.GOAL_RANK else 4
    work["ground_status_internal_swipe_calls"] += internal_swipes
    work["ground_swipe_calls"] += internal_swipes
    return ground.state_from_board_v1(board).status.value


def run_episode(
    seed: int,
    action_fn: Callable[[tuple[int, ...], int], str],
    max_steps: int = 2000,
) -> dict:
    """Play from two initial tiles, using a separate environment RNG.

    ``action_fn(board, step_index)`` returns one action name.  An illegal action
    fails the episode; it is never silently replaced.  Work counts cover this
    environment's calls, not computations performed inside ``action_fn``.
    """
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    started = perf_counter()
    rng, work = random.Random(seed), Counter()
    board = (0,) * 16
    initial_spawns = []
    for _ in range(2):
        board, cell, rank = _spawn(board, rng, work)
        initial_spawns.append(dict(cell=cell, rank=rank))
        work["initial_spawns"] += 1
    initial_board = board
    status = _status(board, work)
    steps, return_score = [], 0
    for index in range(max_steps):
        action = ground.Swipe2048Action(action_fn(board, index))
        work["ground_explicit_swipe_calls"] += 1
        work["ground_swipe_calls"] += 1
        afterstate, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f"illegal action {action.value} at step {index}")
        next_board, cell, rank = _spawn(afterstate, rng, work)
        work["sampled_transitions"] += 1
        status = _status(next_board, work)
        steps.append(dict(
            board=list(board), action=action.value, afterstate=list(afterstate),
            next_board=list(next_board), score=score, status=status,
            spawned_cell=cell, spawned_rank=rank,
        ))
        return_score += score
        board = next_board
        if status != "ACTIVE":
            break
    if status == "ACTIVE":
        status = "CUTOFF"
    return dict(
        seed=seed, initial_board=list(initial_board), initial_spawns=initial_spawns,
        final_board=list(board), status=status, return_score=return_score,
        steps_count=len(steps), steps=steps, work=dict(work),
        seconds=perf_counter() - started,
    )


def targets(
    episode: dict,
    policy: str,
    episode_index: int,
    stride: int = 4,
    horizons: tuple[int, ...] = (30, 31),
) -> list[dict]:
    """Return observed consequences starting immediately before the anchor spawn.

    R excludes the anchor action's score, then accumulates at most ``horizon``
    subsequent action scores divided by 2048.  F and S indicate the first terminal
    event from the anchor spawn through those actions.  Terminal trajectories
    absorb; a cutoff supplies no target whose observation window is incomplete.
    """
    if stride <= 0 or any(horizon < 0 for horizon in horizons):
        raise ValueError("stride must be positive and horizons nonnegative")
    steps = episode["steps"]
    if not steps:
        return []
    prefix = [0]
    for step in steps:
        prefix.append(prefix[-1] + step["score"])
    first_terminal = next(
        (index for index, step in enumerate(steps) if step["status"] in ("WON", "LOST")),
        None,
    )
    anchors = sorted(set(range(0, len(steps), stride)) | {len(steps) - 1})
    records = []
    for index in anchors:
        for horizon in horizons:
            last = index + horizon
            observed_terminal = first_terminal is not None and index <= first_terminal <= last
            if observed_terminal:
                last = first_terminal
                terminal_status = steps[last]["status"]
            elif last >= len(steps):
                continue
            else:
                terminal_status = "ACTIVE"
            reward = (prefix[last + 1] - prefix[index + 1]) / 2048.0
            records.append(dict(
                board=steps[index]["afterstate"], horizon=horizon, policy=policy,
                target=[reward, float(terminal_status == "LOST"), float(terminal_status == "WON")],
                episode=episode_index, anchor_step=index,
            ))
    return records
