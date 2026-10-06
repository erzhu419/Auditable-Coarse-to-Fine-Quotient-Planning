"""Finite source, freeze-order and paired-control runner checks."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_program_planning_v140 as runner


ROOT = Path(__file__).resolve().parents[1]
FIT_WORK = []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_program_planning_v140.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        fit_work=FIT_WORK, environment_samples=0, environment_random_draws=0,
        native_model_calls=0, model_updates=0,
        scope='Mocked source pairing, fixed prefix fitting, random seeds, action context and all-history freeze order.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, counts={}, leaves={},
        training_windows=f'/retained/V138/life_{life}.jsonl.gz',
        episodes=[dict(episode=i, seed=100+i, windows=1, transitions=2, status='LOST')
            for i in range(64)]) for life in runner.LIVES], inherited_costs={'old': 1})
    run = dict(status='complete', lifecycles=[dict(life=life,
        snapshots=[dict(age=age, FACTORED=dict(path=f'train_{life}/FACTORED_{age}.json',
            summary=dict(num_programs=age), bytes=age*10)) for age in runner.AGES])
        for life in runner.LIVES], eval_lifecycles=['not a training source'])
    analysis = dict(complete=True, primary_complete=True, costs={'previous': 2})
    return capsule, run, analysis


def window(episode=0):
    return dict(episode=episode, seed=100+episode, start_step=32,
        root=[1]+[0]*15, actions=['LEFT', 'UP'],
        spawns=[dict(cell=1, rank=2), None],
        expected=dict(scores=[4, 999], exit_board='must not supervise an unobserved action'))


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


class Rule:
    calls = []
    @classmethod
    def from_payload(cls, payload): return cls()
    def to_payload(self): return dict(frozen=True)
    def swipe(self, board, action, work):
        Rule.calls.append((board, action))
        work['mock_recorded_swipes'] += 1
        return (3,)+(0,)*15, 4, True


def test_source_keeps_training_windows_and_final_factored_libraries_in_place():
    capsule, run, analysis = source_fixture()
    extracted = runner.extract_source(capsule, run, analysis)
    assert extracted['inherited_costs'] == dict(old=1, v139_experiment={'previous': 2})
    for source, original, trained in zip(extracted['snapshots'], capsule['snapshots'], run['lifecycles']):
        assert source['training_windows'] == original['training_windows']
        assert source['episodes'] == original['episodes']
        reference = trained['snapshots'][-1]['FACTORED']
        assert source['factored_ref'] == str((runner.SOURCE/reference['path']).resolve())
        assert source['factored_summary'] == reference['summary']
    extracted['snapshots'][0]['episodes'][0]['windows'] = 99
    assert capsule['snapshots'][0]['episodes'][0]['windows'] == 1
    for key in ('complete', 'primary_complete'):
        incomplete = dict(analysis); incomplete[key] = False
        with pytest.raises(ValueError, match='V139 must be complete'):
            runner.extract_source(capsule, run, incomplete)


def test_training_example_uses_only_first_action_and_actual_spawn_for_second_action_label():
    Rule.calls = []
    record, work = window(), Counter()
    before = deepcopy(record)
    result = runner.training_example(Rule(), record, work)
    assert result == dict(board=[3, 2]+[0]*14, previous_action='LEFT', action='UP')
    assert Rule.calls == [(tuple(record['root']), 'LEFT')]
    assert work == Counter(mock_recorded_swipes=1, recorded_spawn_patches=1)
    assert record == before


def test_training_example_rejects_reachable_mismatched_action_score_or_spawn():
    for changed, score, after in ((False, 4, [0]*16), (True, 8, [0]*16), (True, 4, [1]*16)):
        rule = SimpleNamespace(swipe=lambda *args, changed=changed, score=score, after=after:
            (after, score, changed))
        work = Counter()
        with pytest.raises(ValueError, match='retained training window disagrees'):
            runner.training_example(rule, window(), work)
        assert not work['recorded_spawn_patches']


def test_only_fixed_prefixes_fit_and_random_controls_pair_with_their_own_age(tmp_path, monkeypatch):
    source = runner.extract_source(*source_fixture())['snapshots'][2]
    records, sizes, seeds = [window(i) for i in range(64)], [], []
    fit, randomize = runner.fit_programs, runner.randomize_programs
    def record_fit(examples):
        sizes.append(len(examples))
        result = fit(examples); FIT_WORK.append(result['work']); return result
    def record_random(payload, seed):
        seeds.append((payload['metadata']['examples'], seed))
        return randomize(payload, seed)
    monkeypatch.setattr(runner, 'LearnedDynamics', Rule)
    monkeypatch.setattr(runner.previous.previous, 'read_rows', lambda path: iter(records))
    monkeypatch.setattr(runner, 'fit_programs', record_fit)
    monkeypatch.setattr(runner, 'randomize_programs', record_random)
    monkeypatch.setattr(runner.old, 'run_episode', lambda *args: pytest.fail('training sampled a new game'))
    monkeypatch.setattr(runner.old, 'load_teacher', lambda *args: pytest.fail('training queried a new teacher'))
    result = runner.train_lifecycle(source, tmp_path)
    assert sizes == [1, 8, 64]
    assert seeds == [(age, runner.random_program_seed(2, age)) for age in runner.AGES]
    assert result['examples'] == 64 and result['rule_before'] == result['rule_after']
    assert result['replay_work'] == dict(mock_recorded_swipes=64, recorded_spawn_patches=64)
    rows = read(tmp_path/result['examples_trace'])
    assert [row['episode'] for row in rows] == list(range(64))
    assert all(row['board'] == [3, 2]+[0]*14 and row['action'] == 'UP' for row in rows)
    for snapshot in result['snapshots']:
        learned = json.loads((tmp_path/snapshot['LEARNED']['path']).read_text())
        random = json.loads((tmp_path/snapshot['RANDOM']['path']).read_text())
        assert snapshot['examples'] == learned['metadata']['examples'] == snapshot['age']
        assert random['metadata']['random_seed'] == snapshot['random_seed']
        assert learned['metadata'] == snapshot['LEARNED']['metadata']
        assert learned['work'] == snapshot['LEARNED']['work']
        assert [[node[0] for node in tree] for tree in learned['trees']] == [
            [node[0] for node in tree] for tree in random['trees']]
    assert runner.program_reference(result, 'DIRECT64') == runner.program_reference(result, 'LEARNED64')
    assert runner.program_reference(result, 'RANDOM1') == result['snapshots'][0]['RANDOM']['path']


def test_replay_rejects_changed_episode_order_and_window_count(tmp_path, monkeypatch):
    source = runner.extract_source(*source_fixture())['snapshots'][0]
    monkeypatch.setattr(runner, 'LearnedDynamics', Rule)
    monkeypatch.setattr(runner.previous.previous, 'read_rows', lambda path: iter([window(1)]))
    with pytest.raises(ValueError, match='training prefix order differs'):
        runner.train_lifecycle(source, tmp_path)
    source['life'] = 1; source['episodes'][0]['windows'] = 2
    monkeypatch.setattr(runner.previous.previous, 'read_rows', lambda path: iter([window(0)]))
    with pytest.raises(ValueError, match='training prefix windows differ'):
        runner.train_lifecycle(source, tmp_path)


def test_pair_seeds_and_direct_context_follow_actual_actions_without_environment_rng(monkeypatch):
    environment_calls, plans = [], []
    class Planner:
        def __init__(self, value_kind):
            self.counts = Counter(); self.calls = []; self.value_kind = value_kind
        def choose(self, board, query, **kwargs):
            action = ('LEFT', 'UP')[len(self.calls)]
            self.calls.append((board, query, kwargs)); self.counts['choose_calls'] += 1
            return dict(action=action, value=1., status='ACTIVE', value_kind=self.value_kind,
                action_values={action:dict(value=1.)})
    def game(seed, act, probability, limit):
        environment_calls.append((seed, probability, limit))
        assert [act([i]+[0]*15, i) for i in range(2)] == ['LEFT', 'UP']
        return dict(seed=seed, status='LOST')
    monkeypatch.setattr(runner.old, 'run_episode', game)
    monkeypatch.setattr(runner.old, 'game_result', lambda game, query, work, seconds: dict(work=work))
    monkeypatch.setattr(runner.old, 'compact_trace', lambda game: {})
    for query, method in (('risk1', 'DIRECT64'), ('risk8', 'LEARNED64'),
        ('risk1', 'RANDOM64'), ('risk8', 'H2')):
        kind = 'action_priority' if method == 'DIRECT64' else 'estimated_return'
        planner = Planner(kind); row = runner.play(planner, 2, query, method, 3)
        plans.append((planner, row))
        assert [entry['previous_action'] for entry in row['choices']] == ['DOWN', 'LEFT']
        assert all(entry['value_kind'] == kind for entry in row['choices'])
    assert environment_calls == [(runner.evaluation_seed(2, 3), .1, 2000)]*4
    for planner, row in plans[:3]:
        assert [call[2] for call in planner.calls] == [dict(
            simulation_seed=runner.simulation_seed(2, 3, step), previous_action=previous)
            for step, previous in enumerate(('DOWN', 'LEFT'))]
    assert all(not call[2] for call in plans[-1][0].calls)
    assert all(row['simulation_seed'] is None for row in plans[-1][1]['choices'])
    assert runner.simulation_seed(2, 3, 0) != runner.evaluation_seed(2, 3)
    assert len({runner.simulation_seed(life, replica, step) for life in runner.LIVES
        for replica in range(runner.REPLICAS) for step in (0, 1999)}) == 64


def test_frozen_evaluation_uses_same_query_leaf_and_factors_for_every_method(tmp_path, monkeypatch):
    source = dict(life=0, factored_ref=str(tmp_path/'factors.json'))
    (tmp_path/'factors.json').write_text(json.dumps(dict(factors='retained')))
    snapshots = []
    for age in runner.AGES:
        snapshot = dict(age=age)
        for kind in ('LEARNED', 'RANDOM'):
            path = tmp_path/f'{kind}_{age}.json'
            path.write_text(json.dumps(dict(kind=kind, age=age)))
            snapshot[kind] = dict(path=path.name)
        snapshots.append(snapshot)
    constructors, games, leaves = [], [], []
    class Planner:
        def __init__(self, leaf=None, factors=None, payload=None, **kwargs):
            self.counts, self.setup_counts = Counter(), Counter()
            self.setup_seconds, self.spawn_probabilities = 0., (.9, .1)
            if leaf is not None: constructors.append((leaf, factors, payload, kwargs))
    def teacher(source, rep, query, folder):
        assert rep == 'SINGLE'
        leaf = SimpleNamespace(query=query); leaves.append(leaf)
        return SimpleNamespace(query=query), leaf, Planner(), {}
    def play(planner, life, query, method, replica):
        games.append((life, query, method, replica)); planner.counts['mock_games'] += 1
        return dict(life=life, query=query, method=method, replica=replica)
    monkeypatch.setattr(runner, 'ProgramPlanner', Planner)
    monkeypatch.setattr(runner.old, 'load_teacher', teacher)
    monkeypatch.setattr(runner, 'leaf_state', lambda leaf, parent=False: dict(query=leaf.query, frozen=True))
    monkeypatch.setattr(runner, 'play', play)
    monkeypatch.setattr(runner, 'fit_programs', lambda *args: pytest.fail('evaluation fitted policy programs'))
    result = runner.evaluate_lifecycle(source, dict(snapshots=snapshots), tmp_path)
    assert games == [(0, query, method, replica) for query in runner.QUERIES
        for method in runner.METHODS for replica in range(runner.REPLICAS)]
    assert len(read(tmp_path/result['control_trace'])) == 128
    for index, query in enumerate(runner.QUERIES):
        calls = constructors[index*7:(index+1)*7]
        assert all(call[0] is leaves[index] for call in calls)
        assert all(call[1] == dict(factors='retained') for call in calls)
        assert calls[0][3]['mode'] == 'DIRECT'
        assert all(call[3]['mode'] == 'ROLLOUT' for call in calls[1:])
        assert calls[0][2] == dict(kind='LEARNED', age=64)
        for data in result['queries'][query]['planners'].values():
            assert data['before'] == data['after']
            assert data['policy_payload_unchanged'] and data['factored_payload_unchanged']
            assert data['counts'] == dict(mock_games=8)


def test_all_four_histories_freeze_before_any_evaluation(tmp_path, monkeypatch):
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
        assert frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
        assert len(frozen['lifecycles']) == 4 and trained['frozen']
        assert sum(phase == 'train' for phase, _ in events) == 4
        events.append(('evaluate', source['life'])); return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda *args: None)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'train_lifecycle', train)
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    output = tmp_path/'run'; runner.run(output)
    assert events == [(phase, life) for phase in ('train', 'evaluate') for life in runner.LIVES]
    result = json.loads((output/'run.json').read_text())
    assert result['status'] == 'complete' and len(result['eval_lifecycles']) == 4
    assert result['settings']['physical_games'] == 512
