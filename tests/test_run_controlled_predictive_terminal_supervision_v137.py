"""Finite retained-data and evaluation orchestration fixtures; no real games."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_terminal_supervision_v137 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD, AFTER, WIN_BOARD, GOAL = [1, 1]+[0]*14, [2]+[0]*15, [10, 10]+[0]*14, [11]+[0]*15


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_terminal_supervision_v137.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0, model_updates=0,
        scope='Mocked retained-episode replay, matched updates, frozen models, root-value alias and roster'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def source_fixture():
    capsule = dict(snapshots=[], inherited_costs={'old': 1})
    run = dict(status='complete', lifecycles=[], eval_lifecycles=['never used in fitting'])
    analysis = dict(complete=True, primary_complete=True,
        costs=dict(training=dict(statuses=dict(WON=16, LOST=16, ACTIVE=16))), learners=[])
    for life in runner.LIVES:
        capsule['snapshots'].append(dict(life=life, rule={}, models={}, counts={},
            leaves={query: {rep: dict(model_ref=f'/retained/{life}_{query}_{rep}.npz')
                for rep in runner.REPRESENTATIONS} for query in runner.TEACHER_QUERIES}))
        represented = {}; run['lifecycles'].append(dict(life=life, representations=represented))
        for rep in runner.REPRESENTATIONS:
            represented[rep] = {}
            for query in runner.TEACHER_QUERIES:
                represented[rep][query] = dict(training_trace=f'train_{life}/{rep}_{query}.jsonl.gz',
                    checkpoints=['not a fitting initializer'])
                analysis['learners'].append(dict(life=life, representation=rep, teacher_query=query,
                    updates=5, cost=dict(environment_counts=dict(sampled_transitions=6),
                        statuses=dict(WON=1, LOST=1, ACTIVE=1))))
    return capsule, run, analysis


class Leaf:
    def __init__(self, query='risk1', rep='SINGLE'):
        self.target_query = runner.QUERIES[query]
        self.kind, self.offset, self.updates = 'PRIOR', -1., 524000
        if rep != 'SINGLE': self.representation = rep
        self.weights = np.zeros(1); self.weights.flags.writeable = False
        self.source = SimpleNamespace(weights=self.weights)


def choice(board):
    score, after = (2048, GOAL) if max(board) >= 10 else (4, AFTER)
    values = dict(DOWN=dict(afterstate=after, score=score, value=2., tail_value=2.-score/2048.),
        LEFT=dict(afterstate=BOARD, score=0, value=1., tail_value=1.))
    return dict(action='DOWN', value=2., action_values=values)


class Teacher:
    def __init__(self, leaf):
        self.leaf, self.counts = leaf, Counter()
    def choose(self, board, query):
        assert query == self.leaf.target_query and not self.leaf.weights.flags.writeable
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
        assert not self.weights.flags.writeable
        self.counts['checkpoint_saves'] += 1
        return dict(path=str(path), updates=self.updates, parameter_count=2)
    def choose(self, board, query, depth):
        assert query == self.leaf.target_query and depth == 2 and not self.weights.flags.writeable
        self.counts['choose_calls'] += 1
        result = choice(board)
        for item in result['action_values'].values(): item['consequences'] = [1., .5, .5]
        return result
    def value(self, board):
        assert max(board) < self.radix and not self.weights.flags.writeable
        self.counts.update(value_calls=1, component_predictions=2)
        return dict(reward=1.25, success=.5)


def mock_teacher(source, rep, query, folder):
    leaf = Leaf(query, rep)
    return Leaf(query, rep), leaf, Teacher(leaf), {}


def test_source_uses_retained_training_refs_and_frozen_old_query_roster():
    capsule, previous, analysis = source_fixture()
    source = runner.extract_source(capsule, previous, analysis)
    assert len(source['snapshots']) == 4
    assert all(set(row) == {'life', 'rule', 'models', 'counts', 'leaves', 'training_sources'}
               for row in source['snapshots'])
    refs = [row for snapshot in source['snapshots'] for teachers in snapshot['training_sources'].values()
            for row in teachers.values()]
    assert len(refs) == 16
    assert all(set(row) == {'training_trace', 'source_transitions', 'source_statuses', 'source_updates'}
               for row in refs)
    assert all(Path(row['training_trace']).is_relative_to(runner.SOURCE) for row in refs)
    assert source['inherited_costs'] == dict(old=1, v136_experiment=analysis['costs'])
    source['snapshots'][0]['leaves']['risk1']['SINGLE']['model_ref'] = 'changed'
    assert capsule['snapshots'][0]['leaves']['risk1']['SINGLE']['model_ref'].startswith('/retained/')
    for field in ('complete', 'primary_complete'):
        invalid = deepcopy(analysis); invalid[field] = False
        with pytest.raises(ValueError, match='V136 must be complete'):
            runner.extract_source(capsule, previous, invalid)
    assert tuple(runner.QUERIES) == runner.TEACHER_QUERIES == ('risk1', 'risk8')
    assert runner.settings()['physical_control_games'] == 4*2*2*16*3 == 768
    assert runner.settings()['logical_control_rows'] == 4*2*2*16*4 == 1024
    assert runner.evaluation_seed(2, 3) == 13700000000+90000000+200000+3


def test_both_arms_replay_identical_complete_records_and_exclude_final_active(tmp_path, monkeypatch):
    students, calls = [], []
    class Student(Components):
        def __init__(self, *args):
            super().__init__(*args); students.append(self)
    records = [dict(episode=i, seed=100+i, status=status, start_step=0, end_step=2,
        actions=['DOWN', 'LEFT']) for i, status in enumerate(('WON', 'LOST', 'ACTIVE'))]
    def replay(model, record, arm):
        assert record['status'] in ('WON', 'LOST') and model.weights.flags.writeable
        calls.append((id(model.leaf), arm, record['episode'], id(record)))
        model.updates += len(record['actions'])-int(record['status'] == 'WON')
        model.counts['replay_updates'] += len(record['actions'])-int(record['status'] == 'WON')
        return dict(episode=record['episode'], method=arm, updates=model.updates,
                    td_source_comparison=dict(mismatches=0))
    monkeypatch.setattr(runner.previous, 'PolicyComponents', Student)
    monkeypatch.setattr(runner.previous, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(records))
    monkeypatch.setattr(runner, 'replay_episode', replay)
    monkeypatch.setattr(runner.previous, 'run_episode', lambda *args: pytest.fail('replay sampled an environment'))
    source = runner.extract_source(*source_fixture())['snapshots'][2]
    result = runner.train_lifecycle(source, tmp_path)
    assert len(students) == 8 and all(not model.weights.flags.writeable for model in students)
    assert len(calls) == 16
    for start in range(0, 16, 4):
        block = calls[start:start+4]
        assert [(arm, episode) for _, arm, episode, _ in block] == [('TD', 0), ('TERMINAL', 0), ('TD', 1), ('TERMINAL', 1)]
        assert len({leaf for leaf, *_ in block}) == 1
        assert block[0][3] == block[1][3] and block[2][3] == block[3][3]
    for teachers in result['representations'].values():
        for row in teachers.values():
            assert row['source_counts'] == dict(episodes=3, transitions=6, eligible_episodes=2,
                eligible_transitions=4, eligible_updates=3, excluded_episodes=1, excluded_transitions=2)
            assert row['excluded'] == [{key: records[-1][key] for key in ('episode', 'seed', 'status', 'start_step', 'end_step')}]
            assert row['teacher_before'] == row['teacher_after'] and row['parent_before'] == row['parent_after']
            assert row['teacher_counts'] == {}
            for arm, method in row['methods'].items():
                assert method['checkpoint']['updates'] == 3 and method['final_state']['readonly']
                with gzip.open(tmp_path/method['training_trace'], 'rt') as stream:
                    retained = [json.loads(line) for line in stream]
                assert [(record['episode'], record['method']) for record in retained] == [(0, arm), (1, arm)]


def test_unmatched_update_count_is_a_failed_run(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.previous, 'PolicyComponents', Components)
    monkeypatch.setattr(runner.previous, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter([dict(episode=0, seed=100,
        status='LOST', start_step=0, end_step=2, actions=['DOWN', 'LEFT'])]))
    def replay(model, record, arm):
        model.updates += 2 if arm == 'TD' else 1
        return dict(episode=0, method=arm, td_source_comparison=dict(mismatches=0))
    monkeypatch.setattr(runner, 'replay_episode', replay)
    with pytest.raises(AssertionError, match='eligible updates differ'):
        runner.train_lifecycle(runner.extract_source(*source_fixture())['snapshots'][0], tmp_path)


def test_exact_td_numerical_mismatch_is_retained_then_stops_before_other_arm(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.previous, 'PolicyComponents', Components)
    monkeypatch.setattr(runner.previous, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter([dict(episode=0, seed=100,
        status='LOST', start_step=0, end_step=2, actions=['DOWN', 'LEFT'])]))
    called = []
    def replay(model, record, arm):
        called.append(arm)
        return dict(episode=0, method=arm, td_source_comparison=dict(mismatches=1))
    monkeypatch.setattr(runner, 'replay_episode', replay)
    with pytest.raises(AssertionError, match='TD replay differs'):
        runner.train_lifecycle(runner.extract_source(*source_fixture())['snapshots'][0], tmp_path)
    assert called == ['TD']
    with gzip.open(tmp_path/'train_0/SINGLE_risk1_TD.jsonl.gz', 'rt') as stream:
        assert json.loads(next(stream))['td_source_comparison']['mismatches'] == 1


def test_all_root_values_checked_and_teacher_diagnostic_cost_separate(monkeypatch):
    samples = []
    def game(seed, act, probability, limit):
        samples.append(seed)
        assert [act(BOARD, 0), act(WIN_BOARD, 1)] == ['DOWN', 'DOWN']
        return dict(seed=seed, return_score=2052, status='WON', steps_count=2, seconds=0.,
            initial_board=BOARD, initial_spawns=[], final_board=GOAL,
            steps=[dict(action='DOWN', score=score, afterstate=after, spawned_cell=3, spawned_rank=1)
                   for score, after in ((4, AFTER), (2048, GOAL))], work=dict(sampled_transitions=2))
    monkeypatch.setattr(runner.previous, 'run_episode', game)
    leaf = Leaf('risk8'); actor = Teacher(leaf)
    models = {name: Components(leaf) for name in ('INITIAL_H2', 'TD', 'TERMINAL')}
    for model in models.values(): model.freeze()
    row = runner.full_game(actor, leaf, 1, 'SINGLE', 'risk8', 'TEACHER', 3, models)
    assert samples == [runner.evaluation_seed(1, 3)]
    assert row['query'] == 'risk8' and row['result']['utility'] == 2052/2048+8
    assert row['result']['policy_counts'] == {'teacher_calls': 2}
    assert row['zero_equivalence']['exact'] and row['zero_equivalence']['counts'] == {'choose_calls': 2}
    assert row['zero_equivalence']['before'] == row['zero_equivalence']['after']
    for method in models:
        assert row['diagnostic']['predictions'][method] == [dict(reward=1.25, success=.5)]
        assert row['diagnostic']['counts'][method] == dict(value_calls=1, component_predictions=2)
        assert row['diagnostic']['before'][method] == row['diagnostic']['after'][method]
    original = models['INITIAL_H2'].choose
    def altered(board, query, depth):
        result = original(board, query, depth); result['action_values']['LEFT']['value'] += .1
        return result
    models['INITIAL_H2'].choose = altered
    with pytest.raises(AssertionError, match='initial own-query action values differ'):
        runner.full_game(actor, leaf, 1, 'SINGLE', 'risk8', 'TEACHER', 3, models)


def test_physical_roster_and_models_are_frozen_without_initial_games(tmp_path, monkeypatch):
    loaded, calls = [], []
    class Loaded(Components):
        @classmethod
        def load(cls, path, leaf, build):
            model = cls(leaf); model.updates = 3; loaded.append(model); return model
    def game(actor, leaf, life, rep, teacher, method, replica, models=None):
        assert not leaf.weights.flags.writeable
        if method == 'TEACHER':
            assert actor.leaf is leaf and set(models) == {'INITIAL_H2', 'TD', 'TERMINAL'}
            assert all(not model.weights.flags.writeable for model in models.values())
        else:
            assert models is None and not actor.weights.flags.writeable
        calls.append((rep, teacher, method, replica))
        return dict(representation=rep, teacher_query=teacher, method=method, replica=replica)
    monkeypatch.setattr(runner.previous, 'PolicyComponents', Loaded)
    monkeypatch.setattr(runner.previous, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'full_game', game)
    trained = dict(representations={rep: {teacher: dict(methods={arm: dict(checkpoint=dict(
        model_ref=f'{rep}_{teacher}_{arm}.npz')) for arm in runner.ARMS})
        for teacher in runner.TEACHER_QUERIES} for rep in runner.REPRESENTATIONS})
    data = runner.evaluate_lifecycle(dict(life=1), trained, tmp_path)
    assert len(calls) == len(set(calls)) == 192
    assert Counter(row[2] for row in calls) == dict(TEACHER=64, TD=64, TERMINAL=64)
    assert len(loaded) == 8 and all(not model.weights.flags.writeable for model in loaded)
    with gzip.open(tmp_path/data['control_trace'], 'rt') as stream:
        assert len(list(stream)) == 192


def test_all_training_frozen_before_first_control_or_diagnostic(tmp_path, monkeypatch):
    source = tmp_path/'source'; source.mkdir()
    capsule, run, analysis = source_fixture()
    for filename, value in (('source_capsule.json', capsule), ('run.json', run), ('analysis.json', analysis)):
        (source/filename).write_text(json.dumps(value))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def train(source, directory):
        assert not (directory/'frozen_training.json').exists()
        assert 'training_sources' in source
        events.append(('train', source['life']))
        return dict(life=source['life'], frozen=True)
    def evaluate(source, trained, directory):
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'frozen' and len(frozen['lifecycles']) == 4
        assert sum(phase == 'train' for phase, _ in events) == 4 and trained['frozen']
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
