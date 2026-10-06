"""Synthetic V148 wiring checks; no native planner or physical sampling."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_independent_labels_v148 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v148_runtime_tmp'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_samples=0, model_samples=0, training_updates=0,
        scope='Synthetic full roster and mocked frozen models, branches and workers; no native execution.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder: yield Path(folder)


class Model:
    instances = []
    @classmethod
    def from_payload(cls, payload):
        result = cls(); result.frozen = payload['frozen']; result.method = payload['method']
        result.counts, result.setup_counts = Counter(), Counter(loaded_models=1)
        cls.instances.append(result); return result
    def state(self): return dict(frozen=self.frozen, weights=[self.method])
    def update(self, *args): pytest.fail('remeasurement attempted fitting')
    def predict(self, candidate, baseline):
        assert self.frozen; self.counts['pair_predictions'] += 1
        return {'ZERO': [0., 0., 0.], 'UPDATED': [1., .1, 0.], 'SHARED': [2., .2, 0.]}[self.method]


def synthetic_source():
    files, snapshots = {}, []
    for life in runner.LIVES:
        models = {}
        for query in runner.QUERIES:
            models[query] = {}
            for method in runner.METHODS:
                path = f'model:{life}:{query}:{method}'; models[query][method] = path
                files[path] = dict(frozen=True, method=method)
        snapshots.append(dict(life=life, advantage_models=models))
    for origin in ('OLD', 'NEW'):
        examples, roots, ordinal = [], [], 0
        for life in runner.LIVES:
            for query in runner.QUERIES:
                for replica in range(8):
                    for slot in range(4):
                        disagreement = origin == 'NEW' or ordinal < 45
                        key = f'{origin}:{life}:{query}:{replica}:{slot}'
                        example = dict(root_id=key, life=life, query=query, replica=replica, slot=slot,
                            split='TRAIN' if replica < 4 else 'VALIDATION', candidate_action='RIGHT' if disagreement else 'LEFT',
                            baseline_action='LEFT', candidate_after=[1]+[0]*15, baseline_after=[1]+[0]*15,
                            immediate_difference=.25 if disagreement else 0.)
                        examples.append(example)
                        roots.append(dict(root_id=key, life=life, query=query, replica=replica, slot=slot,
                            board=[1, 1]+[0]*14, suffix_seeds=[(143 if origin == 'OLD' else 145)*100000000+i for i in range(8)]))
                        if replica < 4: ordinal += 1
        files[f'{origin}:examples'] = dict(examples=examples); files[f'{origin}:cohort'] = dict(roots=roots)
    return dict(snapshots=snapshots, old_examples_ref='OLD:examples', new_examples_ref='NEW:examples',
        cohort_refs={o: f'{o}:cohort' for o in ('OLD', 'NEW')}, cost_refs=[]), files


def mock_inputs(monkeypatch, files):
    Model.instances = []
    monkeypatch.setattr(runner, 'read', lambda path: deepcopy(files[str(path)]))
    monkeypatch.setattr(runner, 'PairedAdvantage', Model); monkeypatch.setattr(runner, 'SharedLocalAdvantage', Model)
    monkeypatch.setattr(runner, 'load_teacher', lambda *a: pytest.fail('cohort construction loaded a native planner'))


def test_fixed_train_roster_preserves_same_actions_and_collapsed_features(monkeypatch):
    source, files = synthetic_source(); before = deepcopy(files); mock_inputs(monkeypatch, files)
    cohort = runner.build_cohort(source); active, same = cohort['roots'], cohort['same_action_roots']
    assert (len(active), len(same)) == (173, 83)
    assert Counter(r['origin'] for r in active) == {'OLD': 45, 'NEW': 128}
    assert all(r['example']['split'] == 'TRAIN' and r['replica'] < 4 for r in active+same)
    assert all(r['example']['candidate_after'] == r['example']['baseline_after'] for r in active)
    assert set(Counter((r['origin'], r['life'], r['query'], r['replica']) for r in active+same).values()) == {4}
    assert all(len(r['suffix_seeds']) == 32 and len(r['actions']) == 2 for r in active)
    assert all(not r['suffix_seeds'] and len(r['actions']) == 1 for r in same)
    assert all(r['predictions']['ZERO']['estimated_advantage'] == .25 for r in active)
    assert all(r['predictions'][m]['estimated_advantage'] == 0. for r in same for m in runner.METHODS)
    assert len(Model.instances) == 24 and sum(m.counts['pair_predictions'] for m in Model.instances) == 519
    assert all(w['state_unchanged'] for w in cohort['prediction_work']) and files == before


def test_acquisition_seeds_distinguish_origins_and_never_reuse_old_streams():
    seeds = [runner.suffix_seed(l, q, o, r, j, k) for l in runner.LIVES for q in runner.QUERIES
             for o in ('OLD', 'NEW') for r in range(4) for j in range(4) for k in range(32)]
    assert len(seeds) == len(set(seeds)) == 8192
    assert min(seeds) == 14800000000 and max(seeds) < 14900000000
    assert runner.suffix_seed(0, 'risk1', 'OLD', 0, 0, 0) != runner.suffix_seed(0, 'risk1', 'NEW', 0, 0, 0)


def test_unfrozen_source_model_cannot_start_cohort_prediction(monkeypatch):
    source, files = synthetic_source(); files['model:0:risk1:ZERO']['frozen'] = False; mock_inputs(monkeypatch, files)
    with pytest.raises(ValueError, match='not frozen'): runner.build_cohort(source)


def test_paired_sampling_retains_cutoffs_and_charges_every_branch(local_tmp, monkeypatch):
    calls, teachers = [], []
    def teacher(*args):
        result = SimpleNamespace(counts=Counter(), spawn_probabilities=[.8, .2]); teachers.append(result)
        return {}, {}, result, dict(mock_loads=1)
    def branch(board, action, planner, query, seed, max_steps, p_four):
        calls.append((tuple(board), action, query, seed, max_steps, p_four)); planner.counts['mock_continuations'] += 2
        return dict(seed=seed, first_action=action, result=dict(status='CUTOFF' if action == 'LEFT' else 'WON',
            utility=None if action == 'LEFT' else 1., environment_counts=dict(sampled_transitions=3)))
    monkeypatch.setattr(runner, 'load_teacher', teacher); monkeypatch.setattr(runner, 'leaf_state', lambda *a: {})
    monkeypatch.setattr(runner, 'run_branch', branch)
    roots = [dict(root_id=q, query=q, board=[1, 1]+[0]*14, actions=['LEFT', 'RIGHT'],
        suffix_seeds=[runner.suffix_seed(0, q, 'NEW', 0, 0, k) for k in range(32)]) for q in runner.QUERIES]
    result = runner.acquire_lifecycle(dict(life=0), roots, local_tmp)
    with gzip.open(local_tmp/result['consequences_trace'], 'rt') as stream: rows = [json.loads(line) for line in stream]
    assert len(rows) == 64 and len(calls) == 128
    assert all(call[-2:] == (2000, .1) for call in calls)
    assert all(calls[i][3] == calls[i+1][3] for i in range(0, 128, 2))
    for q in runner.QUERIES:
        cell = result['queries'][q]
        assert cell['paired_records'] == 32 and cell['physical_branches'] == 64
        assert cell['statuses'] == {'CUTOFF': 32, 'WON': 32}
        assert cell['environment_counts'] == {'sampled_transitions': 192}
        assert cell['policy_counts'] == {'mock_continuations': 128}
    assert all(row['branches']['LEFT']['result']['utility'] is None for row in rows)


def test_predictions_and_source_snapshot_are_saved_before_any_worker(local_tmp, monkeypatch):
    events = []; source = dict(snapshots=[dict(life=l) for l in runner.LIVES], cost_refs=[])
    cohort = dict(roots=[dict(life=l, predictions={'ZERO': .25}) for l in runner.LIVES])
    class Pool:
        def __init__(self, **kwargs): assert kwargs == dict(max_workers=4)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args): return SimpleNamespace(result=lambda value=function(*args): value)
    def acquire(snapshot, roots, directory):
        assert events[:2] == ['predictions', 'snapshot']
        assert json.loads((directory/'cohort.json').read_text()) == cohort
        assert json.loads((directory/'frozen_inputs.json').read_text())['status'] == 'frozen'
        assert roots == [dict(life=snapshot['life'], predictions={'ZERO': .25})]
        events.append(snapshot['life']); return dict(life=snapshot['life'])
    monkeypatch.setattr(runner, 'read', lambda path: {})
    monkeypatch.setattr(runner, 'extract_source', lambda *a: source)
    monkeypatch.setattr(runner, 'build_cohort', lambda source: (events.append('predictions') or cohort))
    monkeypatch.setattr(runner, 'snapshot_code', lambda directory: events.append('snapshot'))
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool); monkeypatch.setattr(runner, 'as_completed', lambda tasks: reversed(tasks))
    monkeypatch.setattr(runner, 'acquire_lifecycle', acquire)
    output = local_tmp/'experiment'; runner.run(output)
    assert events == ['predictions', 'snapshot', 0, 1, 2, 3]
    data = json.loads((output/'run.json').read_text())
    assert data['status'] == 'complete' and [x['life'] for x in data['lifecycles']] == list(runner.LIVES)


def test_settings_keep_fixed_budget_without_learning_or_new_policy_games():
    data = runner.settings()
    assert data['suffixes_per_root'] == 32 and data['physical_branches'] == 173*32*2
    assert data['new_training_updates'] == data['full_policy_games'] == 0
    assert data['same_action_roots']+data['disagreement_roots'] == data['total_train_roots'] == 256


def test_source_reference_points_to_v147_models_and_run():
    capsule, _ = synthetic_source(); capsule['source_run_ref'] = '/prior/v145/run.json'
    before = deepcopy(capsule)
    run = dict(status='complete', lifecycles=[dict(life=l, queries={q: dict(models={m:
        dict(model_ref=f'train_{l}/{q}_{m}.json') for m in runner.METHODS}) for q in runner.QUERIES}) for l in runner.LIVES])
    source = runner.extract_source(capsule, run, dict(complete=True, primary_complete=True))
    assert source['source_run_ref'] == str(runner.SOURCE/'run.json') and capsule == before
    assert source['cost_refs'][-1] == dict(path=str(runner.SOURCE/'analysis.json'), fields=['costs'])
    for snapshot in source['snapshots']:
        for q in runner.QUERIES:
            for m in runner.METHODS:
                assert snapshot['advantage_models'][q][m] == str((runner.SOURCE/f'train_{snapshot["life"]}/{q}_{m}.json').resolve())
