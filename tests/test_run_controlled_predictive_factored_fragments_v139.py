"""Finite source pairing, prequential timing and composed-exit runner checks."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_factored_fragments_v139 as runner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_factored_fragments_v139.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0, model_updates=0,
        scope='Mocked matched windows, prequential lookup, inherited baseline references and frozen composition probes'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, counts={}, leaves={})
        for life in runner.LIVES], inherited_costs={'old': 1})
    run = dict(status='complete', lifecycles=[], eval_lifecycles=['unused-evaluation'])
    for life in runner.LIVES:
        run['lifecycles'].append(dict(life=life, training_trace=f'train_{life}/prequential.jsonl.gz',
            episodes=[dict(episode=i, seed=100+i, windows=1, transitions=2, status='LOST')
                      for i in range(64)], snapshots=[dict(age=age, **{name:dict(
                path=f'train_{life}/{name}_{age}.json', summary=dict(num_programs=age), bytes=age*10)
                for name in ('MODULE', 'CACHE')}) for age in runner.AGES]))
    analysis = dict(complete=True, primary_complete=True, costs={'prior': 2})
    return capsule, run, analysis


def board(value): return [value]+[0]*15


def window(value):
    return dict(start_step=0, root=board(value), actions=['DOWN', 'LEFT'],
        spawns=[dict(cell=1, rank=1), dict(cell=2, rank=2)],
        expected=runner.previous.outcome(board(value+1), [4, 8], 'ACTIVE'))


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


class Rule:
    @classmethod
    def from_payload(cls, payload): return cls()
    def to_payload(self): return dict(frozen=True)


class Cache:
    observed = []
    frozen = False
    def __init__(self, rule):
        self.rule, self.work, self.roots = rule, Counter(), set()
        self.last_components = []
    def lookup(self, root, actions, spawns):
        self.work['lookup_calls'] += 1
        hit = root[0] in self.roots
        self.last_components = list(range(8 if hit else 7))
        self.work['hits' if hit else 'misses'] += 1
        return deepcopy(self.expected[tuple(root)]) if hit else None
    def observe(self, root, actions, spawns, expected_exit, expected_scores, status):
        assert not self.frozen, 'evaluation changed a frozen library'
        Cache.observed.append((type(self).__name__, root[0]))
        self.roots.add(root[0]); self.work['observations'] += 1
    def summary(self): return dict(num_programs=len(self.roots))
    def to_dict(self):
        self.work['serialized_programs'] += len(self.roots)
        return dict(roots=sorted(self.roots))
    @classmethod
    def from_dict(cls, payload, rule):
        result = cls(rule); result.roots = set(payload['roots']); result.frozen = True
        return result


class Factored(Cache): pass
class Whole(Cache): pass
class Concrete(Cache): pass


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
    return SimpleNamespace(), SimpleNamespace(rule=Rule()), Teacher(), {}


def patch_models(monkeypatch):
    monkeypatch.setattr(runner, 'FactoredFragmentCache', Factored)
    monkeypatch.setattr(runner, 'KINDS', dict(FACTORED=Factored, WHOLE=Whole, CACHE=Concrete))
    monkeypatch.setattr(runner, 'LearnedDynamics', Rule)
    monkeypatch.setattr(runner.previous.old, 'load_teacher', mock_teacher)
    monkeypatch.setattr(runner, 'leaf_state', lambda model, parent=False: dict(readonly=True, updates=0))


def test_source_keeps_same_windows_and_baseline_snapshots_in_place():
    capsule, run, analysis = source_fixture()
    source = runner.extract_source(capsule, run, analysis)
    assert len(source['snapshots']) == 4
    for actual, trained in zip(source['snapshots'], run['lifecycles']):
        assert actual['training_windows'] == str((runner.SOURCE/trained['training_trace']).resolve())
        assert actual['episodes'] == trained['episodes']
        for new, old in zip(actual['baseline_snapshots'], trained['snapshots']):
            assert new['age'] == old['age']
            for name, previous in (('WHOLE', 'MODULE'), ('CACHE', 'CACHE')):
                assert new[name] == dict(path=str((runner.SOURCE/old[previous]['path']).resolve()),
                    summary=old[previous]['summary'], bytes=old[previous]['bytes'])
    source['snapshots'][0]['episodes'][0]['windows'] = 99
    assert run['lifecycles'][0]['episodes'][0]['windows'] == 1
    assert source['inherited_costs'] == dict(old=1, v138_experiment={'prior': 2})
    for flag in ('complete', 'primary_complete'):
        invalid = dict(analysis); invalid[flag] = False
        with pytest.raises(ValueError, match='V138 must be complete'):
            runner.extract_source(capsule, run, invalid)
    assert runner.settings()['methods'] == ['FACTORED', 'WHOLE', 'CACHE']
    assert runner.settings()['ages'] == [1, 8, 64]
    assert runner.settings()['episodes'] == 64 and runner.settings()['physical_games'] == 64
    assert runner.evaluation_seed(2, 3) == 13900000000+90000000+200000+3


def test_prequential_replay_updates_only_factored_and_preserves_baseline_refs(tmp_path, monkeypatch):
    patch_models(monkeypatch); Cache.observed = []
    monkeypatch.setattr(runner, 'EPISODES', 2); monkeypatch.setattr(runner, 'AGES', (1, 2))
    source = runner.extract_source(*source_fixture())['snapshots'][0]
    records = [dict(episode=i, seed=100+i, **window(i+1), probes='not fitting labels') for i in range(2)]
    monkeypatch.setattr(runner.previous, 'read_rows', lambda path: iter(records))
    monkeypatch.setattr(runner.previous.old, 'run_episode', lambda *args: pytest.fail('training sampled an environment'))
    Cache.expected = {tuple(window(i)['root']): window(i)['expected'] for i in (1, 2)}
    result = runner.train_lifecycle(source, tmp_path)
    rows = read(tmp_path/result['training_trace'])
    assert len(rows) == 2 and len(result['episodes']) == 2
    assert not rows[0]['probes']['FACTORED']['hit'] and rows[0]['probes']['FROZEN1'] is None
    assert not rows[1]['probes']['FACTORED']['hit'] and not rows[1]['probes']['FROZEN1']['hit']
    assert rows[1]['probes']['FACTORED']['components'] == list(range(7))
    assert Cache.observed == [('Factored', 1), ('Factored', 2)]
    for item, baseline in zip(result['snapshots'], source['baseline_snapshots']):
        assert item['WHOLE'] == baseline['WHOLE'] and item['CACHE'] == baseline['CACHE']
        assert not Path(item['WHOLE']['path']).is_relative_to(tmp_path)
        assert not Path(item['CACHE']['path']).is_relative_to(tmp_path)
    first = json.loads((tmp_path/result['snapshots'][0]['FACTORED']['path']).read_text())
    final = json.loads((tmp_path/result['snapshots'][1]['FACTORED']['path']).read_text())
    assert first['roots'] == [1] and final['roots'] == [1, 2]
    assert result['rule_before'] == result['rule_after'] == dict(frozen=True)


def test_source_episode_order_and_matched_window_count_are_required(tmp_path, monkeypatch):
    patch_models(monkeypatch)
    source = runner.extract_source(*source_fixture())['snapshots'][0]
    monkeypatch.setattr(runner.previous, 'read_rows', lambda path: iter([dict(episode=1, **window(1))]))
    with pytest.raises(ValueError, match='fixed64-episode order'):
        runner.train_lifecycle(source, tmp_path)
    source['life'] = 1; source['episodes'][0]['windows'] = 2
    monkeypatch.setattr(runner.previous, 'read_rows', lambda path: iter([dict(episode=0, seed=100, **window(1))]))
    with pytest.raises(ValueError, match='matched source window count differs'):
        runner.train_lifecycle(source, tmp_path)


@pytest.mark.parametrize('covered', [True, False])
def test_frozen_nine_snapshot_probes_only_plan_from_complete_hits(tmp_path, monkeypatch, covered):
    patch_models(monkeypatch); Cache.observed = []
    monkeypatch.setattr(runner.previous, 'STRIDE', 2)
    Cache.expected = {tuple(board(1)): runner.previous.outcome(board(3), [4, 4], 'ACTIVE'),
        tuple(board(3)): runner.previous.outcome(board(11), [4, 2048], 'WON')}
    calls = []
    def game(seed, act, probability, limit):
        calls.append(seed); states = [board(i) for i in (1, 2, 3, 4, 11)]
        assert [act(states[i], i) for i in range(4)] == ['DOWN']*4
        steps = [dict(board=states[i], action='DOWN', score=2048 if i == 3 else 4,
            afterstate=states[i+1], spawned_cell=2, spawned_rank=1, next_board=states[i+1],
            status='WON' if i == 3 else 'ACTIVE') for i in range(4)]
        return dict(seed=seed, return_score=2060, status='WON', steps_count=4, seconds=0.,
            initial_board=states[0], initial_spawns=[], final_board=states[-1], steps=steps,
            work=dict(sampled_transitions=4))
    monkeypatch.setattr(runner.previous.old, 'run_episode', game)
    snapshots = []
    for age in runner.AGES:
        refs = {}
        for name in runner.KINDS:
            roots = ([1, 3] if name == 'FACTORED' and age > 1 else [1]) if covered else []
            path = tmp_path/f'{name}_{age}.json'; path.write_text(json.dumps(dict(roots=roots)))
            refs[name] = dict(path=path.name)
        snapshots.append(dict(age=age, **refs))
    result = runner.evaluate_lifecycle(dict(life=1), dict(snapshots=snapshots), tmp_path)
    assert calls == [runner.evaluation_seed(1, i) for i in range(16)]
    assert not Cache.observed and result['models_before'] == result['models_after']
    assert len(result['models_before']) == 9
    rows = read(tmp_path/result['fragments_trace'])
    assert len(rows) == 32 and len(read(tmp_path/result['control_trace'])) == 16
    for row in rows:
        for name, value in row['probes'].items():
            if value['hit']:
                assert value['correct']
                if not name.startswith('CACHE_'):
                    assert value['continuation_exact'] and value['continuation_work'] == dict(choose_calls=1)
            if not value['hit'] or name.startswith('CACHE_'):
                assert 'continuation' not in value
            if name.startswith('FACTORED_'):
                assert value['components'] == list(range(8 if value['hit'] else 7))
        assert row['reference_work'] == (dict(choose_calls=1) if covered and row['start_step'] == 2 else {})
    expected = dict(control=dict(choose_calls=64), continuation=dict(choose_calls=128),
        terminal_reference=dict(choose_calls=16)) if covered else dict(
            control=dict(choose_calls=64), continuation={}, terminal_reference={})
    assert result['teacher_work'] == expected
    assert result['teacher_counts'] == dict(choose_calls=208 if covered else 64)


def test_all_four_histories_freeze_before_first_probe(tmp_path, monkeypatch):
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
