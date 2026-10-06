"""Paid complete-game detection, physical reconstruction and frozen acquisition."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import confirmed_context_data_v309 as core
from acfqp.science.confirmed_context_v309 import ConfirmedContexts
from acfqp.science.retained_actor_data_v287 import _Replay
from test_confirmed_context_v309 import commit
from test_independent_actor_data_v291 import FrozenTemplate, RetainedStream, prepare, retained_warmup


def setup(monkeypatch):
    budget = prepare(monkeypatch)
    monkeypatch.setattr(core, 'run_episode', retained_warmup)
    monkeypatch.setattr(core, 'NativeValueStream', RetainedStream)
    return budget


def acquire(template, router, records, runtime, *, stage='A1', p_four=.1, budget=512):
    return core.acquire_stage(template, 21, 1, stage, router, records.append, runtime,
        p_four=p_four, warmup_seed_base=309100000000, training_seed_base=309200000000,
        raw_budget=budget)


def test_first_context_full_physical_cohort_retains_v308_splits_and_tail(monkeypatch, tmp_path):
    budget = setup(monkeypatch)
    router, template, records = ConfirmedContexts(), FrozenTemplate(), []
    result = acquire(template, router, records, tmp_path, budget=budget)
    kinds = [row['kind'] for row in records]
    detection = kinds.index('DETECTION_SNAPSHOT')
    assert kinds[:detection] == ['WARMUP', 'WARMUP', 'DETECTOR_LOOK']
    assert kinds[detection+1] == 'TRAIN' and kinds[-1] == 'ACQUISITION_SNAPSHOT'
    assert kinds.count('DETECTION_SNAPSHOT') == kinds.count('ACQUISITION_SNAPSHOT') == 1
    warm, data = result['acquisition']['warmup'], result['dataset']
    assert warm['raw_tiles'] == warm['initial_raw_tiles'] == 278
    assert warm['confirmation_raw_tiles'] == warm['confirmation_games'] == 0
    assert warm['initial_game_count'] == 2 and warm['detector_looks'] == 1
    assert result['route']['decision'] == 'FIRST_CONTEXT'
    assert router.banks[0]['observations'] == warm['raw_tiles']
    assert data['actor_memory_A1_end']['observations_seen'] == warm['raw_tiles']+budget
    assert data['fit_game_count'] == 6 and [game['split'] for game in data['games']] == ['FIT']*6+['HELDOUT']*2
    assert data['costs']['excluded_tail_raw_tiles'] == 5 and data['costs']['excluded_tail_steps'] == 3
    assert warm['memory_counts']['predict_calls'] == result['detector_belief']['memory']['counts']['predict_calls'] == 1
    assert data['costs']['processing_memory_counts']['predict_calls'] == result['acquisition']['training']['chunks']+2
    assert data['costs']['warmup_raw_tiles'] == warm['raw_tiles']
    assert result['acquisition']['physical_acquisitions'] == 1
    assert result['acquisition']['new_value_updates'] == 0 and template.updates == 99
    assert RetainedStream.instances[-1].closed
    assert all(row['start']['stream_seed'] == 309200000000+21*10000000 for row in records if row['kind'] == 'TRAIN')


def test_immediate_reuse_ignores_task_metadata_and_never_constructs_engine(monkeypatch, tmp_path):
    budget = setup(monkeypatch)
    router, template = ConfirmedContexts(), FrozenTemplate()
    first = acquire(template, router, [], tmp_path, budget=budget)
    before, records = deepcopy(router.banks), []
    def no_stream(*args, **kwargs):
        raise AssertionError('Reuse constructed a training engine')
    monkeypatch.setattr(core, 'NativeValueStream', no_stream)
    result = acquire(template, router, records, tmp_path, stage='B', p_four=.5, budget=budget)
    assert result['route']['decision'] == 'REUSE' and result['route']['context_id'] == 0
    assert result['dataset'] is result['acquisition']['training'] is result['acquisition']['snapshot'] is None
    assert result['acquisition']['physical_acquisitions'] == 0 and result['acquisition']['native_setup_counts'] == {}
    assert [row['kind'] for row in records] == ['WARMUP', 'WARMUP', 'DETECTOR_LOOK', 'DETECTION_SNAPSHOT']
    assert result['acquisition']['warmup']['raw_tiles'] == first['acquisition']['warmup']['raw_tiles']
    assert router.banks[0]['observations'] == 2*before[0]['observations'] and router.banks[0]['visits'] == 2
    assert router.counts['prototype_commits'] == 2 and template.updates == 99


class BranchReplay:
    instances = []

    def __init__(self, expected, phase):
        from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
        self.expected, self.memory = expected, SpawnMemory('LIBRARY')
        self.processing, self.chunks, self.cpu_seconds, self.warmup_raw = Counter(), 0, 0., 0
        self.instances.append(self)

    def warmup(self, row):
        for spawn in row['raw_spawns']:
            self.memory.observe(spawn['rank'])
        self.warmup_raw += len(row['raw_spawns'])
        self.processing['warmup_records'] += 1

    def train(self, row):
        for spawn in row['raw_spawns']:
            self.memory.observe(spawn['rank'])
        self.chunks += 1

    def checkpoint(self, row):
        assert self.memory.predict() == row['snapshot']['estimated_p_four']

    def finish(self):
        assert self.warmup_raw == self.expected['warmup']['raw_tiles']
        return dict(costs={})


class PhysicalWarmupReplay(BranchReplay):
    warmup = _Replay.warmup


class BranchStream:
    instances = []

    def __init__(self, template, seed, runtime, max_steps):
        self.raw, self.closed = 0, False
        self.setup_counts, self.setup_seconds = Counter(), 0.
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.instances.append(self)

    def state(self):
        return dict(raw_tiles=self.raw, pending_bank_id=None)

    def advance(self, template, bank, pending, pmodel, ptrue, tile_budget, max_postaction):
        before = self.state()
        self.raw += tile_budget
        self.counts['environment']['raw_tile_productions'] += tile_budget
        return dict(start=before, end=self.state(), raw_spawns=[dict(rank=1) for _ in range(tile_budget)],
            actions=[], scores=[], completed_games=[], updates=[], seconds=0., cpu_seconds=0.,
            counts=dict(environment=dict(raw_tile_productions=tile_budget), planning={}, learning={}))

    def close(self):
        self.closed = True


def branch_setup(monkeypatch, fours):
    """Synthetic rank pools exercise routing; retained fixtures cover game physics."""
    sequence = iter(fours)
    def game(seed, policy, p_four, max_steps):
        k = next(sequence)
        ranks = [2]*k+[1]*(300-k)
        board = (1,)+(0,)*15
        steps = [dict(action=policy(board, i), score=0, spawned_rank=rank, spawned_cell=0)
                 for i, rank in enumerate(ranks[2:])]
        return dict(initial_spawns=[dict(rank=rank, cell=i) for i, rank in enumerate(ranks[:2])],
            steps=steps, return_score=0, status='LOST', steps_count=298, final_board=[0]*16,
            work=dict(initial_spawns=2, raw_tile_productions=300, sampled_transitions=298))
    monkeypatch.setattr(core, 'run_episode', game)
    monkeypatch.setattr(core, '_Replay', BranchReplay)
    monkeypatch.setattr(core, 'NativeValueStream', BranchStream)
    BranchStream.instances.clear()


@pytest.mark.parametrize('extra_k,decision', [(20, 'REUSE'), (60, 'CONFIRMED_NEW')])
def test_pending_pool_resolves_after_new_paid_game_without_intermediate_commit(monkeypatch, tmp_path, extra_k, decision):
    branch_setup(monkeypatch, [45, extra_k])
    router, template, records, banks_at_rows = ConfirmedContexts(), FrozenTemplate(), [], []
    commit(router, 10000, 1000)
    before = deepcopy(router.banks)
    def emit(row):
        records.append(row)
        banks_at_rows.append(deepcopy(router.banks))
    result = core.acquire_stage(template, 21, 1, 'B', router, emit, tmp_path,
        p_four=.5, warmup_seed_base=309100000000, training_seed_base=309200000000, raw_budget=8)
    assert [row['kind'] for row in records[:5]] == ['WARMUP', 'DETECTOR_LOOK', 'CONFIRMATION', 'DETECTOR_LOOK', 'DETECTION_SNAPSHOT']
    assert records[1]['decision'] == 'PENDING_CONFIRMATION' and records[3]['decision'] == decision
    assert all(banks == before for banks in banks_at_rows[:4])
    assert result['route']['decision'] == decision and result['route']['statistics'] == dict(observations=600, fours=45+extra_k)
    assert router.counts['prototype_commits'] == 2 and router.counts['probe_calls'] == 3
    warm = result['acquisition']['warmup']
    assert warm['initial_raw_tiles'] == warm['confirmation_raw_tiles'] == 300
    assert warm['initial_game_count'] == warm['confirmation_games'] == 1 and warm['detector_looks'] == 2
    assert warm['raw_tiles'] == 600 and warm['direct_counts']['direct_choose_calls'] == 596
    assert warm['memory_counts']['observations_received'] == 600 and warm['memory_counts']['predict_calls'] == 1
    assert warm['memory_events'] == records[0]['memory_events']+records[2]['memory_events']
    assert warm['game_summaries'][1]['seed'] == warm['game_summaries'][0]['seed']+1
    assert result['detector_belief']['memory']['pending']['n'] == 24
    assert len(BranchStream.instances) == int(decision == 'CONFIRMED_NEW') and template.updates == 99
    assert result['acquisition']['physical_acquisitions'] == int(decision == 'CONFIRMED_NEW')
    assert BranchReplay.instances[-1].expected['warmup'] == warm


def test_true_b_observations_confirm_immediately_without_extra_game(monkeypatch, tmp_path):
    branch_setup(monkeypatch, [150])
    router, records = ConfirmedContexts(), []
    commit(router, 10000, 1000)
    result = acquire(FrozenTemplate(), router, records, tmp_path, stage='B', p_four=.5, budget=8)
    assert result['route']['decision'] == 'CONFIRMED_NEW' and result['route']['context_id'] == 1
    assert result['route']['novelty_posterior'] >= .99
    assert result['acquisition']['warmup']['confirmation_games'] == 0
    assert len(BranchStream.instances) == 1 and not any(row['kind'] == 'CONFIRMATION' for row in records)


def test_cap_pays_whole_overshooting_game_and_preserves_prototypes(monkeypatch, tmp_path):
    # Fixed cumulative counts keep BF near -2 at every complete-game look.
    cumulative = [48, 86, 123, 159, 194, 229, 264, 299, 334, 368, 402, 437, 471, 505]
    branch_setup(monkeypatch, [cumulative[0]]+[b-a for a, b in zip(cumulative, cumulative[1:])])
    router, template, records = ConfirmedContexts(), FrozenTemplate(), []
    commit(router, 10000, 1000)
    before = deepcopy(router.banks)
    result = acquire(template, router, records, tmp_path, budget=8)
    route, warm = result['route'], result['acquisition']['warmup']
    assert route['decision'] == 'CAP_REUSE_UNRESOLVED' and not route['prototype_committed']
    assert route['prototype_before'] == route['prototype_after'] == before[0] and router.banks == before
    assert router.counts['prototype_commits'] == 1
    looks = [row for row in records if row['kind'] == 'DETECTOR_LOOK']
    assert len(looks) == warm['detector_looks'] == 14 and all(row['decision'] == 'PENDING_CONFIRMATION' for row in looks)
    assert not any(row['at_cap'] for row in looks[:-1]) and looks[-1]['at_cap']
    assert warm['raw_tiles'] == 4200 and warm['confirmation_raw_tiles'] == 3900
    assert warm['initial_game_count'] == 1 and warm['confirmation_games'] == 13
    assert warm['environment_counts']['raw_tile_productions'] == 4200
    assert warm['direct_counts']['direct_choose_calls'] == 14*298
    assert route['statistics'] == dict(observations=4200, fours=505)
    assert result['dataset'] is None and result['acquisition']['physical_acquisitions'] == 0
    assert not BranchStream.instances and template.updates == 99


def test_extra_games_are_reconstructed_as_actual_complete_games(monkeypatch, tmp_path):
    setup(monkeypatch)
    monkeypatch.setattr(core, '_Replay', PhysicalWarmupReplay)
    monkeypatch.setattr(core, 'NativeValueStream', BranchStream)
    BranchStream.instances.clear()
    router, records = ConfirmedContexts(), []
    commit(router, 10000, 9760)
    result = acquire(FrozenTemplate(), router, records, tmp_path, budget=8)
    warm = result['acquisition']['warmup']
    assert result['route']['decision'] == 'CONFIRMED_NEW'
    assert warm['initial_raw_tiles'] == warm['confirmation_raw_tiles'] == 278
    assert warm['initial_game_count'] == warm['confirmation_games'] == 2
    assert warm['raw_tiles'] == 556 and result['route']['statistics']['fours'] == 556
    assert result['acquisition']['reconstruction']['counts']['warmup_records'] == 4
    assert result['acquisition']['reconstruction']['counts']['ground_explicit_swipe_calls'] == 548
    assert [row['summary']['seed'] for row in records if row['kind'] in ('WARMUP', 'CONFIRMATION')] == [309100000000+21*1000000+i for i in range(4)]
    assert BranchStream.instances[-1].closed


@pytest.mark.parametrize('where', ['warmup', 'confirmation', 'training'])
def test_cutoffs_remain_retained_and_never_supply_labels(monkeypatch, tmp_path, where):
    budget = setup(monkeypatch)
    router, template, records = ConfirmedContexts(), FrozenTemplate(), []
    if where == 'training':
        monkeypatch.setattr(RetainedStream, 'cutoff', True)
    else:
        if where == 'confirmation':
            commit(router, 10000, 9760)
        calls = 0
        def cutoff(*args):
            nonlocal calls
            calls += 1
            game = retained_warmup(*args)
            if calls == (1 if where == 'warmup' else 3):
                game['status'] = 'CUTOFF'
            return game
        monkeypatch.setattr(core, 'run_episode', cutoff)
    with pytest.raises(ValueError, match='cutoff retained'):
        acquire(template, router, records, tmp_path, budget=budget)
    assert not any(row['kind'] == 'ACQUISITION_SNAPSHOT' for row in records)
    assert template.updates == 99
    if where == 'training':
        assert records[-1]['kind'] == 'TRAIN' and RetainedStream.instances[-1].closed
    else:
        assert records[-1]['kind'] == where.upper() and records[-1]['summary']['status'] == 'CUTOFF'
        assert not any(row['kind'] == 'DETECTION_SNAPSHOT' for row in records)


def test_parent_and_source_freeze_are_enforced_before_games(monkeypatch, tmp_path):
    setup(monkeypatch)
    template, router, records = FrozenTemplate(), ConfirmedContexts(), []
    with pytest.raises(ValueError, match='parent'):
        core.acquire_stage(template, 21, 0, 'B', router, records.append, tmp_path,
            p_four=.5, warmup_seed_base=1, training_seed_base=2)
    template.weights.flags.writeable = True
    with pytest.raises(ValueError, match='frozen'):
        acquire(template, router, records, tmp_path)
    assert not records and not router.banks
