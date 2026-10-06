"""Observed regime evidence and unchanged sampled-game semantics."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_lifelong_experience_v77 as old
from acfqp.science import controlled_predictive_regime_experience_v115 as module

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    patch = pytest.MonkeyPatch()
    for target in (old, module):
        original = target._spawn
        def spawn(*args, _spawn=original, **kwargs):
            result = _spawn(*args, **kwargs)
            WORK['environment_spawns'] += 1
            WORK['environment_random_draws'] += 2
            return result
        patch.setattr(target, '_spawn', spawn)
    yield
    patch.undo()
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_regime_experience_v115.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        development_work=dict(WORK),
        newly_sampled_environment_transitions=WORK['sampled_transitions'],
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='bounded real development episodes; no production sampling'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def actor(board, _index):
    return ground.legal_actions_v1(board)[0].value


def episode(function, *args, **kwargs):
    WORK['started_episode_calls'] += 1
    result = function(*args, **kwargs)
    WORK['completed_episode_calls'] += 1
    WORK['sampled_transitions'] += result['work'].get('sampled_transitions', 0)
    return result


def test_standard_probability_reproduces_v77_trajectory_and_work_exactly():
    baseline = episode(old.run_episode, 115001, actor, max_steps=12)
    candidate = episode(module.run_episode, 115001, actor, .1, max_steps=12)
    baseline.pop('seconds')
    candidate.pop('seconds')
    assert candidate == baseline
    assert candidate['status'] == 'CUTOFF' and candidate['steps_count'] == 12
    assert all(module.observed_rank(step) == step['spawned_rank'] for step in candidate['steps'])


@pytest.mark.parametrize('probability,rank', [(0.0, 1), (1.0, 2)])
def test_regime_boundaries_change_only_spawns_with_legal_observation(probability, rank):
    result = episode(module.run_episode, 115002, actor, probability, max_steps=8)
    assert result['status'] == 'CUTOFF' and result['steps_count'] == 8
    assert all(row['rank'] == rank for row in result['initial_spawns'])
    assert all(module.observed_rank(step) == rank for step in result['steps'])
    for step in result['steps']:
        after, score, changed = ground.swipe_board_v1(
            tuple(step['board']), ground.Swipe2048Action(step['action']))
        assert changed and list(after) == step['afterstate'] and score == step['score']
    assert result['work']['environment_random_draws'] == 20


def test_observed_rank_uses_only_two_boards_and_ignores_hidden_metadata():
    before = [1, 0] + [0] * 14
    after = [1, 2] + [0] * 14
    assert module.observed_rank(dict(afterstate=before, next_board=after)) == 2
    assert module.observed_rank(dict(afterstate=before, next_board=after,
        p_four=0, seed=1, spawned_rank=1, spawned_cell=15)) == 2


def test_observation_rejects_missing_multiple_and_non_spawn_changes():
    before = [1] + [0] * 15
    for after in (before, [1, 1, 2] + [0] * 13, [2] + [0] * 15, [1, 3] + [0] * 14):
        with pytest.raises(ValueError, match='spawn observation'):
            module.observed_rank(dict(afterstate=before, next_board=after))


def test_illegal_action_is_not_replaced():
    with pytest.raises(ValueError):
        episode(module.run_episode, 115003, lambda board, index: 'NOT_AN_ACTION', .1, max_steps=1)


def test_invalid_configuration_fails_before_any_sampling():
    previous = WORK['environment_spawns']
    for probability, max_steps in [(-.1, 1), (1.1, 1), (.1, 0)]:
        with pytest.raises(ValueError):
            module.run_episode(115004, actor, probability, max_steps=max_steps)
    assert WORK['environment_spawns'] == previous
