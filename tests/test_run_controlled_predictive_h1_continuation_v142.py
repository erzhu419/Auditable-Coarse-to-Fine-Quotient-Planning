"""Finite source, pairing and cost checks for the H1-only continuation treatment."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_h1_continuation_v142 as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_h1_continuation_v142.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0, source_refits=0,
        scope='Mocked V141 source references, every retained diagnostic, paired streams, H1-only games, separated work and input freeze.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    root = ROOT/'reports/v142_runtime_tmp'; root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='runner_test_', dir=root) as path:
        yield Path(path)


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, leaves={},
        factored_ref=f'/retained/factors_{life}.json', program_ref=f'/retained/policy_{life}.json',
        baseline_control_trace=f'/retained/v140_{life}.jsonl.gz') for life in runner.LIVES],
        inherited_costs={'prior': 1})
    run = dict(status='complete', eval_lifecycles=[dict(life=life,
        control_trace=f'eval_{life}/control.jsonl.gz', diagnostics_trace=f'eval_{life}/diagnostics.jsonl.gz')
        for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v141': 2})
    return capsule, run, analysis


def choice(action='LEFT'):
    return dict(action=action, value=4., status='ACTIVE', value_kind='estimated_return',
        action_values={name:dict(value=value, afterstate=[rank]+[0]*15, score=0, tail_value=value)
            for name, rank, value in (('LEFT', 1, 4.), ('RIGHT', 2, 3.), ('UP', 3, 2.))})


def diagnostic(query='risk1', replica=0, step=32):
    return dict(life=0, query=query, replica=replica,
        seed=runner.previous.previous.evaluation_seed(0, replica), step=step,
        board=[step//32+1, replica+1]+[0]*14, previous_action='RIGHT',
        simulation_seed=runner.previous.previous.simulation_seed(0, replica, step),
        reference=choice(), probes={'SHALLOW':choice(), 'LEARNED64':choice('UP')})


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def test_source_keeps_old_games_and_diagnostics_as_absolute_references():
    capsule, run, analysis = source_fixture(); frozen = deepcopy(capsule)
    result = runner.extract_source(capsule, run, analysis)
    assert result['inherited_costs'] == dict(prior=1, v141_experiment={'v141': 2})
    for source, old in zip(result['snapshots'], capsule['snapshots']):
        life = source['life']
        assert source['shallow_control_trace'] == str((runner.SOURCE/f'eval_{life}/control.jsonl.gz').resolve())
        assert source['diagnostic_source_trace'] == str((runner.SOURCE/f'eval_{life}/diagnostics.jsonl.gz').resolve())
        for key in ('baseline_control_trace', 'program_ref', 'factored_ref'):
            assert source[key] == old[key]
        assert 'games' not in source and 'diagnostics' not in source
    result['snapshots'][0]['leaves']['changed'] = 1
    assert capsule == frozen


@pytest.mark.parametrize('failed', ['status', 'complete', 'primary_complete'])
def test_incomplete_v141_cannot_start_a_new_experiment(failed):
    capsule, run, analysis = source_fixture()
    if failed == 'status': run[failed] = 'evaluation'
    else: analysis[failed] = False
    with pytest.raises(ValueError, match='V141 must be complete'):
        runner.extract_source(capsule, run, analysis)


def test_probe_uses_retained_stream_and_keeps_all_actions_without_copying_old_probes():
    record = diagnostic('risk8', 5, 96)
    record['simulation_seed'] += 701  # This retained input must win over recomputation.
    frozen = deepcopy(record); calls = []; raw = choice()
    class Planner:
        def __init__(self): self.counts = Counter(prior_control_work=900)
        def choose(self, board, query, **kwargs):
            calls.append((list(board), query, kwargs)); self.counts['choose_calls'] += 1
            return raw
    result = runner.diagnostic_probe(Planner(), record)
    assert calls == [(record['board'], runner.QUERIES['risk8'],
        dict(simulation_seed=record['simulation_seed'], previous_action='RIGHT'))]
    assert set(result['probes']) == {'H1_CONT'} and 'reference' not in result
    assert result['probes']['H1_CONT']['work'] == dict(choose_calls=1)
    assert result['probes']['H1_CONT']['action_values'] == raw['action_values']
    assert result['probes']['H1_CONT']['seconds'] >= 0
    raw['action_values']['RIGHT']['value'] = 99
    result['board'][0] = 99
    assert result['probes']['H1_CONT']['action_values']['RIGHT']['value'] == 3.
    assert record == frozen


def test_only_h1_gets_new_games_and_every_retained_root_is_probed_once(local_tmp, monkeypatch):
    source = dict(life=0, factored_ref=str(local_tmp/'factors.json'),
        program_ref='/never/read/policy.json', baseline_control_trace='/never/read/v140.jsonl.gz',
        shallow_control_trace='/never/read/v141.jsonl.gz', diagnostic_source_trace='/retained/diagnostics.jsonl.gz')
    (local_tmp/'factors.json').write_text(json.dumps(dict(factors='frozen')))
    records = [diagnostic(query, replica, step) for query in reversed(runner.QUERIES)
        for replica in range(8) for step in range(0, 33 if replica%2 else 65, 32)]
    frozen_records = deepcopy(records); reads, controls, calls, leaves = [], [], [], []
    def retained(path):
        reads.append(path); assert path == source['diagnostic_source_trace']
        return iter(records)
    class Planner:
        def __init__(self, leaf, factors, **kwargs):
            self.counts, self.setup_counts = Counter(), Counter(copied=1)
            self.setup_seconds, self.spawn_probabilities = 0., (.9, .1)
            self.query = leaf.query
            assert factors == dict(factors='frozen')
        def choose(self, board, query, **kwargs):
            assert query == runner.QUERIES[self.query]
            calls.append((self.query, list(board), kwargs)); self.counts['choose_calls'] += 1
            return choice()
    def teacher(source, representation, query, folder):
        assert representation == 'SINGLE'
        leaf = SimpleNamespace(query=query); leaves.append(leaf)
        return SimpleNamespace(query=query), leaf, SimpleNamespace(counts=Counter()), dict(copied_leaf=1)
    def play(planner, life, query, method, replica):
        assert method == 'H1_CONT' and planner.query == query
        controls.append((life, query, method, replica)); planner.counts['control_games'] += 1
        return dict(life=life, query=query, method=method, replica=replica)
    monkeypatch.setattr(runner, 'read_rows', retained)
    monkeypatch.setattr(runner, 'H1ContinuationPlanner', Planner)
    monkeypatch.setattr(runner.previous.previous.old, 'load_teacher', teacher)
    monkeypatch.setattr(runner.previous.previous, 'play', play)
    monkeypatch.setattr(runner, 'leaf_state', lambda leaf, parent=False: dict(query=leaf.query, frozen=True))
    monkeypatch.setattr(runner.previous.previous, 'fit_programs', lambda *args: pytest.fail('refitted inherited programs'))
    monkeypatch.setattr(runner.previous.previous.old, 'run_episode', lambda *args: pytest.fail('unexpected natural game'))
    result = runner.evaluate_lifecycle(source, local_tmp)
    assert reads == [source['diagnostic_source_trace']]
    assert controls == [(0, query, 'H1_CONT', replica) for query in runner.QUERIES for replica in range(8)]
    assert len(read(local_tmp/result['control_trace'])) == 16
    output = read(local_tmp/result['diagnostics_trace'])
    ordered = [record for query in runner.QUERIES for record in records if record['query'] == query]
    keys = ('life','query','replica','seed','step','board','previous_action','simulation_seed')
    assert [{key:row[key] for key in keys} for row in output] == [{key:row[key] for key in keys} for row in ordered]
    assert len(calls) == len(records) == result['source_diagnostic_rows_read']
    assert all(set(row['probes']) == {'H1_CONT'} and 'reference' not in row for row in output)
    assert result['baseline_refs'] == dict(H2=source['baseline_control_trace'],
        LEARNED64=source['baseline_control_trace'], SHALLOW=source['shallow_control_trace'])
    for query in runner.QUERIES:
        metadata = result['queries'][query]; n = sum(row['query'] == query for row in records)
        assert metadata['control_work'] == dict(control_games=8)
        assert metadata['diagnostic_work'] == dict(choose_calls=n)
        assert metadata['counts'] == dict(control_games=8, choose_calls=n)
        assert metadata['diagnostic_windows'] == n and metadata['unused_teacher_counts'] == {}
        assert metadata['parent_before'] == metadata['parent_after']
        assert metadata['leaf_before'] == metadata['leaf_after']
    assert result['factored_payload_unchanged'] and records == frozen_records


def test_control_reuses_v140_environment_and_simulation_seed_formulas(monkeypatch):
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
    old = runner.previous.previous
    monkeypatch.setattr(old.old, 'run_episode', episode)
    monkeypatch.setattr(old.old, 'game_result', lambda game, query, work, seconds: dict(work=work))
    monkeypatch.setattr(old.old, 'compact_trace', lambda game: {})
    row = old.play(Planner(), 3, 'risk8', 'H1_CONT', 7)
    assert outer == [(old.evaluation_seed(3, 7), .1, 2000)]
    assert calls == [dict(simulation_seed=old.simulation_seed(3, 7, step), previous_action=prior)
        for step, prior in enumerate(('DOWN', 'LEFT'))]
    assert row['method'] == 'H1_CONT' and row['result']['work'] == dict(choose_calls=2)


def test_freeze_precedes_all_new_evaluations_and_no_training_phase(local_tmp, monkeypatch):
    source = local_tmp/'source'; source.mkdir()
    for name, payload in zip(('source_capsule.json','run.json','analysis.json'), source_fixture()):
        (source/name).write_text(json.dumps(payload))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def evaluate(snapshot, directory):
        frozen = json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
        assert len(json.loads((directory/'source_capsule.json').read_text())['snapshots']) == 4
        assert events[0] == 'code_snapshot'
        events.append(snapshot['life']); return dict(life=snapshot['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda *args: events.append('code_snapshot'))
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    monkeypatch.setattr(runner.previous.previous, 'train_lifecycle', lambda *args: pytest.fail('V142 retrained programs'))
    output = local_tmp/'run'; runner.run(output)
    result = json.loads((output/'run.json').read_text())
    assert events == ['code_snapshot', *runner.LIVES]
    assert result['status'] == 'complete' and [row['life'] for row in result['eval_lifecycles']] == list(runner.LIVES)
    assert result['settings']['new_physical_games'] == 64
    assert result['settings']['inherited_physical_games'] == 192
    assert result['settings']['logical_games'] == 256
