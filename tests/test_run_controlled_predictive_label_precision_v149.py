"""Synthetic V149 wiring checks; no native planning or environment samples."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_label_precision_v149 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v149_runtime_tmp'
MOCK_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_samples=0, model_samples=0,
        real_training_updates=0, synthetic_work=dict(MOCK_WORK),
        scope='Synthetic retained labels and mocked learners/workers; no native execution.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder: yield Path(folder)


def synthetic_inputs():
    roots, same, snapshots, traces, files = [], [], [], {}, {}
    old_index = 0
    for life in runner.LIVES:
        refs = {q: {m: f'model:{life}:{q}:{m}' for m in ('ZERO', 'UPDATED')} for q in runner.QUERIES}
        snapshots.append(dict(life=life, training_trace_ref=f'trace:{life}', reference_models=refs,
            leaves={q: dict(SINGLE=dict(model_ref=f'leaf:{life}:{q}')) for q in runner.QUERIES}))
        traces[f'trace:{life}'] = []
        for query in runner.QUERIES:
            for method, path in refs[query].items(): files[path] = dict(method=method, frozen=True)
            for origin in ('OLD', 'NEW'):
                for replica in range(4):
                    for slot in range(4):
                        active = origin == 'NEW' or old_index < 45
                        if origin == 'OLD': old_index += 1
                        key = f'{origin}:{life}:{query}:{replica}:{slot}'
                        example = dict(root_id=key, life=life, query=query, replica=replica, slot=slot,
                            split='TRAIN', candidate_action='RIGHT' if active else 'LEFT', baseline_action='LEFT',
                            candidate_after=[life, replica, slot, 1]+[0]*12 if active else [0]*16,
                            baseline_after=[0]*16, immediate_difference=.25 if active else 0.,
                            target_total=[-99., -99., -99.], target_tail=[-99., -99., -99.])
                        seeds = [runner.previous.suffix_seed(life, query, origin, replica, slot, s) for s in range(32)] if active else []
                        root = dict(root_id=key, life=life, query=query, origin=origin, replica=replica,
                            slot=slot, board=[1, 1]+[0]*14, example=example,
                            actions=['LEFT', 'RIGHT'] if active else ['LEFT'], suffix_seeds=seeds,
                            predictions=dict(SHARED=dict(estimated_advantage=999.)))
                        (roots if active else same).append(root)
                        for suffix, seed in reversed(list(enumerate(seeds))):
                            branches = {action: dict(result=dict(status='WON',
                                components=[100.+suffix, float(suffix % 2), float(1-suffix % 2)] if action == 'RIGHT' else [100., 0., 0.],
                                environment_counts=dict(sampled_transitions=suffix+1))) for action in root['actions']}
                            traces[f'trace:{life}'].append(dict(root_id=key, suffix=suffix, seed=seed,
                                continuation='H2', branches=branches))
    return dict(snapshots=snapshots, cost_refs=[]), dict(roots=roots, same_action_roots=same,
        excluded_same_action_roots=[r['root_id'] for r in same], prediction_work=[]), traces, files


def test_nested_labels_use_suffix_indices_and_remove_immediate_once(monkeypatch):
    source, cohort, traces, _ = synthetic_inputs(); before = deepcopy(cohort)
    monkeypatch.setattr(runner, 'read_rows', lambda path: traces[str(path)])
    result = runner.build_examples(source, cohort)
    assert cohort == before
    assert result['source_rows_read'] == dict(trace_files=4, paired_records=5536, branch_results=11072)
    assert result['training_budget_views'] == dict(
        TRAIN8=dict(paired_records=1384, physical_branches=2768, sampled_transitions=173*72),
        TRAIN32=dict(paired_records=5536, physical_branches=11072, sampled_transitions=173*1056))
    expected = sorted(cohort['roots']+cohort['same_action_roots'], key=runner.root_order)
    for method, count, score in (('TRAIN8', 8, 3.5), ('TRAIN32', 32, 15.5)):
        rows = result['methods'][method]
        assert len(rows) == 256 and [e['root_id'] for e in rows] == [r['root_id'] for r in expected]
        for example in rows:
            active = example['candidate_action'] != example['baseline_action']
            assert example['target_total'] == ([score, .5, .5] if active else [0., 0., 0.])
            assert example['target_tail'] == ([score-.25, .5, .5] if active else [0., 0., 0.])
            assert example['suffixes'] == (count if active else 0)
        assert sum(e['suffixes'] == 0 for e in rows) == 83


@pytest.mark.parametrize('change,match', [('missing', 'suffix roster'), ('cutoff', 'not terminal')])
def test_incomplete_training_labels_cannot_be_fitted(monkeypatch, change, match):
    source, cohort, traces, _ = synthetic_inputs(); rows = traces['trace:0']
    if change == 'missing': rows.pop()
    else: rows[0]['branches']['LEFT']['result']['status'] = 'CUTOFF'
    monkeypatch.setattr(runner, 'read_rows', lambda path: traces[str(path)])
    with pytest.raises(ValueError, match=match): runner.build_examples(source, cohort)


class Model:
    instances = []
    def __init__(self):
        self.method = None; self.frozen = False; self.updates = 0; self.calls = []
        self.counts, self.setup_counts = Counter(), Counter(mock_constructs=1)
        Model.instances.append(self)
    @classmethod
    def from_payload(cls, payload):
        model = cls(); model.method = payload['method']; model.frozen = payload['frozen']
        model.setup_counts['mock_loads'] += 1
        return model
    def state(self):
        return dict(frozen=self.frozen, updates=self.updates, weights=[] if self.method in (None, 'ZERO') and not self.updates else [[self.method or 'fit', self.updates]])
    def update(self, candidate, baseline, target, alpha):
        assert not self.frozen and self.method is None
        self.calls.append((deepcopy(candidate), deepcopy(baseline), deepcopy(target), alpha))
        self.updates += 1; self.counts['update_calls'] += 1; MOCK_WORK['update_calls'] += 1
    def freeze(self): self.frozen = True
    def to_payload(self):
        assert self.frozen
        return dict(method=self.method, **self.state())
    def predict(self, candidate, baseline):
        assert self.frozen
        self.counts['pair_predictions'] += 1; MOCK_WORK['predictions'] += 1
        return {'ZERO': [0., 0., 0.], 'UPDATED': [2., .25, .5], 'TRAIN8': [1., 0., 0.], 'TRAIN32': [-1., 0., 0.]}[self.method]


class PairedModel(Model):
    pass


class SharedModel(Model):
    pass


def mock_models(monkeypatch):
    Model.instances = []
    monkeypatch.setattr(runner, 'PairedAdvantage', PairedModel)
    monkeypatch.setattr(runner, 'SharedLocalAdvantage', SharedModel)


def test_training_starts_from_zero_keeps_order_and_preserves_references(local_tmp, monkeypatch):
    source, cohort, traces, files = synthetic_inputs()
    monkeypatch.setattr(runner, 'read_rows', lambda path: traces[str(path)])
    examples = runner.build_examples(source, cohort); mock_models(monkeypatch)
    monkeypatch.setattr(runner, 'read', lambda path: deepcopy(files[str(path)]))
    results = [runner.train_lifecycle(snapshot, examples, local_tmp) for snapshot in source['snapshots']]
    assert len(Model.instances) == 32
    for life, result in enumerate(results):
        for qi, query in enumerate(runner.QUERIES):
            models = Model.instances[life*8+qi*4:life*8+qi*4+4]
            for method, model in zip(runner.METHODS, models):
                assert type(model) is (SharedModel if method == 'ZERO' else PairedModel)
                data = result['queries'][query]['models'][method]
                sequence = [e for e in examples['methods'][method] if e['life'] == life and e['query'] == query] if method in runner.TRAIN_METHODS else []
                expected = [(e['candidate_after'], e['baseline_after'], e['target_tail'], .1) for e in sequence]
                assert model.calls == expected*32
                assert data['training_roots'] == [e['root_id'] for e in sequence]
                assert data['frozen_state']['frozen'] and json.loads((local_tmp/data['model_ref']).read_text())['frozen']
                if method in runner.TRAIN_METHODS:
                    assert data['before'] == dict(frozen=False, updates=0, weights=[])
                    assert len(sequence) == 32 and [e['origin'] for e in sequence] == ['OLD']*16+['NEW']*16
                    assert data['fit_counts']['update_calls'] == 1024 and model.method is None
                else:
                    assert data['before'] == data['frozen_state'] and not data['fit_counts']
                    assert model.method == method
    assert sum(m.updates for m in Model.instances) == 16384


def test_evaluation_freezes_four_predictions_and_passes_only_fresh_seeds(local_tmp, monkeypatch):
    _, cohort, _, _ = synthetic_inputs(); before = deepcopy(cohort); trained = []; files = {}
    for life in runner.LIVES:
        data = dict(life=life, queries={})
        for query in runner.QUERIES:
            models = {m: dict(model_ref=f'{life}_{query}_{m}.json') for m in runner.METHODS}
            data['queries'][query] = dict(models=models)
            for method, model in models.items(): files[str(local_tmp/model['model_ref'])] = dict(method=method, frozen=True)
        trained.append(data)
    mock_models(monkeypatch); monkeypatch.setattr(runner, 'read', lambda path: deepcopy(files[str(path)]))
    result = runner.build_evaluation_cohort(cohort, trained, local_tmp)
    assert cohort == before and len(result['prediction_work']) == 32
    assert all(w['state_unchanged'] for w in result['prediction_work'])
    assert sum(m.counts['pair_predictions'] for m in Model.instances) == 173*4
    assert all(type(m) is (SharedModel if m.method == 'ZERO' else PairedModel) for m in Model.instances)
    new_seeds, train_seeds = [], []
    for root in result['roots']+result['same_action_roots']:
        assert set(root['predictions']) == set(runner.METHODS)
        active = len(root['actions']) == 2
        if active:
            assert len(root['suffix_seeds']) == len(root['training_suffix_seeds']) == 32
            assert root['predictions']['ZERO']['estimated_advantage'] == .25
            assert root['predictions']['TRAIN8']['estimated_advantage'] == 1.25
            assert root['predictions']['TRAIN32']['estimated_advantage'] == -.75
            assert root['predictions']['TRAIN8']['selected_h1'] and not root['predictions']['TRAIN32']['selected_h1']
        else:
            assert root['suffix_seeds'] == root['training_suffix_seeds'] == []
            assert all(p['estimated_advantage'] == 0. and not p['selected_h1'] for p in root['predictions'].values())
        new_seeds.extend(root['suffix_seeds']); train_seeds.extend(root['training_suffix_seeds'])
    assert len(set(new_seeds)) == 5536 and not set(new_seeds).intersection(train_seeds)
    assert min(new_seeds) >= 14900000000 and max(new_seeds) < 15000000000


def test_all_fits_and_predictions_persist_before_fresh_acquisition(local_tmp, monkeypatch):
    events = []; source = dict(snapshots=[dict(life=l) for l in runner.LIVES], cost_refs=[], training_cohort_ref='retained')
    evaluation = dict(roots=[dict(life=l, suffix_seeds=[runner.suffix_seed(l, 'risk1', 'NEW', 0, 0, 0)]) for l in runner.LIVES])
    class Pool:
        def __init__(self, **kwargs): assert kwargs == dict(max_workers=4)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args): return SimpleNamespace(result=lambda value=function(*args): value)
    def train(snapshot, examples, directory):
        assert events[0] == 'snapshot' and (directory/'frozen_inputs.json').exists()
        events.append(('train', snapshot['life'])); return dict(life=snapshot['life'])
    def predictions(cohort, trained, directory):
        assert [r['life'] for r in trained] == list(runner.LIVES)
        assert events == ['snapshot']+[('train', l) for l in runner.LIVES]
        events.append('predictions'); return evaluation
    def acquire(snapshot, roots, directory):
        assert 'predictions' in events
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'trained_frozen' and len(frozen['training_lifecycles']) == 4
        assert not frozen['lifecycles'] and json.loads((directory/'cohort.json').read_text()) == evaluation
        assert roots == [evaluation['roots'][snapshot['life']]]
        events.append(('acquire', snapshot['life'])); return dict(life=snapshot['life'])
    monkeypatch.setattr(runner, 'read', lambda path: {})
    monkeypatch.setattr(runner, 'extract_source', lambda *args: source)
    monkeypatch.setattr(runner, 'build_examples', lambda *args: {})
    monkeypatch.setattr(runner, 'snapshot_code', lambda path: events.append('snapshot'))
    monkeypatch.setattr(runner, 'train_lifecycle', train)
    monkeypatch.setattr(runner, 'build_evaluation_cohort', predictions)
    monkeypatch.setattr(runner, 'acquire_lifecycle', acquire)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda tasks: reversed(tasks))
    runner.run(local_tmp/'experiment')
    result = json.loads((local_tmp/'experiment/run.json').read_text())
    assert result['status'] == 'complete' and [r['life'] for r in result['lifecycles']] == list(runner.LIVES)
    assert events == ['snapshot']+[('train', l) for l in runner.LIVES]+['predictions']+[('acquire', l) for l in runner.LIVES]


def test_settings_charge_training_attempts_without_new_training_acquisition():
    settings = runner.settings()
    assert settings['training_suffixes'] == dict(TRAIN8=list(range(8)), TRAIN32=list(range(32)))
    assert settings['training_update_attempts'] == 4*2*2*32*32 == 16384
    assert settings['new_training_environment_samples'] == settings['full_policy_games'] == 0
    assert settings['paired_records'] == 173*32 and settings['physical_branches'] == 173*32*2
    assert settings['total_train_roots'] == settings['disagreement_roots']+settings['same_action_roots'] == 256


def test_source_references_keep_models_and_inherited_acquisition_costs():
    snapshots = [dict(life=l, advantage_models={q: {m: f'{l}:{q}:{m}' for m in ('ZERO', 'UPDATED', 'SHARED')} for q in runner.QUERIES}) for l in runner.LIVES]
    capsule = dict(snapshots=snapshots, source_run_ref='v147/run.json', cost_refs=[dict(path='old_costs', fields=['costs'])])
    before = deepcopy(capsule)
    run = dict(status='complete', lifecycles=[dict(life=l, consequences_trace=f'acquire_{l}/paired.jsonl.gz') for l in runner.LIVES])
    source = runner.extract_source(capsule, run, dict(complete=True, primary_complete=True))
    assert capsule == before and source['reference_run_ref'] == 'v147/run.json'
    assert source['source_run_ref'] == str(runner.SOURCE/'run.json')
    assert source['cost_refs'][0] == capsule['cost_refs'][0]
    assert source['cost_refs'][1] == dict(path=str(runner.SOURCE/'analysis.json'), fields=['costs'])
    for snapshot in source['snapshots']:
        assert 'advantage_models' not in snapshot
        assert snapshot['training_trace_ref'] == str(runner.SOURCE/f'acquire_{snapshot["life"]}/paired.jsonl.gz')
        for query in runner.QUERIES:
            assert snapshot['reference_models'][query] == {m: f'{snapshot["life"]}:{query}:{m}' for m in ('ZERO', 'UPDATED')}
