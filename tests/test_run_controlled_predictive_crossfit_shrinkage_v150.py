"""Synthetic V150 wiring checks; no native planning or environment samples."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_crossfit_shrinkage_v150 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v150_runtime_tmp'
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
        refs = {q: {m: f'model:{life}:{q}:{m}' for m in ('ZERO', 'TRAIN32')} for q in runner.QUERIES}
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
                        seeds = [14800000000+life*1000000+list(runner.QUERIES).index(query)*100000+
                            ('OLD', 'NEW').index(origin)*50000+replica*10000+slot*100+s for s in range(32)] if active else []
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


def test_four_folds_keep_independent_labels_and_remove_immediate_once(monkeypatch):
    source, cohort, traces, _ = synthetic_inputs(); before = deepcopy(cohort)
    monkeypatch.setattr(runner, 'read_rows', lambda path: traces[str(path)])
    result = runner.build_examples(source, cohort)
    assert cohort == before
    assert result['source_rows_read'] == dict(trace_files=4, paired_records=5536, branch_results=11072)
    expected_order = [r['root_id'] for r in sorted(cohort['roots']+cohort['same_action_roots'], key=runner.root_order)]
    for fold in result['folds']:
        held = list(range(8*fold['fold'], 8*fold['fold']+8)); train = [s for s in range(32) if s not in held]
        assert not set(train)&set(held) and sorted(train+held) == list(range(32))
        for name, indices in (('train', train), ('heldout', held)):
            assert [e['root_id'] for e in fold[name]] == expected_order
            for e in fold[name]:
                active = e['candidate_action'] != e['baseline_action']
                mean = sum(indices)/len(indices)
                assert e['target_total'] == ([mean, .5, .5] if active else [0., 0., 0.])
                assert e['target_tail'] == ([mean-.25, .5, .5] if active else [0., 0., 0.])
                assert e['suffix_indices'] == (indices if active else [])
                assert e['suffixes'] == (len(indices) if active else 0)
    # A heldout-only label edit must leave that fold's training labels unchanged.
    changed = deepcopy(traces); row = next(r for r in changed['trace:0'] if r['suffix'] == 0)
    row['branches']['RIGHT']['result']['components'][0] += 80.
    monkeypatch.setattr(runner, 'read_rows', lambda path: changed[str(path)])
    altered = runner.build_examples(source, cohort)
    assert altered['folds'][0]['train'] == result['folds'][0]['train']
    root_id = row['root_id']
    old = next(e for e in result['folds'][0]['heldout'] if e['root_id'] == root_id)
    new = next(e for e in altered['folds'][0]['heldout'] if e['root_id'] == root_id)
    assert new['target_tail'][0] == old['target_tail'][0]+10.


class Model:
    instances = []
    def __init__(self, radix=11):
        self.radix, self.frozen, self.updates, self._weights = radix, False, 0, {}
        self.calls = []; self.counts, self.setup_counts = Counter(), Counter(mock_constructs=1)
        Model.instances.append(self)
    @property
    def weights(self): return self._weights
    @classmethod
    def from_payload(cls, payload):
        model = cls(); model.frozen = payload['frozen']; model.updates = payload.get('updates', 0)
        model._weights = {r[0]: tuple(r[1:]) for r in payload.get('weights', [])}
        model.setup_counts['mock_loads'] += 1
        return model
    def state(self):
        return dict(radix=self.radix, frozen=self.frozen, updates=self.updates,
            weights=[[key, *self._weights[key]] for key in sorted(self._weights)])
    def update(self, candidate, baseline, target, alpha):
        assert not self.frozen
        self.calls.append((deepcopy(candidate), deepcopy(baseline), deepcopy(target), alpha))
        self.updates += 1; self.counts['update_calls'] += 1; MOCK_WORK['update_calls'] += 1
        self._weights[0] = (2., .25, .5)
    def freeze(self): self.frozen = True
    def to_payload(self):
        assert self.frozen
        self.counts['checkpoint_saves'] += 1
        return self.state()
    def predict(self, candidate, baseline):
        assert self.frozen
        self.counts['pair_predictions'] += 1; MOCK_WORK['predictions'] += 1
        return list(self._weights.get(0, (0., 0., 0.)))


class PairedModel(Model): pass
class SharedModel(Model): pass


def mock_models(monkeypatch):
    Model.instances = []
    monkeypatch.setattr(runner, 'PairedAdvantage', PairedModel)
    monkeypatch.setattr(runner, 'SharedLocalAdvantage', SharedModel)


def test_crossfit_order_bindings_calibration_and_no_reference_refit(local_tmp, monkeypatch):
    source, cohort, traces, files = synthetic_inputs()
    for snapshot in source['snapshots']:
        snapshot['control_models'] = snapshot.pop('reference_models')
    for path, payload in files.items():
        payload['weights'] = [] if payload['method'] == 'ZERO' else [[0, -1., 0., 0.]]
        payload['updates'] = 173
    before_files = deepcopy(files)
    monkeypatch.setattr(runner, 'read_rows', lambda path: traces[str(path)])
    examples = runner.build_examples(source, cohort); mock_models(monkeypatch)
    monkeypatch.setattr(runner, 'read', lambda path: deepcopy(files[str(path)]))
    results = [runner.train_lifecycle(snapshot, examples, local_tmp) for snapshot in source['snapshots']]
    trained = [m for m in Model.instances if m.calls]
    assert len(trained) == 32 and sum(m.updates for m in trained) == 32768
    assert sum(m.counts['pair_predictions'] for m in trained) == 173*4
    assert files == before_files
    at = 0
    for life, result in enumerate(results):
        for query in runner.QUERIES:
            qdata = result['queries'][query]
            assert qdata['binding'] == dict(life=life, query=query, continuation='H2', leaf_ref=f'leaf:{life}:{query}')
            pairs = []
            for fold, data in zip(examples['folds'], qdata['folds']):
                train = [e for e in fold['train'] if e['life'] == life and e['query'] == query]
                held = [e for e in fold['heldout'] if e['life'] == life and e['query'] == query]
                assert [e['origin'] for e in train] == ['OLD']*16+['NEW']*16
                assert trained[at].calls == [(e['candidate_after'], e['baseline_after'], e['target_tail'], .1) for e in train]*32
                at += 1
                assert data['training_roots'] == [e['root_id'] for e in train]
                assert data['fit_counts']['update_calls'] == 1024
                assert data['frozen_state'] == data['after_prediction']
                assert data['before'] == dict(radix=11, frozen=False, updates=0, weights=[])
                assert len(data['predictions']) == 32
                for e, p in zip(held, data['predictions']):
                    pairs.append((runner.tail_utility(p['predicted_tail'], query), runner.tail_utility(e['target_tail'], query)))
            assert qdata['calibration'] == runner.calibration(pairs)
            assert qdata['calibration']['rows'] == 128
            for method in ('ZERO', 'TRAIN32'):
                data = qdata['models'][method]
                assert data['before'] == data['frozen_state'] and data['training_roots'] == [] and data['fit_counts'] == {}
            assert qdata['models']['CF']['fit_counts'] == {} and qdata['models']['CF']['training_roots'] == []
            for data in [*qdata['folds'], *qdata['models'].values()]:
                assert json.loads((local_tmp/data['model_ref']).read_text())['frozen']


@pytest.mark.parametrize('rows,numerator,denominator,beta', [
    ([(0., 5.)], 0., 0., 0.), ([(2., -1.), (1., -2.)], -4., 5., 0.),
    ([(2., 1.), (1., .5)], 2.5, 5., .5), ([(2., 6.)], 12., 4., 1.)])
def test_fixed_scalar_rule_clips_only_after_summing_pairs(rows, numerator, denominator, beta):
    assert runner.calibration(rows) == dict(numerator=numerator, denominator=denominator, beta=beta, rows=len(rows))


@pytest.mark.parametrize('beta', [0., .1, 1.])
def test_shrink_preserves_source_and_immediate_but_can_change_gate(monkeypatch, beta):
    mock_models(monkeypatch); source = PairedModel(); source._weights = {0: (-1., 0., 0.)}
    source.updates = 17; source.freeze(); source.counts['retained_count'] = 9
    before, counts, setup = source.state(), dict(source.counts), dict(source.setup_counts)
    shrunk, work = runner.shrink_model(source, beta)
    assert source.state() == before and dict(source.counts) == counts and dict(source.setup_counts) == setup
    assert shrunk.frozen and shrunk.updates == 17 and not shrunk.counts
    assert dict(shrunk.weights) == ({0: (-beta, 0., 0.)} if beta else {})
    assert work == dict(source_weight_addresses=1, scaled_component_parameters=3, output_weight_addresses=int(bool(beta)))
    example = dict(root_id='synthetic', query='risk1', candidate_action='RIGHT', baseline_action='LEFT',
        candidate_after=[1]+[0]*15, baseline_after=[0]*16, immediate_difference=.25)
    base, calibrated = runner.prediction(source, example), runner.prediction(shrunk, example)
    assert base['estimated_advantage'] == -.75 and not base['selected_h1']
    assert calibrated['estimated_advantage'] == pytest.approx(.25-beta)
    assert calibrated['selected_h1'] == (beta < .25)
    example['immediate_difference'] = 0.
    assert not runner.prediction(shrunk, example)['selected_h1']


def test_evaluation_counts_real_gate_changes_and_freezes_fresh_seeds(local_tmp, monkeypatch):
    _, cohort, _, _ = synthetic_inputs(); before = deepcopy(cohort); trained = []; files = {}
    for life in runner.LIVES:
        data = dict(life=life, queries={})
        for query in runner.QUERIES:
            models = {m: dict(model_ref=f'{life}_{query}_{m}.json') for m in runner.METHODS}
            data['queries'][query] = dict(models=models)
            for method, model in models.items():
                files[str(local_tmp/model['model_ref'])] = dict(frozen=True,
                    weights=[] if method == 'ZERO' else [[0, -1. if method == 'TRAIN32' else -.1, 0., 0.]])
        trained.append(data)
    mock_models(monkeypatch); monkeypatch.setattr(runner, 'read', lambda path: deepcopy(files[str(path)]))
    result = runner.build_evaluation_cohort(cohort, trained, local_tmp)
    assert cohort == before and len(result['prediction_work']) == 24
    assert result['gate_changes']['total_vs_train32'] == 173 and result['gate_changes']['total_vs_zero'] == 0
    assert all(w['state_unchanged'] for w in result['prediction_work'])
    assert sum(m.counts['pair_predictions'] for m in Model.instances) == 173*3
    fresh, old = [], []
    for root in result['roots']+result['same_action_roots']:
        assert set(root['predictions']) == set(runner.METHODS)
        if len(root['actions']) == 2:
            assert root['predictions']['CF']['selected_h1'] and not root['predictions']['TRAIN32']['selected_h1']
            assert len(root['suffix_seeds']) == len(root['training_suffix_seeds']) == 32
        else:
            assert root['suffix_seeds'] == root['training_suffix_seeds'] == []
            assert all(p['estimated_advantage'] == 0. and not p['selected_h1'] for p in root['predictions'].values())
        fresh += root['suffix_seeds']; old += root['training_suffix_seeds']
    assert len(set(fresh)) == 5536 and not set(fresh)&set(old)
    assert min(fresh) >= 15000000000 and max(fresh) < 15100000000


@pytest.mark.parametrize('changes,expected_status', [(0, 'no_action_change'), (1, 'complete')])
def test_action_change_condition_and_freeze_precede_any_new_acquisition(local_tmp, monkeypatch, changes, expected_status):
    events = []; source = dict(snapshots=[dict(life=l) for l in runner.LIVES], cost_refs=[], training_cohort_ref='retained')
    evaluation = dict(roots=[dict(life=l, suffix_seeds=[runner.suffix_seed(l, 'risk1', 'NEW', 0, 0, 0)]) for l in runner.LIVES],
        gate_changes=dict(total_vs_train32=changes, total_vs_zero=0, by_life_query=[]))
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
        assert changes and 'predictions' in events
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
    assert result['status'] == expected_status
    assert events == ['snapshot']+[('train', l) for l in runner.LIVES]+['predictions']+([('acquire', l) for l in runner.LIVES] if changes else [])
    assert len(result['lifecycles']) == (4 if changes else 0)


def test_settings_charge_fold_work_and_source_uses_only_v148_labels():
    settings = runner.settings()
    assert settings['training_update_attempts'] == 4*2*4*32*32 == 32768
    assert settings['out_of_fold_prediction_records'] == 1024 and settings['scalar_calibrations'] == 8
    assert settings['new_training_environment_samples'] == settings['full_policy_games'] == 0
    assert settings['physical_branches'] == 173*32*2
    source, _, _, _ = synthetic_inputs(); source['training_cohort_ref'] = 'V148/cohort.json'; before = deepcopy(source)
    trained = [dict(life=l, queries={q: dict(models={m: dict(model_ref=f'train_{l}/{q}_{m}.json')
        for m in ('ZERO', 'TRAIN32')}) for q in runner.QUERIES}) for l in runner.LIVES]
    result = runner.extract_source(source, dict(status='complete', training_lifecycles=trained), dict(complete=True, primary_complete=True))
    assert source == before and result['training_cohort_ref'] == 'V148/cohort.json'
    for snapshot in result['snapshots']:
        life = snapshot['life']; assert snapshot['training_trace_ref'] == f'trace:{life}'
        for query in runner.QUERIES:
            assert snapshot['control_models'][query] == {m: str(runner.SOURCE/f'train_{life}/{query}_{m}.json') for m in ('ZERO', 'TRAIN32')}
