"""Finite actual-board receipts test timing; native math is tested separately."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import online_episode_stream_v292 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from test_retained_actor_data_v287 import game_events


class Head:
    def __init__(self, parent=None, kind=None, runtime=None):
        self.parent = parent or self
        self.weights = np.array([3. if parent is None else parent.weights[0]])
        self.radix, self.updates, self.counts = 11, 0, Counter()
        self.setup_counts = Counter(source_parameters_copied=1, source_weight_bytes_copied=8)
        self.setup_seconds = 0.

    def freeze(self):
        self.weights.flags.writeable = False


class Stream:
    instances = []

    def __init__(self, template, seed, runtime, max_steps):
        self.max_steps, self.event_index, self.closed = max_steps, 0, False
        self.events = game_events()[0]
        self.current = dict(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
            episode=-1, step=0, return_score=0, status='NOT_STARTED', initial_count=0,
            raw_tiles=0, post_action_spawns=0, game_start_raw=0, stream_seed=seed, random_draw_position=0)
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.setup_counts, self.setup_seconds, self.calls, self.evaluations = Counter(), 0., [], []
        self.instances.append(self)

    def state(self):
        return deepcopy(self.current)

    def advance(self, leaf, bank, pending, p, env_p, tile_budget, max_postaction, depth, stop_on_game_end):
        assert not leaf.weights.flags.writeable and stop_on_game_end and bank == 0
        start, raw, actions, scores, completed = self.state(), [], [], [], []
        self.calls.append(dict(start=start, weight=float(leaf.weights[0]), depth=depth,
            quota=tile_budget, p=p, env_p=env_p, head_updates=leaf.updates))
        state = self.current
        while len(raw) < tile_budget and len(actions) < max_postaction:
            if state['status'] not in ('ACTIVE', 'INITIALIZING'):
                state.update(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
                    episode=state['episode']+1, step=0, return_score=0, status='INITIALIZING',
                    initial_count=0, game_start_raw=state['raw_tiles'])
                self.event_index = 0
            spawn, action, score = self.events[self.event_index]
            self.event_index += 1
            spawn = dict(spawn, episode=state['episode'])
            raw.append(spawn)
            if action is None:
                state['initial_count'] += 1
                state['board'][spawn['cell']] = spawn['rank']
                if state['initial_count'] == 2:
                    state['status'] = 'ACTIVE'
            else:
                after, actual, changed = ground.swipe_board_v1(tuple(state['board']), ground.Swipe2048Action(action))
                assert changed and actual == score
                actions.append(action); scores.append(score)
                state['board'] = list(after)
                state['board'][spawn['cell']] = spawn['rank']
                state['step'] += 1
                state['return_score'] += score
                state['post_action_spawns'] += 1
                state['status'] = ground.state_from_board_v1(tuple(state['board'])).status.value
                if state['status'] == 'ACTIVE' and state['step'] == self.max_steps:
                    state['status'] = 'CUTOFF'
                state['pending_afterstate'] = list(after) if state['status'] == 'ACTIVE' else None
                state['pending_bank_id'] = 0 if state['status'] == 'ACTIVE' else None
            state['raw_tiles'] += 1
            state['random_draw_position'] += 2
            if state['status'] in ('WON', 'LOST', 'CUTOFF'):
                completed.append(dict(episode=state['episode'], stream_seed=state['stream_seed'],
                    start_raw=state['game_start_raw'], end_raw=state['raw_tiles'], steps=state['step'],
                    score=state['return_score'], status=state['status']))
                break
        work = dict(environment=dict(raw_tile_productions=len(raw),
            initial_spawns=sum(spawn['kind'] == 'INITIAL' for spawn in raw),
            sampled_transitions=len(actions), environment_random_draws=2*len(raw)),
            planning=dict(choose_calls=len(actions)), learning={})
        for kind, value in work.items():
            self.counts[kind].update(value)
        return dict(start=start, end=self.state(), raw_spawns=raw, actions=actions, scores=scores,
                    completed_games=completed, counts=work, updates=[], seconds=0., cpu_seconds=0.)

    def evaluate_games(self, leaf, p, env_p, seeds, depth, max_steps):
        assert not leaf.weights.flags.writeable
        self.evaluations.append(dict(weight=float(leaf.weights[0]), p=p, env_p=env_p,
                                     seeds=list(seeds), depth=depth, updates=leaf.updates))
        return dict(game_summaries=[dict(seed=seed, utility=float(leaf.weights[0]), status='LOST', steps=1)
            for seed in seeds], counts=dict(environment=dict(sampled_transitions=len(seeds),
            initial_spawns=2*len(seeds), raw_tile_productions=3*len(seeds)),
            planning=dict(choose_calls=len(seeds))), seconds=0., cpu_seconds=0.)

    def close(self):
        self.closed = True


def setup(monkeypatch, budget=None):
    captures = []
    monkeypatch.setattr(core, 'QueryTD', Head)
    monkeypatch.setattr(core, 'NativeValueStream', Stream)
    monkeypatch.setattr(core, 'RAW_TILES_PER_PHASE', budget or (len(game_events()[0])//2+1))
    monkeypatch.setattr(core, 'EVALUATION_GAMES', 2)

    def fit(leaf, data, method, runtime, alpha):
        assert leaf.weights.flags.writeable and alpha == .0025
        n = len(data['rewards'])
        captures.append(dict(method=method, dataset=deepcopy(data), old_updates=leaf.updates,
                             old_weight=float(leaf.weights[0])))
        leaf.weights[0] += 10.
        leaf.updates += n
        sample = dict(episode=0, step=0, target=4., raw_target=4., error=1., raw_prediction_before_update=3.)
        return dict(method=method, alpha=alpha, fitted_games=1, fitted_steps=n, trained_afterstates=n,
            learning_counts=dict(td_updates=n, table_updates=n), target_counts=dict(target_suffix_accumulations=n),
            consolidation_counts=dict(game_parameter_commits=1, native_buffer_bytes_peak=n),
            setup_counts={}, first_sample=sample, last_sample=dict(sample, step=n-1), seconds=0., cpu_seconds=0.)
    monkeypatch.setattr(core, 'fit_consolidated', fit)
    warmed = SpawnMemory('LIBRARY')
    for _ in range(256):
        warmed.observe(2)
    source = Head(); source.freeze()
    return source, warmed, captures


def test_mixed_phase_whole_game_is_fitted_before_next_initialization(monkeypatch, tmp_path):
    source, warmed, captures = setup(monkeypatch)
    old_memory, records = warmed.to_payload(), []
    result = core.run_arm(source, warmed, 0, 'MEAN_H2', records.append, tmp_path)
    assert len(captures) == 1
    steps = len(game_events()[0])-2
    data = captures[0]['dataset']
    assert data['fit_step_end'] == steps and data['terminal_codes'].tolist() == [-1]
    assert data['rewards'].tolist() == [score/2048. for _, action, score in game_events()[0] if action is not None]
    assert result['phases']['A']['snapshot']['value_updates'] == 0
    assert result['phases']['B']['snapshot']['value_updates'] == steps
    assert result['phases']['A']['snapshot']['unfinished_game']['steps'] > 0
    fit_index = next(i for i, row in enumerate(records) if row['kind'] == 'GAME_FIT')
    terminal, fit = records[fit_index-1], records[fit_index]
    assert terminal['kind'] == 'TRAIN' and terminal['completed_games'][0]['end_raw'] == len(game_events()[0])
    assert fit['phase'] == 'B' and fit['fit']['first_sample']['global_raw_before_action'] == 2
    assert fit['fit']['last_sample']['global_raw_before_action'] == steps+1
    next_train = next(row for row in records[fit_index+1:] if row['kind'] == 'TRAIN')
    assert next_train['start']['episode'] == 0 and next_train['start']['status'] == 'LOST'
    assert next_train['leaf_updates_before'] == steps
    calls = Stream.instances[-1].calls
    assert next(call for call in calls if call['start']['status'] == 'LOST')['weight'] == 13.
    assert any(call['env_p'] == .1 for call in calls) and any(call['env_p'] == .5 for call in calls)
    assert result['final_unfitted_game']['steps'] > 0
    assert result['fit_totals']['trained_afterstates'] == steps
    assert result['final_memory']['observations_seen'] == 256+3*core.RAW_TILES_PER_PHASE
    assert source.updates == 0 and source.weights.tolist() == [3.] and warmed.to_payload() == old_memory
    assert Stream.instances[-1].closed


def test_retention_uses_saved_A_belief_and_A_head_on_B_uses_current_B_belief(monkeypatch, tmp_path):
    source, warmed, _ = setup(monkeypatch)
    result = core.run_arm(source, warmed, 3, 'MEAN_H2', lambda row: None, tmp_path)
    a, b, returned = (result['phases'][phase] for phase, _ in core.PHASES)
    assert a['retention_probe']['shared_with_current']
    assert a['retention_probe']['game_summaries'] == a['game_summaries']
    assert a['retention_probe']['counts'] == {'environment': {}, 'planning': {}}
    assert b['retention_probe']['model_p_four'] == returned['retention_probe']['model_p_four'] == a['snapshot']['estimated_p_four']
    a_seeds = [core.evaluation_seed(3, 0, e) for e in range(2)]
    assert [game['seed'] for game in b['retention_probe']['game_summaries']] == a_seeds
    probe = b['a_head_on_B']
    assert probe['model_p_four'] == b['snapshot']['estimated_p_four']
    assert probe['environment_p_four'] == .5
    assert [game['seed'] for game in probe['game_summaries']] == [game['seed'] for game in b['game_summaries']]
    assert probe['game_summaries'][0]['utility'] == 3.
    assert b['game_summaries'][0]['utility'] == 13.
    assert result['retained_A_head_setup']['setup_counts']['source_weight_bytes_copied'] == 8
    assert result['retained_A_head_setup']['setup_counts']['retained_A_weight_bytes_copied'] == 8
    assert result['evaluation_counts']['environment']['sampled_transitions'] == 6
    assert result['retention_evaluation_counts']['environment']['sampled_transitions'] == 4
    assert result['a_head_on_B_evaluation_counts']['environment']['sampled_transitions'] == 2
    assert len(Stream.instances[-1].evaluations) == 6


@pytest.mark.parametrize('arm,method,depth', [('FROZEN_H2', None, 2), ('FROZEN_DIRECT', None, 1),
    ('NSEQ_H2', 'NORMALIZED_SEQUENTIAL_MC', 2), ('MEAN_DIRECT', 'EPISODE_MEAN_MC', 1)])
def test_all_fixed_arms_have_readonly_actor_and_appropriate_fit_permission(monkeypatch, tmp_path, arm, method, depth):
    source, warmed, captures = setup(monkeypatch)
    result = core.run_arm(source, warmed, 1, arm, lambda row: None, tmp_path)
    assert all(call['depth'] == depth for call in Stream.instances[-1].calls)
    assert len(captures) == int(method is not None)
    if method is None:
        assert result['fit_totals']['trained_afterstates'] == 0
        assert result['costs']['retained_afterstate_steps_peak'] == 0
    else:
        assert captures[0]['method'] == method
    assert result['retained_A_head_setup'] is None
    assert not any('a_head_on_B' in phase for phase in result['phases'].values())


def test_cutoff_is_paid_and_skipped_without_false_MC_terminal(monkeypatch, tmp_path):
    source, warmed, captures = setup(monkeypatch, budget=5)
    monkeypatch.setattr(core, 'MAX_STEPS', 3)
    records = []
    result = core.run_arm(source, warmed, 0, 'MEAN_H2', records.append, tmp_path)
    assert result['cutoff_games'] == 3 and not captures
    assert result['fit_totals']['fitted_games'] == 0
    assert result['training_counts']['environment']['raw_tile_productions'] == 15
    assert result['final_unfitted_game']['raw_tiles'] == 0
    fits = [row for row in records if row['kind'] == 'GAME_FIT']
    assert all(not row['fitted'] and row['fit']['method'] == 'SKIPPED_CUTOFF' for row in fits)
    assert all(phase['training']['cutoff_games'] == 1 for phase in result['phases'].values())
