"""Grouped holdout wiring with synthetic core fits and no environment sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts import run_controlled_predictive_module_holdout_v155 as runner

TEMP=Path(__file__).resolve().parents[1]/'reports/v155_runtime_tmp'
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
        scope='Real core learner on synthetic labels and locally created synthetic OLD payloads.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:
        yield Path(folder)


def synthetic_capsule(folder):
    models=[];roots=[];examples=[]
    for life in range(4):
        for qi,query in enumerate(runner.QUERIES):
            payload=dict(schema='acfqp.root_consequences.v151',radix=11,updates=17+life,
                frozen=True,weights=[[-1,.1,0.,0.]])
            ref=f'frozen_models/life_{life}/{query}/OLD.json';path=folder/ref
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload))
            models.append(dict(life=life,query=query,arm='OLD',model_ref=ref,
                frozen_state={k:deepcopy(payload[k]) for k in ('radix','updates','frozen','weights')}))
            for mi,method in enumerate(('H2','LEARN8')):
                for slot,replica in enumerate((0,4,8,12)):
                    root=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,
                        source_method=method,slot=slot,replica=replica,
                        source_seed=15290000000+life*1000000+replica,
                        board=[life+1,qi+1,mi+1,slot+1]+[0]*12)
                    roots.append(root)
                    examples.append(dict(root,suffixes=16,targets={
                        'REPAIR_H2':[.25*(slot+mi+1),-.1,.1],
                        'REPAIR_GATE':[-.5*(slot+mi+1),.1,-.1]}))
    return dict(models=models,roots=roots,examples=examples,cost_refs=[],retained_training_cost={})


def count_fits(models):
    SYNTHETIC_WORK['core_fits']+=len(models)
    SYNTHETIC_WORK['core_updates']+=sum(m['new_updates'] for m in models)


def test_folds_hold_out_both_policy_roots_from_the_same_episode(local_tmp):
    capsule=synthetic_capsule(local_tmp);folds=runner.build_folds(capsule['roots'])
    assert len(folds)==32 and len({f['fold_id'] for f in folds})==32
    roots={r['root_id']:r for r in capsule['roots']}
    assert Counter(key for fold in folds for key in fold['heldout_ids'])=={key:1 for key in roots}
    for fold in folds:
        assert len(fold['train_ids'])==6 and len(fold['heldout_ids'])==2
        assert not set(fold['train_ids'])&set(fold['heldout_ids'])
        held=[roots[key] for key in fold['heldout_ids']]
        assert {r['source_method'] for r in held}=={'H2','LEARN8'}
        assert {r['source_seed'] for r in held}=={fold['source_seed']}
        assert {r['replica'] for r in held}=={fold['replica']}
        expected=[r['root_id'] for r in capsule['roots'] if (r['life'],r['query'])==(fold['life'],fold['query'])
            and r['replica']!=fold['replica']]
        assert fold['train_ids']==expected


def test_actual_core_fit_ignores_heldout_labels_but_responds_to_training_target(local_tmp):
    baseline_folder=local_tmp/'baseline';capsule=synthetic_capsule(baseline_folder)
    fold=runner.build_folds(capsule['roots'])[0]
    old_ref=capsule['models'][0]['model_ref'];old_bytes=(baseline_folder/old_ref).read_bytes()
    baseline=runner.fit_models(capsule,[fold],baseline_folder);count_fits(baseline)
    heldout_folder=local_tmp/'heldout_changed';heldout=synthetic_capsule(heldout_folder)
    for example in heldout['examples']:
        if example['root_id'] in fold['heldout_ids']:
            example['targets']={'REPAIR_H2':[100.,1.,-1.],'REPAIR_GATE':[-100.,-1.,1.]}
    heldout_fits=runner.fit_models(heldout,[fold],heldout_folder);count_fits(heldout_fits)
    assert [m['frozen_state'] for m in heldout_fits]==[m['frozen_state'] for m in baseline]
    train_folder=local_tmp/'train_changed';training=synthetic_capsule(train_folder)
    changed=next(e for e in training['examples'] if e['root_id']==fold['train_ids'][0])
    changed['targets']['REPAIR_GATE'][0]+=3.
    train_fits=runner.fit_models(training,[fold],train_folder);count_fits(train_fits)
    assert train_fits[0]['frozen_state']==baseline[0]['frozen_state']
    assert train_fits[1]['frozen_state']!=baseline[1]['frozen_state']
    for collection in (baseline,heldout_fits,train_fits):
        assert len(collection)==2
        for model in collection:
            assert model['before']==capsule['models'][0]['frozen_state']
            assert model['root_ids']==fold['train_ids'] and model['new_updates']==192
            assert model['fit_counts']['update_calls']==192 and model['frozen_state']['frozen']
    assert all((folder/old_ref).read_bytes()==old_bytes for folder in (baseline_folder,heldout_folder,train_folder))


def test_all_real_folds_freeze_before_predictions_and_each_root_is_heldout_once_per_arm(local_tmp,monkeypatch):
    output=local_tmp/'experiment';events=[];source_holder={}
    actual_fit,actual_evaluate=runner.fit_models,runner.evaluate
    def extract(directory):
        capsule=synthetic_capsule(directory);source_holder['capsule']=deepcopy(capsule)
        source_holder['old_bytes']={m['model_ref']:(directory/m['model_ref']).read_bytes() for m in capsule['models']}
        return capsule
    def fit(capsule,folds,directory):
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen' and frozen['folds']==folds and len(folds)==32
        assert frozen['evaluation'] is None and not frozen['training']
        result=actual_fit(capsule,folds,directory);count_fits(result);events.append('all_fitted')
        return result
    def evaluate(capsule,folds,models,directory):
        assert events==['snapshot','all_fitted'] and len(models)==64
        assert json.loads((directory/'frozen_training.json').read_text())==models
        for model in models:
            payload=json.loads((directory/model['model_ref']).read_text())
            assert payload['frozen'] and payload['updates']==model['frozen_state']['updates']
        rows,work=actual_evaluate(capsule,folds,models,directory)
        SYNTHETIC_WORK['core_predictions']+=work['root_predictions'];events.append('evaluated')
        return rows,work
    monkeypatch.setattr(runner,'extract_source',extract)
    monkeypatch.setattr(runner,'snapshot_code',lambda *args:events.append('snapshot'))
    monkeypatch.setattr(runner,'fit_models',fit);monkeypatch.setattr(runner,'evaluate',evaluate)
    runner.run(output)
    result=json.loads((output/'run.json').read_text());rows=json.loads((output/'evaluation_rows.json').read_text())
    assert result['status']=='complete' and events==['snapshot','all_fitted','evaluated']
    assert len(result['training'])==64 and sum(m['new_updates'] for m in result['training'])==12288
    assert len(rows)==512 and Counter(r['split'] for r in rows)=={'train':384,'heldout':128}
    capsule=source_holder['capsule'];root_ids={r['root_id'] for r in capsule['roots']}
    for arm in ('REPAIR_H2','REPAIR_GATE'):
        assert Counter(r['root_id'] for r in rows if r['arm']==arm and r['split']=='heldout')=={key:1 for key in root_ids}
    evaluation=result['evaluation']
    assert len(evaluation['models'])==72 and evaluation['root_predictions']==576
    assert evaluation['new_environment_samples']==evaluation['native_planner_calls']==0
    assert all(m['before']==m['after'] for m in evaluation['models'])
    for ref,original in source_holder['old_bytes'].items():assert (output/ref).read_bytes()==original
