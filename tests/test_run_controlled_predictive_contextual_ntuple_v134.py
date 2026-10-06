"""Finite runner fixtures for source isolation, stream continuity and aliases."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_contextual_ntuple_v134 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD, AFTER = [1, 1]+[0]*14, [2]+[0]*15


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_contextual_ntuple_v134.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0,
        scope='Mocked source, models, streams, games and phase execution; no natural samples'))
    path.write_text(json.dumps(record, indent=2)+'\n')


class Model:
    def __init__(self, parent=None, kind='PRIOR', build=None):
        assert kind == 'PRIOR'
        self.kind, self.offset, self.updates = kind, -1., 0
        self.weights = np.zeros(1)
        self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.
        self.source = SimpleNamespace(weights=np.zeros(1), counts=Counter())
        self.source.weights.flags.writeable = False

    def freeze(self):
        self.weights.flags.writeable = False

    def save(self, path):
        self.counts['checkpoint_saves'] += 1
        return dict(path=str(path), updates=self.updates, bytes=0)

    def choose(self, board, query):
        self.counts['choose_calls'] += 1
        rows = dict(DOWN=dict(afterstate=AFTER, score=4, value=2.),
                    LEFT=dict(afterstate=BOARD, score=0, value=1.))
        return dict(action='DOWN', **rows['DOWN'], action_values=rows)


class ConditionalModel(Model):
    def __init__(self, parent=None, representation='GLOBAL', build_dir=None):
        super().__init__(parent, 'PRIOR', build_dir)
        assert representation in ('GLOBAL', 'CAPACITY')
        self.representation = representation


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(row) for row in stream]


def test_source_omits_adapted_checkpoints_and_retained_evaluation_results():
    previous = dict(snapshots=[dict(life=0, rule={'kept': 1}, models={'value': 'V120'},
        counts={'constant': 'V127'}, checkpoints={'reject': 'V133'},
        training_trace='reject', control_trace='reject')], inherited_costs={'old': 12})
    source = runner.extract_source(previous, dict(complete=True, costs={'replay': 13}, outcomes=[999]))
    assert set(source['snapshots'][0]) == {'life', 'rule', 'models', 'counts'}
    assert source['inherited_costs'] == dict(old=12, v133_experiment={'replay': 13})
    source['snapshots'][0]['rule']['kept'] = 2
    assert previous['snapshots'][0]['rule']['kept'] == 1
    assert runner.train_seed(2, 'risk8', 3) == 13400000000+10000000+2000000+500000+3
    assert runner.evaluation_seed(2, 3) == 13400000000+90000000+200000+3
    assert runner.settings()['physical_control_games'] == 4*2*16*(1+3*3) == 1280
    assert runner.settings()['logical_control_rows'] == 4*2*16*4*4 == 2048


def test_three_representations_use_the_original_stream_and_preserve_pending(tmp_path, monkeypatch):
    streams, models = [], []
    class SavingModel(Model):
        def __init__(self, *args):
            super().__init__(*args); models.append(self)
    class SavingConditional(ConditionalModel):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs); models.append(self)
    class Stream:
        def __init__(self, model, seed_fn, max_steps=2000, p_four=.1):
            self.model, self.seed_fn = model, seed_fn
            self.transitions = self.episodes_started = self.episodes_completed = 0
            self.episode, self.step = -1, 0
            self.board = self.pending = None
            self.environment_counts, self.calls = Counter(), []
            streams.append(self)
        def advance_to(self, total):
            self.calls.append(total)
            if not total:
                return []
            start = self.transitions
            self.transitions = self.step = total
            self.episodes_started, self.episode = 1, 0
            self.board, self.pending = BOARD, AFTER
            self.environment_counts['sampled_transitions'] = total
            self.model.updates = total-1
            return [dict(start_step=start, end_step=total, status='ACTIVE', seed=self.seed_fn(0))]
    monkeypatch.setattr(runner, 'QueryTD', SavingModel)
    monkeypatch.setattr(runner, 'ConditionalQueryTD', SavingConditional)
    monkeypatch.setattr(runner, 'TDStream', Stream)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Model(), {}))
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 2, 5))
    monkeypatch.setattr(runner, 'run_episode', lambda *args: pytest.fail('training started evaluation'))
    data = runner.train_lifecycle(dict(life=2), tmp_path)
    assert len(streams) == 6
    assert [getattr(s.model, 'representation', 'SINGLE') for s in streams] == list(runner.KINDS)*2
    assert all(s.calls == [0, 2, 5] for s in streams)
    assert all(not m.weights.flags.writeable for m in models)
    for query, row in data['queries'].items():
        assert row['parent_before'] == row['parent_after']
        for kind, learner in row['learners'].items():
            checks = learner['checkpoints']
            assert [r['transitions'] for r in checks] == [0, 2, 5]
            assert checks[0]['stream_state']['board'] is None
            assert [r['updates'] for r in checks] == [0, 1, 4]
            assert [r['stream_state']['pending'] for r in checks] == [None, AFTER, AFTER]
            state = learner['initialization']['state']
            assert state['kind'] == 'PRIOR'
            assert state.get('representation', 'SINGLE') == kind
            trace = read_rows(tmp_path/learner['training_trace'])
            assert [(r['start_step'], r['end_step']) for r in trace] == [(0, 2), (2, 5)]
            assert all(r['seed'] == runner.train_seed(2, query, 0) for r in trace)


def test_one_parent_game_checks_all_three_zero_models_and_every_legal_action(monkeypatch):
    calls = []
    def game(seed, act, probability, max_steps):
        calls.append(seed)
        assert act(BOARD, 0) == 'DOWN'
        return dict(seed=seed, return_score=4, status='LOST', steps_count=1, seconds=0.,
            initial_board=BOARD, initial_spawns=[], final_board=AFTER,
            steps=[dict(action='DOWN', score=4, spawned_cell=1, spawned_rank=1)],
            work=dict(sampled_transitions=1))
    monkeypatch.setattr(runner, 'run_episode', game)
    parent = Model()
    zeros = {kind: Model() if kind == 'SINGLE' else ConditionalModel(representation=kind)
             for kind in runner.KINDS}
    for model in [parent, *zeros.values()]: model.freeze()
    row = runner.full_game(parent, 0, 'risk1', 'PARENT', 0, 3, zeros=zeros)
    assert calls == [runner.evaluation_seed(0, 3)]
    assert set(row['zero_equivalence']) == set(runner.KINDS)
    assert all(item['exact'] and item['before'] == item['after']
               and item['counts'] == {'choose_calls': 1} for item in row['zero_equivalence'].values())
    original = zeros['GLOBAL'].choose
    def disagree(board, query):
        choice = original(board, query); choice['action_values']['LEFT']['value'] += .1
        return choice
    zeros['GLOBAL'].choose = disagree
    with pytest.raises(AssertionError, match='zero-training GLOBAL differs'):
        runner.full_game(parent, 0, 'risk1', 'PARENT', 0, 3, zeros=zeros)


def test_evaluation_freezes_models_and_does_not_run_duplicate_zero_games(tmp_path, monkeypatch):
    loads, calls = [], []
    class LoadedModel(Model):
        @classmethod
        def load(cls, path, parent, build):
            assert path.name.startswith('SINGLE_')
            model = cls(); model.load_counts, model.last_load_seconds = {'checkpoint_loads': 1}, 0.
            loads.append(model); return model
    class LoadedConditional(ConditionalModel):
        @classmethod
        def load(cls, path, parent, build):
            representation = path.name.split('_')[0]
            model = cls(representation=representation)
            model.load_counts, model.last_load_seconds = {'checkpoint_loads': 1}, 0.
            loads.append(model); return model
    def game(model, life, query, method, checkpoint, replica, zeros=None):
        assert not model.weights.flags.writeable or method == 'PARENT'
        if zeros is not None:
            assert set(zeros) == set(runner.KINDS)
            assert all(not zero.weights.flags.writeable for zero in zeros.values())
        calls.append((query, method, checkpoint, replica, zeros is not None))
        return dict(query=query, method=method, checkpoint=checkpoint, replica=replica)
    monkeypatch.setattr(runner, 'QueryTD', LoadedModel)
    monkeypatch.setattr(runner, 'ConditionalQueryTD', LoadedConditional)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Model(), {}))
    monkeypatch.setattr(runner, 'full_game', game)
    monkeypatch.setattr(runner, 'REPLICAS', 2)
    trained = dict(queries={q: dict(learners={kind: dict(checkpoints=[dict(age=age,
        model_ref=f'{kind}_{age}.npz') for age in runner.CHECKPOINTS]) for kind in runner.KINDS})
        for q in runner.QUERIES})
    data = runner.evaluate_lifecycle(dict(life=1), trained, tmp_path)
    assert len(calls) == len(read_rows(tmp_path/data['control_trace'])) == 40
    assert sum(row[1] == 'PARENT' for row in calls) == 4
    assert sum(row[-1] for row in calls) == 4
    assert not any(row[1] in runner.KINDS and row[2] == 0 for row in calls)
    assert len(loads) == 24 and all(not model.weights.flags.writeable for model in loads)
    for query in data['queries'].values():
        for item in query['checkpoint_loads']:
            assert item['state'].get('representation', 'SINGLE') == item['kind']


def test_all_histories_freeze_before_any_evaluation(tmp_path, monkeypatch):
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
    assert events == [(phase, life) for phase in ('train', 'evaluate') for life in runner.LIVES]
    assert json.loads((output/'run.json').read_text())['status'] == 'complete'
