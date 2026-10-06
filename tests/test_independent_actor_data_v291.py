"""Finite lawful standard-world receipts; no fresh environment sampling."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import independent_actor_data_v291 as core
from test_retained_actor_data_v287 import fixture, game_events


class FrozenTemplate:
    def __init__(self):
        self.weights = np.array([3.])
        self.weights.flags.writeable = False
        self.updates, self.counts = 99, Counter()

    def choose(self, board, query):
        self.counts['direct_choose_calls'] += 1
        choices = [(score, action.value) for action in ground.ACTION_ORDER
            for after, score, changed in [ground.swipe_board_v1(board, action)] if changed]
        return dict(action=min(choices)[1])


def retained_warmup(seed, policy, p_four, max_steps):
    events, final = game_events()
    board, steps = (0,)*16, []
    for spawn, action, score in events:
        if action is not None:
            assert policy(board, len(steps)) == action
            board, actual, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            assert actual == score and changed
            steps.append(dict(action=action, score=score,
                              spawned_cell=spawn['cell'], spawned_rank=spawn['rank']))
        board = list(board)
        board[spawn['cell']] = spawn['rank']
        board = tuple(board)
    return dict(initial_spawns=[dict(cell=spawn['cell'], rank=spawn['rank']) for spawn, _, _ in events[:2]],
        steps=steps, return_score=sum(step['score'] for step in steps), steps_count=len(steps),
        status='LOST', final_board=list(final),
        work=dict(initial_spawns=2, sampled_transitions=len(steps),
                  raw_tile_productions=len(events), environment_random_draws=2*len(events)))


class RetainedStream:
    instances, cutoff = [], False

    def __init__(self, template, seed, runtime, max_steps):
        rows, _, _, _ = fixture()
        self.receipts = deepcopy([row for row in rows if row['kind'] == 'TRAIN' and row['phase'] == 'A'])
        for receipt in self.receipts:
            for boundary in ('start', 'end'):
                receipt[boundary]['stream_seed'] = seed
            for game in receipt['completed_games']:
                game['stream_seed'] = seed
        if self.cutoff:
            first = next(row for row in self.receipts if row['completed_games'])
            first['completed_games'][0]['status'] = 'CUTOFF'
        self.current = deepcopy(self.receipts[0]['start'])
        self.cursor, self.calls, self.closed = 0, [], False
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.setup_counts, self.setup_seconds = Counter(native_setup=1), 0.
        self.instances.append(self)

    def state(self):
        return deepcopy(self.current)

    def advance(self, active, bank_id, pending, model_p, env_p, tile_budget, max_postaction):
        receipt = deepcopy(self.receipts[self.cursor])
        assert not active.weights.flags.writeable
        assert bank_id == 0 and env_p == .1 and max_postaction == 64
        assert model_p == receipt['model_p_four']
        assert tile_budget == len(receipt['raw_spawns'])
        assert self.current == receipt['start']
        self.calls.append(dict(tile_budget=tile_budget, pending=pending,
                               model_p=model_p, env_p=env_p))
        self.cursor += 1
        self.current = receipt['end']
        for kind, counts in receipt['counts'].items():
            self.counts[kind].update(counts)
        receipt.update(updates=[], seconds=0., cpu_seconds=0.)
        return receipt

    def close(self):
        self.closed = True


def prepare(monkeypatch):
    monkeypatch.setattr(core, 'run_episode', retained_warmup)
    monkeypatch.setattr(core, 'NativeValueStream', RetainedStream)
    monkeypatch.setattr(RetainedStream, 'cutoff', False)
    rows, _, _, _ = fixture()
    raw_budget = next(row['snapshot']['stream']['raw_tiles'] for row in rows if row['kind'] == 'EVALUATION')
    return raw_budget


def test_fresh_physical_acquisition_reconstructs_only_complete_chronological_games(monkeypatch, tmp_path):
    budget = prepare(monkeypatch)
    template, emitted = FrozenTemplate(), []
    result = core.acquire_dataset(template, 21, 1, emitted.append, tmp_path, raw_budget=budget)
    dataset, acquisition = result['dataset'], result['acquisition']
    assert len(dataset['games']) == 8 and dataset['fit_game_count'] == 6
    assert [game['split'] for game in dataset['games']] == ['FIT']*6+['HELDOUT']*2
    assert dataset['terminal_codes'].tolist() == [-1]*8
    assert dataset['afterstates'].dtype == np.int32 and dataset['rewards'].dtype == np.float64
    assert dataset['ends'].dtype == np.int64
    assert acquisition['training']['raw_tiles'] == budget
    assert acquisition['physical_acquisitions'] == 1 and acquisition['new_evaluation_games'] == 0
    assert acquisition['new_value_updates'] == 0
    assert template.updates == 99 and template.weights.tolist() == [3.]
    assert not template.weights.flags.writeable and RetainedStream.instances[-1].closed
    assert all(row['lifecycle'] == 21 and row['parent'] == 1 for row in emitted)
    assert {row['kind'] for row in emitted} == {'WARMUP', 'TRAIN', 'ACQUISITION_SNAPSHOT'}
    assert sum(row['kind'] == 'ACQUISITION_SNAPSHOT' for row in emitted) == 1


def test_all_initial_tiles_and_unfinished_tail_are_paid_but_holdout_never_enters_fit_memory(monkeypatch, tmp_path):
    budget = prepare(monkeypatch)
    records = []
    result = core.acquire_dataset(FrozenTemplate(), 0, 0, records.append, tmp_path, raw_budget=budget)
    data, costs = result['dataset'], result['acquisition']
    warm = [row for row in records if row['kind'] == 'WARMUP']
    train = [row for row in records if row['kind'] == 'TRAIN']
    warm_raw = sum(len(row['raw_spawns']) for row in warm)
    assert costs['warmup']['raw_tiles'] == warm_raw >= 256
    assert costs['warmup']['environment_counts']['initial_spawns'] == 2*len(warm)
    assert costs['warmup']['direct_counts']['direct_choose_calls'] == warm_raw-2*len(warm)
    assert sum(len(row['raw_spawns']) for row in train) == budget
    assert sum(spawn['kind'] == 'INITIAL' for row in train for spawn in row['raw_spawns']) == 18
    assert data['fit_memory']['observations_seen'] == warm_raw+data['fit_end_raw']
    assert data['actor_memory_A_end']['observations_seen'] == warm_raw+budget
    assert data['costs']['excluded_tail_games'] == 1
    assert data['costs']['excluded_tail_raw_tiles'] == 5
    assert data['costs']['excluded_tail_steps'] == 3
    assert data['costs']['fit_raw_tiles']+data['costs']['heldout_raw_tiles']+5 == budget
    assert data['costs']['full_A_acquisition_counts'] == costs['training']['counts']
    assert data['costs']['processing_memory_counts']['observations_received'] == warm_raw+budget
    assert len(RetainedStream.instances[-1].calls) == costs['reconstruction']['chunks']
    assert all(call['tile_budget'] <= 64 for call in RetainedStream.instances[-1].calls)


def test_independent_seed_families_and_full_warmup_games(monkeypatch, tmp_path):
    budget = prepare(monkeypatch)
    records = []
    core.acquire_dataset(FrozenTemplate(), 63, 3, records.append, tmp_path, raw_budget=budget)
    warm = [row for row in records if row['kind'] == 'WARMUP']
    assert [row['summary']['seed'] for row in warm] == [291100000000+63*1000000+i for i in range(len(warm))]
    assert all(row['summary']['status'] == 'LOST' for row in warm)
    assert all(row['start']['stream_seed'] == 291200000000+63*10000000
               for row in records if row['kind'] == 'TRAIN')
    training = {core.training_seed(life) for life in range(64)}
    warming = {core.warmup_seed(life, game) for life in range(64) for game in range(10)}
    evaluation = {291900000000+life*1000000+game for life in range(64) for game in range(32)}
    assert not training & warming and not training & evaluation and not warming & evaluation


@pytest.mark.parametrize('where', ['warmup', 'training'])
def test_actual_cutoff_is_retained_then_rejected_without_terminal_labels(monkeypatch, tmp_path, where):
    budget = prepare(monkeypatch)
    if where == 'warmup':
        def cutoff(*args):
            result = retained_warmup(*args)
            result['status'] = 'CUTOFF'
            return result
        monkeypatch.setattr(core, 'run_episode', cutoff)
    else:
        monkeypatch.setattr(RetainedStream, 'cutoff', True)
    template, records = FrozenTemplate(), []
    with pytest.raises(ValueError, match='cutoff retained'):
        core.acquire_dataset(template, 0, 0, records.append, tmp_path, raw_budget=budget)
    assert not any(row['kind'] == 'ACQUISITION_SNAPSHOT' for row in records)
    if where == 'warmup':
        assert records[-1]['summary']['status'] == 'CUTOFF'
    else:
        assert any(game['status'] == 'CUTOFF' for game in records[-1]['completed_games'])
        assert RetainedStream.instances[-1].closed
    assert template.weights.tolist() == [3.] and template.updates == 99


def test_wrong_source_parent_and_writable_actor_fail_before_physical_acquisition(monkeypatch, tmp_path):
    prepare(monkeypatch)
    records, template = [], FrozenTemplate()
    with pytest.raises(ValueError, match='parent'):
        core.acquire_dataset(template, 1, 0, records.append, tmp_path, raw_budget=10)
    template.weights.flags.writeable = True
    with pytest.raises(ValueError, match='frozen'):
        core.acquire_dataset(template, 1, 1, records.append, tmp_path, raw_budget=10)
    assert not records
