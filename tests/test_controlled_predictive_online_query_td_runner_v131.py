"""V131 source isolation, exact scheduling and frozen controls, without sampling."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_online_query_td_v131 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1]+[0]*14
AFTER = [2]+[0]*15


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_online_query_td_v131.runner_checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        newly_sampled_environment_transitions=0, environment_random_draws=0,
        native_model_calls=0, optimizer_steps=0,
        scope='Mocked streams, policies, games and phase execution; no native or environment calls'))
    path.write_text(json.dumps(log, indent=2)+'\n')


class Model:
    def __init__(self, parent=None, kind='PRIOR', build=None):
        self.kind, self.offset, self.updates = kind, -1. if kind == 'PRIOR' else 0., 0
        self.weights = np.zeros(1)
        self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.

    def freeze(self):
        self.weights.flags.writeable = False

    def choose(self, board, query=None):
        assert not self.weights.flags.writeable
        self.counts['choose_calls'] += 1
        values = dict(DOWN=dict(afterstate=AFTER, score=4, value=2.),
            LEFT=dict(afterstate=BOARD, score=0, value=1.))
        return dict(action='DOWN', **values['DOWN'], action_values=values, status='ACTIVE')

    def save(self, path):
        self.counts['checkpoint_saves'] += 1
        return dict(path=str(path), updates=self.updates, bytes=0)


class Parent(Model):
    def __init__(self):
        super().__init__()
        self.freeze()
        self.updates = 4096
        self.source = SimpleNamespace(weights=self.weights, counts=Counter(source_fit=4096))


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def test_seed_namespace_source_isolation_and_declared_control_costs():
    assert runner.train_seed(2, 'risk8', 123) == runner.BASE+10000000+2000000+500000+123
    assert runner.evaluation_seed(2, 3) == runner.BASE+90000000+200000+3
    intervals = [(runner.train_seed(life, query, 0), runner.train_seed(life, query, 40000))
        for life in runner.LIVES for query in runner.QUERIES]
    assert all(end < following for (_, end), (following, _) in zip(intervals, intervals[1:]))
    assert intervals[-1][1] < runner.evaluation_seed(0, 0)
    previous = dict(snapshots=[dict(life=0, rule={'keep': 1}, models={'value': 'V120'},
        counts={'constant': 'V127'}, residuals={'reject': 'V130'}, outcomes=[999])],
        inherited_costs={'source_training': 12})
    analysis = dict(complete=True, costs={'historical': 13}, results={'reject': 999})
    source = runner.extract_source(previous, analysis)
    assert set(source['snapshots'][0]) == {'life', 'rule', 'models', 'counts'}
    assert source['required_inputs']['SCRATCH'] == 'identified dynamics only'
    assert source['inherited_costs'] == dict(source_training=12, v130_experiment={'historical': 13})
    source['snapshots'][0]['rule']['keep'] = 2
    assert previous['snapshots'][0]['rule']['keep'] == 1
    actual = len(runner.LIVES)*len(runner.QUERIES)*runner.REPLICAS
    assert runner.settings()['physical_control_games'] == actual*8 == 1024
    assert runner.settings()['logical_control_rows'] == actual*12 == 1536


def test_training_reuses_stream_and_saves_exact_budgets_without_evaluation(tmp_path, monkeypatch):
    streams, parents, saved_models = [], [], []
    class Stream:
        def __init__(self, model, seed_fn, max_steps, probability):
            self.model, self.seed_fn = model, seed_fn
            self.transitions = self.episodes_started = self.episodes_completed = 0
            self.episode, self.step = -1, 0
            self.board = self.pending = None
            self.environment_counts, self.calls = Counter(), []
            streams.append(self)
        def advance_to(self, total):
            self.calls.append(total)
            if total == self.transitions:
                assert total == 0 and self.board is self.pending is None
                return []
            start = self.transitions
            self.transitions = self.step = total
            self.episodes_started, self.episode = 1, 0
            self.board, self.pending = BOARD, AFTER
            self.environment_counts['sampled_transitions'] = total
            self.model.updates = total-1
            return [dict(start_step=start, end_step=total, cumulative_transitions=total,
                pending_after=AFTER, status='ACTIVE', seed=self.seed_fn(0))]
    class SavingModel(Model):
        def __init__(self, *args):
            super().__init__(*args); saved_models.append(self)
    def load(*args):
        parent = Parent(); parents.append(parent)
        return parent, {'source_loads': 1}
    monkeypatch.setattr(runner, 'TDStream', Stream)
    monkeypatch.setattr(runner, 'QueryTD', SavingModel)
    monkeypatch.setattr(runner, 'load_parent', load)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 2, 5))
    monkeypatch.setattr(runner, 'run_episode', lambda *args: pytest.fail('training sampled an evaluation game'))
    data = runner.train_lifecycle(dict(life=2), tmp_path)
    assert len(streams) == 4 and all(s.calls == [0, 2, 5] for s in streams)
    assert all(not m.weights.flags.writeable for m in saved_models)
    for query, row in data['queries'].items():
        assert row['parent_before'] == row['parent_after'] == dict(updates=4096, readonly=True)
        for kind, learner in row['learners'].items():
            checks = learner['checkpoints']
            assert [r['transitions'] for r in checks] == [0, 2, 5]
            assert [r['updates'] for r in checks] == [0, 1, 4]
            assert checks[0]['stream_state']['pending'] is None
            assert all(r['stream_state']['pending'] == AFTER for r in checks[1:])
            assert learner['final_stream_state']['episodes_started'] == 1
            trace = read_rows(tmp_path/learner['training_trace'])
            assert [(r['start_step'], r['end_step']) for r in trace] == [(0, 2), (2, 5)]
            assert all(r['seed'] == runner.train_seed(2, query, 0) for r in trace)
    assert all(p.source.counts == Counter(source_fit=4096) for p in parents)


def test_zero_prior_checks_all_values_during_one_physical_game(tmp_path, monkeypatch):
    calls = []
    def game(seed, act, probability, max_steps):
        calls.append(seed)
        assert act(BOARD, 0) == 'DOWN'
        return dict(seed=seed, return_score=4, status='LOST', steps_count=1, seconds=0.,
            initial_board=BOARD, initial_spawns=[], final_board=AFTER,
            steps=[dict(action='DOWN', score=4, spawned_cell=1, spawned_rank=1)],
            work=dict(sampled_transitions=1))
    monkeypatch.setattr(runner, 'run_episode', game)
    parent, zero = Parent(), Model(); zero.freeze()
    row = runner.full_game(parent, 0, 'risk1', 'PARENT', 0, 3, zero_prior=zero)
    assert calls == [runner.evaluation_seed(0, 3)]
    assert row['exact_zero_prior'] and row['zero_prior_counts'] == {'choose_calls': 1}
    assert row['result']['policy_counts'] == {'choose_calls': 1}
    assert row['result']['model_state_before'] == row['result']['model_state_after']
    assert row['zero_prior_before'] == row['zero_prior_after']
    original = zero.choose
    def disagree(board, query):
        choice = original(board, query)
        choice['action_values']['LEFT']['value'] += .1
        return choice
    zero.choose = disagree
    with pytest.raises(AssertionError, match='zero-training PRIOR'):
        runner.full_game(parent, 0, 'risk1', 'PARENT', 0, 3, zero_prior=zero)


def test_evaluation_loads_frozen_checkpoints_and_reuses_parent_once(tmp_path, monkeypatch):
    loads, calls = [], []
    class LoadedModel(Model):
        @classmethod
        def load(cls, path, parent, build):
            name, age = path.stem.split('_'); model = cls(parent, name)
            model.load_counts, model.last_load_seconds = {'checkpoint_loads': 1}, 0.
            loads.append(model)
            return model
    def game(model, life, query, method, checkpoint, replica, zero_prior=None):
        assert not model.weights.flags.writeable
        if zero_prior is not None:
            assert not zero_prior.weights.flags.writeable
        calls.append((query, method, checkpoint, replica, zero_prior is not None))
        return dict(query=query, method=method, checkpoint=checkpoint, replica=replica)
    monkeypatch.setattr(runner, 'QueryTD', LoadedModel)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Parent(), {}))
    monkeypatch.setattr(runner, 'full_game', game)
    trained = dict(queries={q: dict(learners={kind: dict(checkpoints=[dict(age=age,
        model_ref=f'{kind}_{age}.npz') for age in runner.CHECKPOINTS]) for kind in runner.KINDS})
        for q in runner.QUERIES})
    data = runner.evaluate_lifecycle(dict(life=1), trained, tmp_path)
    assert len(calls) == 256 and len(read_rows(tmp_path/data['control_trace'])) == 256
    assert sum(r[1] == 'PARENT' for r in calls) == 32
    assert not any(r[1] == 'PRIOR' and r[2] == 0 for r in calls)
    assert sum(r[-1] for r in calls) == 32
    assert len(loads) == 16 and all(not m.weights.flags.writeable for m in loads)
    assert all(row['parent_before'] == row['parent_after'] for row in data['queries'].values())


def test_run_freezes_every_lifecycle_before_submitting_any_evaluation(tmp_path, monkeypatch):
    previous = dict(snapshots=[dict(life=life, rule={}, models={}, counts={}, outcomes=[999])
        for life in runner.LIVES], inherited_costs={'old': 1})
    source = tmp_path/'source'; source.mkdir()
    (source/'source_capsule.json').write_text(json.dumps(previous))
    (source/'analysis.json').write_text(json.dumps(dict(complete=True, costs={'history': 2})))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def train(source, directory):
        assert 'outcomes' not in source
        assert not (directory/'frozen_training.json').exists()
        events.append(('train', source['life']))
        return dict(life=source['life'], queries={'frozen': True})
    def evaluate(source, trained, directory):
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'frozen' and len(frozen['lifecycles']) == 4
        assert sum(event[0] == 'train' for event in events) == 4
        assert trained['queries']['frozen']
        events.append(('evaluate', source['life']))
        return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda *args: None)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'train_lifecycle', train)
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    output = tmp_path/'run'; runner.run(output)
    data = json.loads((output/'run.json').read_text())
    assert events == [(phase, life) for phase in ('train', 'evaluate') for life in runner.LIVES]
    assert data['status'] == 'complete' and len(data['eval_lifecycles']) == 4
