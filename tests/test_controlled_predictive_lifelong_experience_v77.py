"""Natural sampling and observed-label semantics; three bounded development tests."""
from collections import Counter
import json
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_lifelong_experience_v77 import run_episode, targets


LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def count_development_ground():
    patch = pytest.MonkeyPatch()
    for name in ("swipe_board_v1", "state_from_board_v1", "step_v1"):
        original = getattr(ground, name)

        def counted(*args, _function=original, _name=name, **kwargs):
            LEDGER[_name] += 1
            return _function(*args, **kwargs)

        patch.setattr(ground, name, counted)
    yield
    patch.undo()
    print("V77_EXPERIENCE_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


def test_natural_start_and_sampled_transition_matches_one_exact_ground_row():
    def actor(board, _):
        return ground.legal_actions_v1(board)[0].value

    episode = run_episode(7701, actor, max_steps=1)
    LEDGER["sampled_episode_calls"] += 1
    LEDGER["sampled_transitions"] += episode["work"]["sampled_transitions"]
    initial = tuple(episode["initial_board"])
    assert len([rank for rank in initial if rank]) == 2
    assert all(rank in (0, 1, 2) for rank in initial)
    assert episode["status"] == "CUTOFF"
    assert episode["work"] == dict(
        environment_random_draws=6, initial_spawns=2,
        ground_state_status_calls=2, ground_status_internal_swipe_calls=8,
        ground_swipe_calls=9, ground_explicit_swipe_calls=1, sampled_transitions=1,
    )
    # Independently replay exactly two cell/rank draws for each initial/action spawn.
    rng, replay = random.Random(7701), [0] * 16
    for _ in range(2):
        empty = [i for i, rank in enumerate(replay) if not rank]
        cell, rank = empty[int(rng.random() * len(empty))], 1 if rng.random() < 0.9 else 2
        replay[cell] = rank
    assert replay == list(initial)
    step = episode["steps"][0]
    empty = [i for i, rank in enumerate(step["afterstate"]) if not rank]
    assert step["spawned_cell"] == empty[int(rng.random() * len(empty))]
    assert step["spawned_rank"] == (1 if rng.random() < 0.9 else 2)
    state = ground.state_from_board_v1(initial)
    rows = ground.step_v1(state, ground.Swipe2048Action(step["action"]))
    LEDGER["enumerated_teacher_outcomes"] += len(rows)
    matches = [row for row in rows if list(row.next_state.board) == step["next_board"]]
    assert len(matches) == 1
    assert matches[0].merge_score == step["score"]
    assert matches[0].next_state.status.value == step["status"]


def test_mc_excludes_anchor_score_and_counts_terminal_event_once():
    episode = dict(status="WON", steps=[
        dict(afterstate=[1] * 16, score=2048, status="ACTIVE"),
        dict(afterstate=[2] * 16, score=4096, status="ACTIVE"),
        dict(afterstate=[3] * 16, score=8192, status="WON"),
    ])
    records = targets(episode, "fixed_policy", 7, stride=2, horizons=(1, 2, 30))
    by_anchor_h = {(row["anchor_step"], row["horizon"]): row for row in records}
    assert by_anchor_h[0, 1]["target"] == [2.0, 0.0, 0.0]
    assert by_anchor_h[0, 2]["target"] == [6.0, 0.0, 1.0]
    assert by_anchor_h[0, 30]["target"] == [6.0, 0.0, 1.0]
    assert all(by_anchor_h[2, h]["target"] == [0.0, 0.0, 1.0] for h in (1, 2, 30))
    assert all(row["policy"] == "fixed_policy" and row["episode"] == 7 for row in records)
    # The final action is retained even when it falls outside the regular stride.
    sparse = targets(episode, "fixed_policy", 7, stride=4, horizons=(2,))
    assert [row["anchor_step"] for row in sparse] == [0, 2]


def test_cutoff_omits_incomplete_windows_without_fabricating_failure():
    episode = dict(status="CUTOFF", steps=[
        dict(afterstate=[i] * 16, score=2048, status="ACTIVE") for i in range(4)
    ])
    records = targets(episode, "fixed_policy", 9, stride=1, horizons=(2, 30))
    assert [(row["anchor_step"], row["horizon"]) for row in records] == [(0, 2), (1, 2)]
    assert all(row["target"] == [2.0, 0.0, 0.0] for row in records)
    lost = dict(status="LOST", steps=[dict(afterstate=[1] * 16, score=2048, status="LOST")])
    assert targets(lost, "fixed_policy", 10)[0]["target"] == [0.0, 1.0, 0.0]
