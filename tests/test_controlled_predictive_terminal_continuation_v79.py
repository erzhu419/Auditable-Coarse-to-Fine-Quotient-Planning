"""Exact stream continuation and suffix-only environment accounting."""
from collections import Counter
import json

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_terminal_continuation_v79 import extend_episode


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
    print("V79_TERMINAL_CONTINUATION_DEVELOPMENT_WORK=" +
          json.dumps(dict(LEDGER), sort_keys=True))


def sample(*args, **kwargs):
    episode = rollout_from_board(*args, **kwargs)
    LEDGER["sampled_rollout_calls"] += 1
    LEDGER.update({key: episode["work"].get(key, 0) for key in
                   ("sampled_transitions", "environment_random_draws", "initial_spawns")})
    return episode


def extend(*args, **kwargs):
    result = extend_episode(*args, **kwargs)
    LEDGER["continuation_calls"] += 1
    LEDGER["restoration_random_draws"] += result["restoration_random_draws"]
    LEDGER.update({key: result["suffix"]["work"].get(key, 0) for key in
                   ("sampled_transitions", "environment_random_draws", "initial_spawns")})
    return result


def fixed_policy(board, index):
    actions = ground.legal_actions_v1(board)
    return actions[index % len(actions)].value


def forbidden_action(*_):
    raise AssertionError("terminal or exhausted prefixes must not invoke the policy")


def test_prefix_plus_suffix_exactly_matches_one_uninterrupted_rollout():
    board, seed = (1, 1) + (0,) * 14, 7901
    full = sample(board, seed, fixed_policy, max_steps=12)
    prefix = sample(board, seed, fixed_policy, max_steps=5)
    prefix_copy = json.loads(json.dumps(prefix))
    callback_indices = []

    def continuation_policy(current, index):
        callback_indices.append(index)
        return fixed_policy(current, index)

    result = extend(prefix, continuation_policy, max_total_steps=12)
    suffix = result["suffix"]
    assert prefix == prefix_copy
    assert prefix["steps"] == full["steps"][:5]
    assert suffix["steps"] == full["steps"][5:]
    assert prefix["steps"] + suffix["steps"] == full["steps"]
    assert callback_indices == list(range(5, 12))
    assert suffix["initial_board"] == prefix["final_board"]
    assert suffix["initial_spawns"] == []
    assert suffix["final_board"] == full["final_board"]
    assert result["total_score"] == full["return_score"]
    assert result["total_steps"] == full["steps_count"]
    assert result["status"] == suffix["status"] == full["status"]
    assert Counter(prefix["work"]) + Counter(suffix["work"]) == Counter(full["work"])
    assert result["resumed"] is True
    assert result["restoration_random_draws"] == 10
    assert suffix["work"]["environment_random_draws"] == 14
    assert suffix["work"]["sampled_transitions"] == 7
    assert suffix["work"]["ground_state_status_calls"] == 7


@pytest.mark.parametrize("board,action,status", [
    ((10, 10) + (0,) * 14, "LEFT", "WON"),
    ((3, 4, 5, 0, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9, 10), "RIGHT", "LOST"),
])
def test_true_terminal_prefix_needs_no_new_environment_or_rng_work(board, action, status):
    prefix = sample(board, 7902, lambda *_: action, max_steps=1)
    assert prefix["status"] == status
    old_ground_counts = {name: LEDGER[name] for name in
                         ("swipe_board_v1", "state_from_board_v1", "step_v1")}
    result = extend(prefix, forbidden_action, max_total_steps=2000)
    assert result["resumed"] is False
    assert result["status"] == status
    assert result["total_steps"] == prefix["steps_count"]
    assert result["total_score"] == prefix["return_score"]
    assert result["restoration_random_draws"] == 0
    assert result["suffix"]["work"] == {}
    assert result["suffix"]["steps"] == []
    assert result["suffix"]["return_score"] == 0
    assert all(LEDGER[name] == count for name, count in old_ground_counts.items())


def test_cap_preserves_unknown_terminal_outcome_and_can_later_resume():
    prefix = sample((1, 1) + (0,) * 14, 7904, fixed_policy, max_steps=2)
    assert prefix["status"] == "CUTOFF"
    old_ground_counts = {name: LEDGER[name] for name in
                         ("swipe_board_v1", "state_from_board_v1", "step_v1")}
    exhausted = extend(prefix, forbidden_action, max_total_steps=2)
    assert exhausted["status"] == "CUTOFF"
    assert exhausted["resumed"] is False
    assert exhausted["suffix"]["work"] == {}
    assert exhausted["restoration_random_draws"] == 0
    assert all(LEDGER[name] == count for name, count in old_ground_counts.items())
    extended = extend(prefix, fixed_policy, max_total_steps=4)
    assert extended["status"] == "CUTOFF"
    assert extended["total_steps"] == 4
    assert extended["suffix"]["steps_count"] == 2
    assert extended["suffix"]["steps"][-1]["status"] == "ACTIVE"
    assert extended["restoration_random_draws"] == 4
    assert extended["suffix"]["work"]["environment_random_draws"] == 4


def test_illegal_continuation_reports_the_absolute_action_index():
    # Seed 1 places the new tile in the top row: UP then changes nothing.
    prefix = sample((1, 1) + (0,) * 14, 1, lambda *_: "LEFT", max_steps=1)
    with pytest.raises(ValueError, match="illegal action UP at step 1"):
        extend_episode(prefix, lambda *_: "UP", max_total_steps=2)
    LEDGER["rejected_illegal_continuation_calls"] += 1
    LEDGER["restoration_random_draws"] += prefix["work"]["environment_random_draws"]
