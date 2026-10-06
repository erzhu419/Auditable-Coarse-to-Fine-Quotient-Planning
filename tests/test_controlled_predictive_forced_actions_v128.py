"""Shared-prefix and forced-policy tests using deterministic scripted spawns."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_forced_actions_v128 as core
from acfqp.science.controlled_predictive_anchored_success_v127 import AnchoredSuccess
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_forced_actions_v128_build'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = [1, 1, 0, 0] + [0] * 12
MODELS, SOURCES, GAMES = [], [], []
PREFIX_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_forced_actions_v128.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    work = sum((Counter(g['work']) for g in GAMES), Counter())
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, prefix_work=dict(PREFIX_WORK), scripted_game_work=dict(work),
        core_work=dict(sum((m.counts for m in MODELS), Counter())),
        source_work=dict(sum((m.counts for m in SOURCES), Counter())),
        setup_counts=dict(sum((m.setup_counts for m in MODELS + SOURCES), Counter())),
        newly_sampled_environment_transitions=0, environment_random_draws=0,
        scripted_transitions=work['sampled_transitions'],
        scope='All test spawns scripted; ground swipes/status checks are deterministic, no random environment draw.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def rule(radix=11):
    return LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', radix)


def traces():
    final = [2, 0, 0, 1] + [0] * 10 + [2, 0]
    left = dict(seed=15, initial_board=BOARD, actions=['LEFT', 'UP'],
        scores=[4, 0], spawned_cells=[15, 14], spawned_ranks=[1, 2], final_board=final)
    right = deepcopy(left); right['actions'][1] = 'RIGHT'
    return left, right


def prefix(left, right):
    result = core.board_at_first_divergence(left, right, rule())
    PREFIX_WORK.update(result['counts'])
    return result


def test_first_divergence_returns_pre_action_board_after_shared_spawn():
    left, right = traces(); result = prefix(left, right)
    assert result['diverged'] and result['index'] == 1
    assert result['board'] == [2] + [0] * 14 + [1]
    assert result['left_action'] == 'UP' and result['right_action'] == 'RIGHT'
    assert result['counts'] == dict(learned_swipe_calls=1, learned_line_rewrites=4, recorded_spawns_replayed=1)


def test_initial_divergence_needs_no_replay_and_no_change_returns_full_prefix():
    left, right = traces(); right['actions'][0] = 'DOWN'
    result = prefix(left, right)
    assert result['index'] == 0 and result['board'] == BOARD and result['counts'] == {}
    result = prefix(left, deepcopy(left))
    assert not result['diverged'] and result['board'] is None
    assert result['shared_prefix_steps'] == 2 and result['counts']['learned_swipe_calls'] == 2


def test_unpaired_or_inconsistent_common_prefix_is_rejected():
    left, right = traces(); right['seed'] += 1
    with pytest.raises(ValueError, match='share seed'): prefix(left, right)
    right = deepcopy(left); right['scores'][0] = 8
    with pytest.raises(ValueError, match='different score or spawn'): prefix(left, right)


class FixedSource:
    def __init__(self, action='UP'):
        self.counts = Counter(); self.updates = 72; self.action = action; self.queries = []
    def choose(self, board, query):
        self.counts['choose_calls'] += 1; self.queries.append(query)
        return dict(action=self.action)


def scripted(monkeypatch, pairs):
    choices = iter(pairs)
    def spawn(board, rng, work, p_four):
        assert p_four == .1
        cell, rank = next(choices)
        assert board[cell] == 0
        out = list(board); out[cell] = rank
        work['scripted_spawns'] += 1
        return tuple(out), cell, rank
    monkeypatch.setattr(core, '_spawn', spawn)


def test_forced_winning_action_still_spawns_without_calling_source(monkeypatch):
    scripted(monkeypatch, [(15, 1)]); actor = FixedSource()
    game = core.run_forced_continuation([10, 10] + [0] * 14, 'LEFT', actor, QUERY, 12)
    GAMES.append(game)
    assert game['status'] == 'WON' and game['return_score'] == 2048
    assert game['steps_count'] == 1 and game['final_board'][15] == 1
    assert game['initial_spawns'] == [] and game['work']['forced_actions'] == 1
    assert game['policy_counts'] == {} and actor.updates == 72


def test_forced_loss_counts_one_transition_and_never_bootstraps(monkeypatch):
    scripted(monkeypatch, [(3, 2)]); actor = FixedSource()
    board = [0, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    game = core.run_forced_continuation(board, 'LEFT', actor, QUERY, 13)
    GAMES.append(game)
    assert game['status'] == 'LOST' and game['steps_count'] == 1
    assert game['return_score'] == 0 and game['work']['sampled_transitions'] == 1
    assert not game['policy_counts']


def test_only_first_action_forced_then_original_query_policy_and_cutoff(monkeypatch):
    scripted(monkeypatch, [(15, 1), (14, 2)]); actor = FixedSource('UP')
    game = core.run_forced_continuation(BOARD, 'LEFT', actor, QUERY, 14, max_steps=2)
    GAMES.append(game)
    assert [step['action'] for step in game['steps']] == ['LEFT', 'UP']
    assert game['return_score'] == 4 and game['status'] == 'CUTOFF'
    assert game['policy_counts']['choose_calls'] == game['steps_count'] - 1
    assert actor.queries == [QUERY]
    assert game['source_updates_before'] == game['source_updates_after'] == 72


def test_count_checkpoint_load_preserves_predictions_and_only_charges_new_load():
    source = NtupleValue(rule(4), BUILD); SOURCES.append(source)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 9 * .001
    original = AnchoredSuccess(source, QUERY, BUILD); MODELS.append(original)
    original.train_episode([BOARD, [4] + [0] * 15], 'WON')
    original.train_episode([[2, 0, 1, 0] + [0] * 12], 'LOST')
    path = BUILD / 'load_fixture.npz'; saved = original.save(path)
    expected = original.probabilities([BOARD])
    loaded = core.load_anchored_success(path, source, QUERY, BUILD); MODELS.append(loaded)
    assert loaded.probabilities([BOARD]) == expected
    assert loaded.updates == 2 and loaded.successes == 1
    assert loaded.loaded_metadata['updates'] == 2
    assert loaded.load_counts == dict(checkpoint_loads=1, checkpoint_loaded_addresses=saved['nonzero_addresses'],
                                     checkpoint_loaded_count_entries=2 * saved['nonzero_addresses'])
    assert loaded.counts['success_observation_updates'] == 0
    assert not loaded.visits.flags.writeable and not loaded.wins.flags.writeable
    assert not loaded.source.weights.flags.writeable
    with pytest.raises(ValueError, match='does not match'):
        core.load_anchored_success(path, source, dict(reward_weight=1., failure_penalty=0., goal_bonus=0.), BUILD)
