"""Finite fixed-teacher orchestration and diagnostic-cost fixtures."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_bellman_consequences_v136 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD, AFTER, WIN_BOARD, GOAL = [1, 1]+[0]*14, [2]+[0]*15, [10, 10]+[0]*14, [11]+[0]*15


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_bellman_consequences_v136.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0, model_updates=0,
        scope='Mocked teachers, students, streams and games; aliases, diagnostics and frozen phase ordering'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def source_fixture():
    return dict(snapshots=[dict(life=life, rule={}, models={}, counts={},
        leaves={query: {representation: dict(model_ref=f'/retained/{life}_{query}_{representation}.npz',
            checkpoint=524288, updates=524000) for representation in runner.REPRESENTATIONS}
            for query in runner.TEACHER_QUERIES}, outcomes='not a training input')
        for life in runner.LIVES], inherited_costs={'old': 1})


class Leaf:
    def __init__(self, query='risk1', representation='SINGLE'):
        self.target_query = runner.QUERIES[query]
        self.kind, self.offset, self.updates = 'PRIOR', -1., 524000
        if representation != 'SINGLE': self.representation = representation
        self.weights = np.zeros(1); self.weights.flags.writeable = False
        self.source = SimpleNamespace(weights=self.weights)


def choice(board):
    winning = max(board) >= 10
    score, after = (2048, GOAL) if winning else (4, AFTER)
    values = dict(DOWN=dict(afterstate=after, score=score, value=2., tail_value=2.-score/2048.),
                  LEFT=dict(afterstate=BOARD, score=0, value=1., tail_value=1.))
    return dict(action='DOWN', value=2., action_values=values)


class Teacher:
    def __init__(self, leaf):
        self.leaf, self.counts = leaf, Counter()
    def choose(self, board, query):
        assert query == self.leaf.target_query
        assert not self.leaf.weights.flags.writeable
        self.counts['teacher_calls'] += 1
        return choice(board)


class Components:
    def __init__(self, leaf, build=None):
        self.leaf, self.radix, self.updates = leaf, 11, 0
        self.weights = np.zeros(2)
        self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.
        self.load_counts, self.last_load_seconds = {'checkpoint_loads': 1}, 0.
    def freeze(self):
        self.weights.flags.writeable = False
    def save(self, path):
        self.counts['checkpoint_saves'] += 1
        return dict(path=str(path), updates=self.updates, parameter_count=2)
    def choose(self, board, query, depth):
        assert depth == 2
        self.counts['choose_calls'] += 1
        result = choice(board)
        for row in result['action_values'].values(): row['consequences'] = [1., .5, .5]
        return result
    def value(self, board):
        assert max(board) < self.radix
        self.counts.update(value_calls=1, component_predictions=2)
        return dict(reward=1.25, success=.5)


def mock_teacher(source, representation, query, folder):
    leaf = Leaf(query, representation)
    return Leaf(query, representation), leaf, Teacher(leaf), {}


def test_source_isolation_and_fixed_query_roster():
    previous = source_fixture()
    source = runner.extract_source(previous, dict(complete=True, primary_complete=True, costs={'v135': 2}))
    assert len(source['snapshots']) == 4
    assert all(set(row) == {'life', 'rule', 'models', 'counts', 'leaves'} for row in source['snapshots'])
    assert sum(len(kinds) for row in source['snapshots'] for kinds in row['leaves'].values()) == 16
    source['snapshots'][0]['leaves']['risk1']['SINGLE']['updates'] = 0
    assert previous['snapshots'][0]['leaves']['risk1']['SINGLE']['updates'] == 524000
    assert source['inherited_costs'] == dict(old=1, v135_experiment={'v135': 2})
    for complete, primary in ((False, True), (True, False)):
        with pytest.raises(ValueError, match='V135 must be complete'):
            runner.extract_source(previous, dict(complete=complete, primary_complete=primary, costs={}))
    assert runner.evaluation_queries('risk1') == ('risk1', 'risk2', 'risk6')
    assert runner.evaluation_queries('risk8') == ('risk8', 'risk2', 'risk6')
    assert runner.settings()['physical_control_games'] == 16*16*(1+2+3) == 1536
    assert runner.settings()['logical_control_rows'] == 16*16*3*3 == 2304
    seeds = [runner.train_seed(life, representation, query, 0) for life in runner.LIVES
             for representation in runner.REPRESENTATIONS for query in runner.TEACHER_QUERIES]
    assert len(set(seeds)) == 16 and max(seeds) < runner.evaluation_seed(0, 0)
    assert runner.evaluation_seed(2, 3) == 13600000000+90000000+200000+3


def test_students_keep_their_frozen_teacher_and_resume_one_pending_stream(tmp_path, monkeypatch):
    streams, students = [], []
    class Student(Components):
        def __init__(self, *args):
            super().__init__(*args); students.append(self)
    class Stream:
        def __init__(self, model, teacher, seed_fn, limit, probability):
            assert model.leaf is teacher.leaf
            assert not teacher.leaf.weights.flags.writeable
            self.model, self.teacher, self.seed_fn = model, teacher, seed_fn
            self.transitions = self.episodes_started = self.episodes_completed = 0
            self.episode, self.step = -1, 0
            self.board = self.pending = None
            self.environment_counts, self.calls = Counter(), []
            streams.append(self)
        def advance_to(self, age):
            self.calls.append(age)
            if age == 0: return []
            self.teacher.choose(BOARD, self.model.leaf.target_query)
            self.transitions = self.step = age
            self.episodes_started, self.episode = 1, 0
            self.board, self.pending = BOARD, AFTER
            self.environment_counts['sampled_transitions'] = age
            self.model.updates = age-1
            return [dict(seed=self.seed_fn(0), start_step=0, end_step=age, status='ACTIVE')]
    monkeypatch.setattr(runner, 'PolicyComponents', Student)
    monkeypatch.setattr(runner, 'TeacherTDStream', Stream)
    monkeypatch.setattr(runner, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 5))
    monkeypatch.setattr(runner, 'run_episode', lambda *args: pytest.fail('training invoked evaluation'))
    data = runner.train_lifecycle(dict(life=2), tmp_path)
    assert len(streams) == len(students) == 4
    assert all(stream.calls == [0, 5] for stream in streams)
    assert all(not model.weights.flags.writeable for model in students)
    for representation, teachers in data['representations'].items():
        for query, row in teachers.items():
            assert row['teacher_before'] == row['teacher_after']
            assert row['parent_before'] == row['parent_after']
            assert [r['updates'] for r in row['checkpoints']] == [0, 4]
            assert [r['stream_state']['pending'] for r in row['checkpoints']] == [None, AFTER]
            assert row['teacher_counts'] == {'teacher_calls': 1}
            with gzip.open(tmp_path/row['training_trace'], 'rt') as stream:
                rows = [json.loads(line) for line in stream]
            assert len(rows) == 1 and rows[0]['seed'] == runner.train_seed(2, representation, query, 0)


def test_teacher_uses_own_query_and_zero_alias_checks_all_actions_before_diagnostics(monkeypatch):
    calls = []
    def game(seed, act, probability, limit):
        calls.append(seed)
        assert [act(BOARD, 0), act(WIN_BOARD, 1)] == ['DOWN', 'DOWN']
        return dict(seed=seed, return_score=2052, status='WON', steps_count=2, seconds=0.,
            initial_board=BOARD, initial_spawns=[], final_board=GOAL,
            steps=[dict(action='DOWN', score=score, afterstate=after, spawned_cell=3, spawned_rank=1)
                   for score, after in ((4, AFTER), (2048, GOAL))], work=dict(sampled_transitions=2))
    monkeypatch.setattr(runner, 'run_episode', game)
    leaf = Leaf(); teacher, initial, final = Teacher(leaf), Components(leaf), Components(leaf)
    initial.freeze(); final.freeze()
    row = runner.full_game(teacher, leaf, 1, 'SINGLE', 'risk1', 'risk6', 'TEACHER', 3,
                          initial=initial, final=final)
    assert calls == [runner.evaluation_seed(1, 3)]
    assert row['result']['utility'] == 2052/2048+6
    assert row['result']['policy_counts'] == {'teacher_calls': 2}
    assert row['zero_equivalence']['exact'] and row['zero_equivalence']['counts'] == {'choose_calls': 2}
    assert row['zero_equivalence']['before'] == row['zero_equivalence']['after']
    for method in ('INITIAL_H2', 'LEARNED_H2'):
        assert row['diagnostic']['predictions'][method] == [dict(reward=1.25, success=.5)]
        assert row['diagnostic']['counts'][method] == dict(value_calls=1, component_predictions=2)
        assert row['diagnostic']['before'][method] == row['diagnostic']['after'][method]
    original = initial.choose
    def altered(board, query, depth):
        result = original(board, query, depth); result['action_values']['LEFT']['value'] += .1
        return result
    initial.choose = altered
    with pytest.raises(AssertionError, match='zero own-query H2 differs'):
        runner.full_game(teacher, leaf, 1, 'SINGLE', 'risk1', 'risk1', 'TEACHER', 3,
                         initial=initial, final=final)


def test_physical_roster_runs_teacher_once_and_reuses_initial_own_query(tmp_path, monkeypatch):
    loaded, calls = [], []
    class Loaded(Components):
        @classmethod
        def load(cls, path, leaf, build):
            model = cls(leaf); model.updates = max(0, int(path.stem.rsplit('_', 1)[1])-1)
            loaded.append(model); return model
    def game(actor, leaf, life, representation, teacher_query, query, method, replica, initial=None, final=None):
        assert not leaf.weights.flags.writeable
        if method == 'TEACHER':
            assert query == teacher_query and actor.leaf is leaf
            assert not initial.weights.flags.writeable and not final.weights.flags.writeable
        else:
            assert not actor.weights.flags.writeable
        calls.append((representation, teacher_query, query, method, replica))
        return dict(representation=representation, teacher_query=teacher_query,
                    query=query, method=method, replica=replica)
    monkeypatch.setattr(runner, 'PolicyComponents', Loaded)
    monkeypatch.setattr(runner, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'full_game', game)
    trained = dict(representations={representation: {query: dict(checkpoints=[dict(age=age,
        model_ref=f'{representation}_{query}_{age}.npz') for age in runner.CHECKPOINTS])
        for query in runner.TEACHER_QUERIES} for representation in runner.REPRESENTATIONS})
    data = runner.evaluate_lifecycle(dict(life=1), trained, tmp_path)
    assert len(calls) == len(set(calls)) == 384
    assert Counter(row[3] for row in calls) == dict(TEACHER=64, INITIAL_H2=128, LEARNED_H2=192)
    assert not any(method == 'INITIAL_H2' and query == teacher_query
                   for _, teacher_query, query, method, _ in calls)
    assert len(loaded) == 8 and all(not model.weights.flags.writeable for model in loaded)
    with gzip.open(tmp_path/data['control_trace'], 'rt') as stream:
        assert len(list(stream)) == 384


def test_every_teacher_training_finishes_before_any_holdout_or_diagnostic(tmp_path, monkeypatch):
    source = tmp_path/'source'; source.mkdir()
    (source/'source_capsule.json').write_text(json.dumps(source_fixture()))
    (source/'analysis.json').write_text(json.dumps(dict(complete=True, primary_complete=True, costs={'v135': 2})))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def train(source, directory):
        assert 'outcomes' not in source and not (directory/'frozen_training.json').exists()
        events.append(('train', source['life']))
        return dict(life=source['life'], frozen=True)
    def evaluate(source, trained, directory):
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'frozen' and len(frozen['lifecycles']) == 4
        assert sum(event[0] == 'train' for event in events) == 4 and trained['frozen']
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
