"""Finite orchestration checks for conditional fragment accumulation."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_guarded_fragments_v138 as runner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_guarded_fragments_v138.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0, model_updates=0,
        scope='Mocked source replay, prequential timing, frozen snapshots, paired probes and H2 continuation'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, counts={}, leaves={})
        for life in runner.LIVES], inherited_costs={'old': 1})
    run = dict(status='complete', lifecycles=[dict(life=life, representations=dict(SINGLE=dict(
        risk1=dict(training_trace=f'train_{life}/SINGLE_risk1.jsonl.gz'),
        risk8=dict(training_trace='unused-risk8')), CAPACITY=dict(risk1='unused-capacity')))
        for life in runner.LIVES], eval_lifecycles=['unused-evaluation'])
    analysis = dict(complete=True, primary_complete=True, costs={'prior': 2})
    return capsule, run, analysis


def board(value):
    return [value]+[0]*15


def window(value):
    return dict(start_step=0, root=board(value), actions=['DOWN', 'LEFT'],
        spawns=[dict(cell=1, rank=1), dict(cell=2, rank=2)],
        expected=runner.outcome(board(value+1), [4, 8], 'ACTIVE'))


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


class Cache:
    observed = []
    frozen = False
    exact = False
    def __init__(self, rule):
        self.rule, self.work, self.roots = rule, Counter(), set()
    def lookup(self, root, actions, spawns):
        self.work['lookup_calls'] += 1
        hit = root[0] in self.roots if self.exact else bool(self.roots)
        self.work['hits' if hit else 'misses'] += 1
        return deepcopy(self.expected[tuple(root)]) if hit else None
    def observe(self, root, actions, spawns, expected_exit, expected_scores, status):
        assert not self.frozen, 'evaluation changed a frozen library'
        Cache.observed.append((type(self).__name__, root[0]))
        self.roots.add(root[0]); self.work['observations'] += 1
    def summary(self):
        return dict(num_programs=len(self.roots))
    def to_dict(self):
        self.work['serialized_programs'] += len(self.roots)
        return dict(roots=sorted(self.roots))
    @classmethod
    def from_dict(cls, payload, rule):
        result = cls(rule); result.roots = set(payload['roots']); result.frozen = True
        return result


class Concrete(Cache):
    exact = True


class Teacher:
    def __init__(self): self.counts = Counter()
    def choose(self, state, query):
        assert query == runner.QUERY
        self.counts['choose_calls'] += 1
        if state[0] == 11:
            return dict(action=None, value=1., status='WON', action_values={})
        return dict(action='DOWN', value=float(state[0]), status='ACTIVE', action_values={
            'DOWN': dict(afterstate=board(state[0]+1), score=4, value=float(state[0]), tail_value=.5),
            'LEFT': dict(afterstate=state, score=0, value=-1., tail_value=-1.)})


def mock_teacher(source, rep, query, folder):
    assert rep == 'SINGLE' and query == 'risk1'
    return SimpleNamespace(), SimpleNamespace(rule={}), Teacher(), {}


def patch_models(monkeypatch):
    monkeypatch.setattr(runner, 'GuardedFragmentCache', Cache)
    monkeypatch.setattr(runner, 'ExactConcreteFragmentCache', Concrete)
    monkeypatch.setattr(runner.old, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'leaf_state', lambda model, parent=False: dict(readonly=True, updates=0))


def test_only_selected_teacher_training_refs_and_fixed_roster():
    capsule, run, analysis = source_fixture()
    source = runner.extract_source(capsule, run, analysis)
    assert len(source['snapshots']) == 4
    for row in source['snapshots']:
        assert set(row) == {'life', 'rule', 'models', 'counts', 'leaves', 'training_trace'}
        assert row['training_trace'] == str((runner.SOURCE/f"train_{row['life']}/SINGLE_risk1.jsonl.gz").resolve())
    assert source['inherited_costs'] == dict(old=1, v136_experiment={'prior': 2})
    for flag in ('complete', 'primary_complete'):
        invalid = dict(analysis); invalid[flag] = False
        with pytest.raises(ValueError, match='V136 source must be complete'):
            runner.extract_source(capsule, run, invalid)
    assert runner.settings()['ages'] == [1, 8, 64]
    assert runner.settings()['episodes'] == 64 and runner.settings()['stride'] == 32
    assert runner.settings()['physical_games'] == 4*16 == 64
    assert runner.evaluation_seed(2, 3) == 13800000000+90000000+200000+3


def test_source_and_game_windows_keep_two_spawns_exit_and_winning_score(monkeypatch):
    afterstates = [board(index+2) for index in range(34)]
    afterstates[-1] = board(11)
    record = dict(start_board=board(1), spawned_cells=[15]*34, spawned_ranks=[1]*33+[2],
        actions=['DOWN']*34, scores=[4]*33+[2048], status='WON')
    monkeypatch.setattr(runner, 'reconstruct_episode', lambda row: (afterstates, dict(replay_swipes=34)))
    windows, work = runner.fragments_from_source(record)
    assert [item['start_step'] for item in windows] == [0, 32]
    assert work == dict(replay_swipes=34)
    assert windows[0]['root'] == board(1)
    assert windows[0]['expected'] == runner.outcome(afterstates[1][:-1]+[1], [4, 4], 'ACTIVE')
    assert windows[1]['root'] == afterstates[31][:-1]+[1]
    assert windows[1]['spawns'] == [dict(cell=15, rank=1), dict(cell=15, rank=2)]
    assert windows[1]['expected'] == runner.outcome(board(11)[:-1]+[2], [4, 2048], 'WON')
    states = [record['start_board']]+[after[:-1]+[rank] for after, rank in zip(afterstates, record['spawned_ranks'])]
    game = dict(steps=[dict(board=states[i], action='DOWN', spawned_cell=15,
        spawned_rank=record['spawned_ranks'][i], next_board=states[i+1],
        score=record['scores'][i], status='WON' if i == 33 else 'ACTIVE') for i in range(34)])
    assert runner.fragments_from_game(game) == windows


def test_prequential_predicts_before_reveal_and_first_snapshot_never_changes(tmp_path, monkeypatch):
    patch_models(monkeypatch); Cache.observed = []
    monkeypatch.setattr(runner, 'EPISODES', 2); monkeypatch.setattr(runner, 'AGES', (1, 2))
    records = [dict(episode=i, seed=100+i, status='WON', actions=['DOWN', 'LEFT']) for i in range(3)]
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(records))
    monkeypatch.setattr(runner, 'fragments_from_source', lambda record:
        ([window(record['episode']+1)], dict(replay_swipes=2)))
    monkeypatch.setattr(runner.old, 'run_episode', lambda *args: pytest.fail('training sampled an environment'))
    Cache.expected = {tuple(window(i)['root']): window(i)['expected'] for i in (1, 2)}
    result = runner.train_lifecycle(dict(life=0, training_trace='retained'), tmp_path)
    rows = read(tmp_path/result['training_trace'])
    assert len(rows) == 2 and len(result['episodes']) == 2
    assert not rows[0]['probes']['CONTINUAL']['hit'] and not rows[0]['probes']['CONCRETE']['hit']
    assert rows[0]['probes']['FROZEN1'] is None
    assert rows[1]['probes']['CONTINUAL']['hit'] and rows[1]['probes']['FROZEN1']['hit']
    assert not rows[1]['probes']['CONCRETE']['hit']
    assert Cache.observed == [('Cache', 1), ('Concrete', 1), ('Cache', 2), ('Concrete', 2)]
    for name in ('MODULE', 'CACHE'):
        first = json.loads((tmp_path/result['snapshots'][0][name]['path']).read_text())
        final = json.loads((tmp_path/result['snapshots'][1][name]['path']).read_text())
        assert first['roots'] == [1] and final['roots'] == [1, 2]
    assert result['replay_counts'] == dict(replay_swipes=4)
    assert result['teacher_counts'] == {}
    assert result['leaf_before'] == result['leaf_after'] and result['parent_before'] == result['parent_after']


def test_retained_prefix_does_not_skip_incomplete_episode(tmp_path, monkeypatch):
    patch_models(monkeypatch)
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter([dict(episode=0, status='ACTIVE')]))
    monkeypatch.setattr(runner, 'fragments_from_source', lambda *args: pytest.fail('incomplete episode reconstructed'))
    with pytest.raises(ValueError, match='retained complete prefix'):
        runner.train_lifecycle(dict(life=0, training_trace='retained'), tmp_path)


def test_evaluation_reuses_actual_continuation_and_freezes_all_six_snapshots(tmp_path, monkeypatch):
    patch_models(monkeypatch); Cache.observed = []
    monkeypatch.setattr(runner, 'STRIDE', 2)
    windows = [window(1), window(3)]
    windows[0]['expected'] = runner.outcome(board(3), [4, 4], 'ACTIVE')
    windows[1]['expected'] = runner.outcome(board(11), [4, 2048], 'WON')
    Cache.expected = {tuple(item['root']): item['expected'] for item in windows}
    calls = []
    def game(seed, act, probability, limit):
        calls.append(seed)
        states = [board(i) for i in (1, 2, 3, 4, 11)]
        assert [act(states[i], i) for i in range(4)] == ['DOWN']*4
        steps = [dict(board=states[i], action='DOWN', score=2048 if i == 3 else 4,
            afterstate=states[i+1], spawned_cell=2, spawned_rank=1, next_board=states[i+1],
            status='WON' if i == 3 else 'ACTIVE') for i in range(4)]
        return dict(seed=seed, return_score=2060, status='WON', steps_count=4, seconds=0.,
            initial_board=states[0], initial_spawns=[], final_board=states[-1], steps=steps,
            work=dict(sampled_transitions=4))
    monkeypatch.setattr(runner.old, 'run_episode', game)
    snapshots = []
    for age in runner.AGES:
        refs = {}
        for name in ('MODULE', 'CACHE'):
            path = tmp_path/f'{name}_{age}.json'; path.write_text(json.dumps(dict(roots=[1, 3])))
            refs[name] = dict(path=path.name)
        snapshots.append(dict(age=age, **refs))
    result = runner.evaluate_lifecycle(dict(life=1), dict(snapshots=snapshots), tmp_path)
    assert calls == [runner.evaluation_seed(1, i) for i in range(16)]
    assert not Cache.observed and result['models_before'] == result['models_after']
    assert len(result['models_before']) == 6
    rows = read(tmp_path/result['fragments_trace'])
    assert len(rows) == 32 and len(read(tmp_path/result['control_trace'])) == 16
    for row in rows:
        assert all(value['hit'] and value['correct'] for value in row['probes'].values())
        for name, value in row['probes'].items():
            if name.startswith('MODULE_'):
                assert value['continuation_exact'] and value['continuation_work'] == dict(choose_calls=1)
            else:
                assert 'continuation' not in value
        assert row['reference_work'] == ({} if row['start_step'] == 0 else dict(choose_calls=1))
    assert result['teacher_work'] == dict(control=dict(choose_calls=64),
        continuation=dict(choose_calls=96), terminal_reference=dict(choose_calls=16))
    assert result['teacher_counts'] == dict(choose_calls=176)


def test_continuation_signature_includes_unselected_legal_action_values():
    first = Teacher().choose(board(1), runner.QUERY)
    changed = deepcopy(first); changed['action_values']['LEFT']['value'] -= .1
    assert runner.continuation_choice(first) != runner.continuation_choice(changed)
    assert runner.continuation_choice(Teacher().choose(board(11), runner.QUERY)) == dict(
        action=None, value=1., status='WON', action_values={})


def test_all_histories_frozen_before_first_evaluation(tmp_path, monkeypatch):
    source = tmp_path/'source'; source.mkdir()
    for name, value in zip(('source_capsule.json', 'run.json', 'analysis.json'), source_fixture()):
        (source/name).write_text(json.dumps(value))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def train(source, directory):
        assert not (directory/'frozen_training.json').exists()
        events.append(('train', source['life'])); return dict(life=source['life'], frozen=True)
    def evaluate(source, trained, directory):
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'frozen' and len(frozen['lifecycles']) == 4
        assert sum(phase == 'train' for phase, _ in events) == 4 and trained['frozen']
        events.append(('evaluate', source['life'])); return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda *args: None)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'train_lifecycle', train)
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    output = tmp_path/'run'; runner.run(output)
    assert events == [(phase, life) for phase in ('train', 'evaluate') for life in runner.LIVES]
    assert json.loads((output/'run.json').read_text())['status'] == 'complete'
