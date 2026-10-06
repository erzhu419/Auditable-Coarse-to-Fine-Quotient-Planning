"""Finite checks of inherited pairing and the new shallow-only treatment."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_shallow_sampling_v141 as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_shallow_sampling_v141.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0, source_refits=0,
        scope='Mocked retained source references, complete stride diagnostics, paired seeds, shallow-only games and input freeze.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, leaves={},
        factored_ref=f'/retained/factors_{life}.json') for life in runner.LIVES],
        inherited_costs={'prior': 1})
    run = dict(status='complete', lifecycles=[dict(life=life,
        snapshots=[dict(age=age, LEARNED=dict(path=f'train_{life}/LEARNED_{age}.json'))
            for age in (1, 8, 64)]) for life in runner.LIVES],
        eval_lifecycles=[dict(life=life, control_trace=f'eval_{life}/control.jsonl.gz')
            for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v140': 2})
    return capsule, run, analysis


def choice(action='LEFT', after=None):
    after = [0]*16 if after is None else after
    return dict(action=action, value=4., status='ACTIVE', value_kind='estimated_return',
        action_values={a:dict(value=value, afterstate=list(after), score=0, tail_value=value)
            for a, value in (('LEFT', 4.), ('RIGHT', 3.), ('UP', 2.))})


def game(query='risk1', method='H2', replica=0, steps=2, won=False):
    actions = [('LEFT', 'RIGHT', 'UP')[step % 3] for step in range(steps)]
    rows = [choice(action, [step % 10+1]+[0]*15) for step, action in enumerate(actions)]
    cells, ranks = [15]*steps, [1]*steps
    if won:
        rows[-1]['action_values'][actions[-1]]['afterstate'][0] = 11
    return dict(life=0, query=query, method=method, replica=replica,
        seed=runner.previous.evaluation_seed(0, replica), initial_board=[0, 2]+[0]*14,
        actions=actions, choices=rows, spawned_cells=cells, spawned_ranks=ranks)


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def test_source_references_final_programs_and_old_games_without_refitting():
    capsule, run, analysis = source_fixture()
    result = runner.extract_source(capsule, run, analysis)
    assert result['inherited_costs'] == dict(prior=1, v140_experiment={'v140': 2})
    for source in result['snapshots']:
        life = source['life']
        assert source['program_ref'] == str((runner.SOURCE/f'train_{life}/LEARNED_64.json').resolve())
        assert source['baseline_control_trace'] == str((runner.SOURCE/f'eval_{life}/control.jsonl.gz').resolve())
        assert source['factored_ref'] == f'/retained/factors_{life}.json'
    result['snapshots'][0]['leaves']['changed'] = 1
    assert capsule['snapshots'][0]['leaves'] == {}
    for key in ('complete', 'primary_complete'):
        incomplete = dict(analysis); incomplete[key] = False
        with pytest.raises(ValueError, match='V140 must be complete'):
            runner.extract_source(capsule, run, incomplete)


def test_diagnostics_keep_every_fixed_stride_root_and_final_winning_spawn():
    original = game(steps=65, won=True); frozen = deepcopy(original); work = Counter()
    windows = list(runner.diagnostic_windows(original, work))
    assert [window['step'] for window in windows] == [0, 32, 64]
    assert windows[0]['board'] == original['initial_board']
    assert windows[0]['previous_action'] == 'DOWN'
    for window in windows[1:]:
        step = window['step']; expected = [(step-1) % 10+1]+[0]*14+[1]
        assert window['board'] == expected
        assert window['previous_action'] == original['actions'][step-1]
        assert window['simulation_seed'] == runner.previous.simulation_seed(0, 0, step)
        assert window['reference'] == original['choices'][step]
        assert len(window['reference']['action_values']) == 3
    windows[0]['reference']['action_values']['LEFT']['value'] = -99
    windows[0]['board'][0] = 99
    assert original == frozen
    assert work == dict(initial_board_rank_reads=16, retained_afterstate_rank_reads=65*16, recorded_spawn_patches=65)


def test_probe_pairs_model_seeds_and_preserves_all_action_values_and_costs():
    calls = []; raw = choice()
    class Planner:
        def __init__(self): self.counts = Counter(old_work=900)
        def choose(self, board, query, **kwargs):
            calls.append((list(board), query, kwargs)); self.counts['choose_calls'] += 1
            return raw
    left, right = Planner(), Planner()
    arguments = ([1]+[0]*15, 'risk8', 2, 5, 64, 'RIGHT')
    results = [runner.probe(planner, *arguments) for planner in (left, right)]
    assert calls[0] == calls[1]
    assert calls[0][2] == dict(simulation_seed=runner.previous.simulation_seed(2, 5, 64), previous_action='RIGHT')
    assert all(result['work'] == dict(choose_calls=1) for result in results)
    assert all(result['action_values'] == raw['action_values'] for result in results)
    raw['action_values']['RIGHT']['value'] = 99
    assert all(result['action_values']['RIGHT']['value'] == 3. for result in results)


def test_only_shallow_gets_new_games_and_only_old_h2_roots_get_diagnostics(tmp_path, monkeypatch):
    source = dict(life=0, factored_ref=str(tmp_path/'factors.json'),
        program_ref=str(tmp_path/'policy.json'), baseline_control_trace='/retained/old.jsonl.gz')
    for name in ('factors', 'policy'):
        (tmp_path/f'{name}.json').write_text(json.dumps({name: 'frozen'}))
    baseline = [game(query, method, replica) for query in runner.QUERIES
        for method in ('H2', 'LEARNED64', 'RANDOM64') for replica in range(8)]
    constructors, controls, calls, leaves = [], [], [], []
    class Planner:
        def __init__(self, leaf, factors, policy=None, **kwargs):
            self.counts, self.setup_counts = Counter(), Counter(copied=1)
            self.setup_seconds, self.spawn_probabilities = 0., (.9, .1)
            self.kind = 'SHALLOW' if policy is None else 'LEARNED64'
            self.query = leaf.query
            constructors.append((self.kind, leaf, factors, policy, kwargs))
        def choose(self, board, query, **kwargs):
            calls.append((self.kind, self.query, list(board), kwargs))
            self.counts['choose_calls'] += 1
            return choice()
    def teacher(source, representation, query, folder):
        assert representation == 'SINGLE'
        leaf = SimpleNamespace(query=query); leaves.append(leaf)
        return SimpleNamespace(query=query), leaf, SimpleNamespace(counts=Counter()), {}
    def play(planner, life, query, method, replica):
        assert method == planner.kind == 'SHALLOW'
        controls.append((life, query, method, replica)); planner.counts['mock_games'] += 1
        return dict(life=life, query=query, method=method, replica=replica)
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(baseline))
    monkeypatch.setattr(runner, 'ShallowSamplingPlanner', Planner)
    monkeypatch.setattr(runner, 'ProgramPlanner', Planner)
    monkeypatch.setattr(runner.previous.old, 'load_teacher', teacher)
    monkeypatch.setattr(runner.previous, 'play', play)
    monkeypatch.setattr(runner, 'leaf_state', lambda leaf, parent=False: dict(query=leaf.query, frozen=True))
    monkeypatch.setattr(runner.previous, 'fit_programs', lambda *args: pytest.fail('refitted an inherited source'))
    monkeypatch.setattr(runner.previous.old, 'run_episode', lambda *args: pytest.fail('unexpected natural game'))
    result = runner.evaluate_lifecycle(source, tmp_path)
    assert controls == [(0, query, 'SHALLOW', replica) for query in runner.QUERIES for replica in range(8)]
    assert len(read(tmp_path/result['control_trace'])) == 16
    diagnostics = read(tmp_path/result['diagnostics_trace'])
    assert len(diagnostics) == 16 and len(calls) == 32
    assert len(result['baseline_roster']) == 32
    assert result['source_game_rows_read'] == 48
    assert {entry['method'] for entry in result['baseline_roster']} == {'H2', 'LEARNED64'}
    for index, query in enumerate(runner.QUERIES):
        assert all(entry[1] is leaves[index] for entry in constructors[index*2:index*2+2])
        metadata = result['queries'][query]
        assert metadata['control_work'] == dict(mock_games=8)
        assert metadata['diagnostic_work'] == {method:dict(choose_calls=8) for method in ('SHALLOW', 'LEARNED64')}
        assert metadata['unused_teacher_counts'] == {}
        assert metadata['reconstruction_work'] == dict(initial_board_rank_reads=8*16,
            retained_afterstate_rank_reads=16*16, recorded_spawn_patches=16)
        assert metadata['parent_before'] == metadata['parent_after']
        assert metadata['leaf_before'] == metadata['leaf_after']
    assert result['policy_payload_unchanged'] and result['factored_payload_unchanged']
    assert all(row['reference']['action_values'] == baseline[0]['choices'][0]['action_values'] for row in diagnostics)


def test_shallow_play_reuses_v140_environment_and_model_seed_formulas(monkeypatch):
    calls, outer = [], []
    class Planner:
        counts = Counter()
        def choose(self, board, query, **kwargs):
            calls.append(kwargs); self.counts['choose_calls'] += 1
            return choice(('LEFT', 'UP')[len(calls)-1])
    def episode(seed, act, probability, limit):
        outer.append((seed, probability, limit))
        assert [act([0]*16, step) for step in range(2)] == ['LEFT', 'UP']
        return dict(seed=seed)
    monkeypatch.setattr(runner.previous.old, 'run_episode', episode)
    monkeypatch.setattr(runner.previous.old, 'game_result', lambda game, query, work, seconds: dict(work=work))
    monkeypatch.setattr(runner.previous.old, 'compact_trace', lambda game: {})
    row = runner.previous.play(Planner(), 3, 'risk8', 'SHALLOW', 7)
    assert outer == [(runner.previous.evaluation_seed(3, 7), .1, 2000)]
    assert calls == [dict(simulation_seed=runner.previous.simulation_seed(3, 7, step), previous_action=prior)
        for step, prior in enumerate(('DOWN', 'LEFT'))]
    assert row['method'] == 'SHALLOW' and row['result']['work'] == dict(choose_calls=2)


def test_all_inputs_freeze_before_new_games_without_any_training_phase(tmp_path, monkeypatch):
    source = tmp_path/'source'; source.mkdir()
    for name, payload in zip(('source_capsule.json', 'run.json', 'analysis.json'), source_fixture()):
        (source/name).write_text(json.dumps(payload))
    evaluations = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def evaluate(source, directory):
        frozen = json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
        assert len(json.loads((directory/'source_capsule.json').read_text())['snapshots']) == 4
        evaluations.append(source['life']); return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda *args: None)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    monkeypatch.setattr(runner.previous, 'train_lifecycle', lambda *args: pytest.fail('V141 retrained old programs'))
    output = tmp_path/'run'; runner.run(output)
    result = json.loads((output/'run.json').read_text())
    assert evaluations == list(runner.LIVES)
    assert result['status'] == 'complete' and [row['life'] for row in result['eval_lifecycles']] == list(runner.LIVES)
    assert result['settings']['new_physical_games'] == 64
    assert result['settings']['inherited_physical_games'] == 128
