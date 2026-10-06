"""Synthetic residual-fold wiring without real teachers or native execution."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts import run_controlled_predictive_module_semantics_v156 as runner
from types import SimpleNamespace

TEMP=Path(__file__).resolve().parents[1]/'reports/v156_runtime_tmp'
SYNTHETIC_WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'runner_checks.json'
    payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,environment_samples=0,native_calls=0,
        production_source_reads=0,synthetic_work=dict(SYNTHETIC_WORK),
        scope='Actual feature arithmetic and residual fits on synthetic boards and action tables.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:
        yield Path(folder)


def synthetic_capsule(folder):
    models=[];roots=[];examples=[]
    for life in range(4):
        for qi,query in enumerate(runner.QUERIES):
            payload=dict(schema='acfqp.root_consequences.v151',radix=11,updates=17+life,frozen=True,
                weights=[[-1,.1,.02,-.01],[0,.003,-.001,.002]])
            ref=f'frozen_models/life_{life}/{query}/OLD.json';path=folder/ref
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload))
            models.append(dict(life=life,query=query,arm='OLD',model_ref=ref,
                frozen_state={k:deepcopy(payload[k]) for k in ('radix','updates','frozen','weights')}))
            for mi,method in enumerate(('H2','LEARN8')):
                for slot,replica in enumerate((0,4,8,12)):
                    board=[life+1,qi+1,mi+1,slot+1,0,slot]+[0]*10
                    root=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,
                        slot=slot,replica=replica,source_seed=15290000000+life*1000000+replica,board=board)
                    roots.append(root)
                    examples.append(dict(root,suffixes=16,targets={
                        'REPAIR_H2':[.25*(slot+mi+1),-.1,.1],'REPAIR_GATE':[-.5*(slot+mi+1),.1,-.1]}))
    return dict(models=models,roots=roots,examples=examples,snapshots=[dict(life=l) for l in range(4)],
        cost_refs=[],retained_training_cost={})


def stub_teachers(monkeypatch):
    class Teacher:
        def __init__(self,query):self.query=query;self.counts=Counter()
        def choose(self,board,query):
            assert query==runner.QUERIES[self.query]
            self.counts['choose_calls']+=1;SYNTHETIC_WORK['teacher_choice_stubs']+=1
            right_wins=self.query=='risk1' or board[5]==0
            values={'RIGHT':dict(value=4. if right_wins else 2.,score=4,afterstate=[0]*12+list(board[:4])),
                'DOWN':dict(value=2. if right_wins else 4.,score=8,afterstate=[0]*8+list(board[:8]))}
            action='RIGHT' if right_wins else 'DOWN'
            return dict(action=action,action_values=values,**deepcopy(values[action]))
    monkeypatch.setattr(runner,'load_teacher',lambda source,representation,query,folder:
        (SimpleNamespace(),SimpleNamespace(),Teacher(query),{}))
    monkeypatch.setattr(runner,'leaf_state',lambda *args:dict(frozen=True))


def feature_fixture(folder,monkeypatch):
    capsule=synthetic_capsule(folder);stub_teachers(monkeypatch)
    features=runner.prepare_features(capsule,folder)
    SYNTHETIC_WORK['old_core_predictions']+=features['old_predictions']
    SYNTHETIC_WORK['local_feature_builds']+=len(features['rows'])
    SYNTHETIC_WORK['semantic_feature_builds']+=len(features['rows'])
    return capsule,features


def count_fits(models):
    SYNTHETIC_WORK['residual_fits']+=len(models)
    SYNTHETIC_WORK['residual_core_updates']+=sum(m['new_updates'] for m in models)


def test_heldout_targets_cannot_change_either_residual_fit_and_old_base_is_fixed(local_tmp,monkeypatch):
    capsule,features=feature_fixture(local_tmp,monkeypatch);fold=runner.build_folds(capsule['roots'])[0]
    features_before=deepcopy(features)
    old_bytes={m['model_ref']:(local_tmp/m['model_ref']).read_bytes() for m in capsule['models']}
    base=runner.fit_models(capsule,[fold],features,local_tmp/'base');count_fits(base)
    changed=deepcopy(capsule)
    for e in changed['examples']:
        if e['root_id'] in fold['heldout_ids']:
            e['targets']={'REPAIR_H2':[100.,1.,-1.],'REPAIR_GATE':[-100.,-1.,1.]}
    held=runner.fit_models(changed,[fold],features,local_tmp/'held_changed');count_fits(held)
    assert [m['frozen_state'] for m in held]==[m['frozen_state'] for m in base]
    changed=deepcopy(capsule)
    next(e for e in changed['examples'] if e['root_id']==fold['train_ids'][0])['targets']['REPAIR_GATE'][0]+=3.
    train=runner.fit_models(changed,[fold],features,local_tmp/'train_changed');count_fits(train)
    for old,new in zip(base,train):
        assert (old['frozen_state']==new['frozen_state'])==(old['arm']=='REPAIR_H2')
    for model in base+held+train:
        assert model['before']==dict(feature_kind=model['representation'],updates=0,frozen=False,weights=[])
        assert model['new_updates']==192 and model['root_ids']==fold['train_ids']
    assert features==features_before
    assert all((local_tmp/ref).read_bytes()==data for ref,data in old_bytes.items())


def test_local_residual_plus_old_matches_the_previous_warm_core_fit(local_tmp,monkeypatch):
    capsule,features=feature_fixture(local_tmp,monkeypatch);fold=runner.build_folds(capsule['roots'])[0]
    residual=runner.fit_models(capsule,[fold],features,local_tmp/'residual');count_fits(residual)
    warm=runner.prior.fit_models(capsule,[fold],local_tmp)
    SYNTHETIC_WORK['warm_core_updates']+=sum(m['new_updates'] for m in warm)
    by_arm={m['arm']:m for m in residual if m['representation']=='LOCAL'}
    feature_index={r['root_id']:r for r in features['rows']}
    for metadata in warm:
        model=runner.RootConsequences.from_payload(json.loads((local_tmp/metadata['model_ref']).read_text()))
        delta=runner.ResidualLMS.from_payload(json.loads((local_tmp/'residual'/by_arm[metadata['arm']]['model_ref']).read_text()))
        for root in capsule['roots']:
            if (root['life'],root['query'])!=(fold['life'],fold['query']):continue
            feature=feature_index[root['root_id']]
            correction=delta.predict(dict(feature['features']['LOCAL']))
            expected=model.predict(root['board'])
            combined=[a+b for a,b in zip(feature['old_prediction']['components'],correction)]
            assert combined==pytest.approx(expected,rel=1e-11,abs=1e-11)
            SYNTHETIC_WORK['residual_predictions']+=1;SYNTHETIC_WORK['warm_core_predictions']+=1


def test_feature_and_model_freezes_precede_all_predictions_and_heldout_roster_is_complete(local_tmp,monkeypatch):
    output=local_tmp/'experiment';events=[];source_holder={};stub_teachers(monkeypatch)
    actual_prepare,actual_fit,actual_evaluate=runner.prepare_features,runner.fit_models,runner.evaluate
    def extract(directory):
        capsule=synthetic_capsule(directory);source_holder['capsule']=deepcopy(capsule)
        source_holder['old_bytes']={m['model_ref']:(directory/m['model_ref']).read_bytes() for m in capsule['models']}
        return capsule
    def prepare(capsule,directory):
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert len(frozen['folds'])==32 and frozen['training']==[] and frozen['evaluation'] is None
        features=actual_prepare(capsule,directory);source_holder['features']=deepcopy(features)
        SYNTHETIC_WORK['old_core_predictions']+=features['old_predictions']
        SYNTHETIC_WORK['local_feature_builds']+=len(features['rows'])
        SYNTHETIC_WORK['semantic_feature_builds']+=len(features['rows'])
        events.append('features');return features
    def fit(capsule,folds,features,directory):
        assert events==['snapshot','features']
        assert json.loads((directory/'frozen_features.json').read_text())==features
        result=actual_fit(capsule,folds,features,directory);count_fits(result);events.append('all_fitted');return result
    def evaluate(capsule,folds,features,models,directory):
        assert events==['snapshot','features','all_fitted'] and len(models)==128
        assert json.loads((directory/'frozen_training.json').read_text())==models
        for model in models:assert json.loads((directory/model['model_ref']).read_text())['frozen']
        rows,work=actual_evaluate(capsule,folds,features,models,directory)
        SYNTHETIC_WORK['residual_predictions']+=sum(m['counts']['predictions'] for m in work['models'])
        events.append('evaluated');return rows,work
    monkeypatch.setattr(runner,'extract_source',extract)
    monkeypatch.setattr(runner,'snapshot_code',lambda *args:events.append('snapshot'))
    monkeypatch.setattr(runner,'prepare_features',prepare)
    monkeypatch.setattr(runner,'fit_models',fit);monkeypatch.setattr(runner,'evaluate',evaluate)
    runner.run(output)
    result=json.loads((output/'run.json').read_text());rows=json.loads((output/'evaluation_rows.json').read_text())
    assert result['status']=='complete' and events==['snapshot','features','all_fitted','evaluated']
    assert len(result['training'])==128 and sum(m['new_updates'] for m in result['training'])==24576
    assert len(rows)==1024 and Counter(r['split'] for r in rows)=={'heldout':256,'train':768}
    roots={r['root_id'] for r in source_holder['capsule']['roots']}
    for representation in ('LOCAL','SEMANTIC'):
        for arm in ('REPAIR_H2','REPAIR_GATE'):
            assert Counter(r['root_id'] for r in rows if r['representation']==representation and r['arm']==arm
                and r['split']=='heldout')=={key:1 for key in roots}
    features=source_holder['features'];cached={r['root_id']:r['old_prediction'] for r in features['rows']}
    assert features['old_predictions']==64 and features['planned_root_queries']==128
    assert all(r['old_prediction']==cached[r['root_id']] for r in rows)
    assert len(result['evaluation']['models'])==128
    assert all(m['before']==m['after'] for m in result['evaluation']['models'])
    for ref,data in source_holder['old_bytes'].items():assert (output/ref).read_bytes()==data
