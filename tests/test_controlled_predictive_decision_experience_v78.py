"""Bounded ground checks for paired counterfactual experience."""
from collections import Counter
import json
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_lifelong_experience_v77 import targets


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
    print("V78_DECISION_EXPERIENCE_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


def sample(*args, **kwargs):
    episode = rollout_from_board(*args, **kwargs)
    LEDGER["sampled_rollout_calls"] += 1
    LEDGER.update({key: episode["work"].get(key, 0) for key in
                   ("sampled_transitions", "environment_random_draws", "initial_spawns")})
    return episode


def test_true_terminal_stops_and_anchor_targets_exclude_forced_action_reward():
    board = (10, 10) + (0,) * 14
    episode = sample(board, 7801, lambda _, index: "LEFT", max_steps=32)
    assert episode["initial_board"] == list(board)
    assert episode["initial_spawns"] == []
    assert episode["status"] == "WON"
    assert episode["steps_count"] == 1
    assert episode["return_score"] == 2048
    assert episode["work"]["sampled_transitions"] == 1
    assert episode["work"]["environment_random_draws"] == 2
    assert episode["work"].get("initial_spawns", 0) == 0
    records = [row for row in targets(episode, "GREEDY", 7, stride=1000)
               if row["anchor_step"] == 0]
    assert [row["horizon"] for row in records] == [30, 31]
    assert all(row["target"] == [0.0, 0.0, 1.0] for row in records)


def test_paired_random_numbers_survive_different_first_actions():
    board, seed = (1, 1) + (0,) * 14, 7802

    def actor(first_action):
        return lambda current, index: (first_action if index == 0 else
                                       ground.legal_actions_v1(current)[0].value)

    left = sample(board, seed, actor("LEFT"), max_steps=2)
    duplicate = sample(board, seed, actor("LEFT"), max_steps=2)
    right = sample(board, seed, actor("RIGHT"), max_steps=2)
    assert left["steps"] == duplicate["steps"]
    assert left["steps"][0]["afterstate"] != right["steps"][0]["afterstate"]
    for episode in (left, duplicate, right):
        assert episode["status"] == "CUTOFF"
        assert episode["work"]["environment_random_draws"] == 4
        rng = random.Random(seed)
        for step in episode["steps"]:
            empty = [cell for cell, rank in enumerate(step["afterstate"]) if rank == 0]
            expected_cell = empty[int(rng.random() * len(empty))]
            expected_rank = 1 if rng.random() < 0.9 else 2
            assert (step["spawned_cell"], step["spawned_rank"]) == (expected_cell, expected_rank)
        # No complete 30/31-step target may be fabricated from this short prefix.
        assert targets(episode, "SPACE", 8, stride=1000) == []


def test_illegal_action_raises_without_silently_substituting_an_action():
    with pytest.raises(ValueError, match="illegal action LEFT at step 0"):
        rollout_from_board((1,) + (0,) * 15, 7803, lambda _, index: "LEFT", max_steps=1)
    LEDGER["rejected_illegal_rollout_calls"] += 1
