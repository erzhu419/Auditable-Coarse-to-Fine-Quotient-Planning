"""Compact-source, independent LMS, and frozen prediction integration fixtures."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import pytest

from scripts import analyze_controlled_predictive_module_holdout_v155 as audit
from scripts import run_controlled_predictive_module_holdout_v155 as runner
from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences

TEMP=Path(__file__).resolve().parents[1]/'reports/v155_runtime_tmp'
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,native_calls=0,raw_branch_reads=0,
        work=dict(WORK),scope='Synthetic compact source; one fold real LMS plus independent oracle; complete frozen-prediction accounting.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def fixture():
    with TemporaryDirectory(prefix='analyzer_',dir=TEMP) as name:
        directory=Path(name);source=directory/'source';source.mkdir();roots=[];examples=[];models=[];originals=[]
        for life in audit.LIVES:
            for qi,query in enumerate(audit.QUERIES):
                model=RootConsequences();model._weights={-1:(.2+life,.1,0.),17:(.4,0.,-.2)};model.updates=19+life
                model.counts['root_predictions']=71;model.freeze();payload=model.to_payload();WORK['fixture_checkpoint_saves']+=1
                path=source/f'models/{life}/{query}/OLD.json';path.parent.mkdir(parents=True,exist_ok=True);runner.save(path,payload)
                target=directory/f'frozen_models/{life}/{query}/OLD.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
                originals.append(dict(life=life,query=query,model_ref=str(path.relative_to(source)),frozen_state=model.state()))
                models.append(dict(life=life,query=query,arm='OLD',source_model_ref=str(path),model_ref=str(target.relative_to(directory)),
                    frozen_state=model.state(),model_bytes=target.stat().st_size))
                for si,method in enumerate(audit.SOURCES):
                    for slot in range(4):
                        root=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,slot=slot,
                            replica=4*slot,source_seed=15290000000+life*1000000+4*slot,board=[life+1,qi+1,si+1,slot+1]+[0]*12)
                        roots.append(root);examples.append(dict(**{k:root[k] for k in ('root_id','life','query','source_method','slot','board')},
                            suffixes=16,targets={'REPAIR_H2':[slot+.5,-.2,.2],'REPAIR_GATE':[si+slot+.1,.1,-.1]}))
        cost=dict(retained_rows_read=4096,retained_environment_transitions=2017530,new_training_environment_samples=0,
            matched_budget_views={a:2017530 for a in audit.ARMS})
        runner.save(source/'run.json',dict(status='complete',training=dict(examples_ref='training_examples.json',read_work=cost)))
        runner.save(source/'analysis.json',dict(complete=True,primary_complete=True));runner.save(source/'training_examples.json',examples)
        runner.save(source/'source_capsule.json',dict(roots=roots,models=originals))
        capsule=dict(source_run_ref=str(source/'run.json'),source_analysis_ref=str(source/'analysis.json'),source_capsule_ref=str(source/'source_capsule.json'),
            source_examples_ref=str(source/'training_examples.json'),roots=roots,examples=examples,models=models,retained_training_cost=cost,cost_refs=[])
        yield directory,capsule


def test_independent_compact_source_and_grouped_folds_match_frozen_runner(fixture):
    directory,capsule=fixture
    assert audit.expected_settings()==runner.settings()
    models,checks=audit.source_models(capsule,directory);WORK.update(source_model_files_read=16,compact_label_rows_read=64)
    assert all(checks.values()),checks
    expected=audit.expected_folds(capsule['roots']);assert expected==runner.build_folds(capsule['roots']) and len(expected)==32
    indexed={r['root_id']:r for r in capsule['roots']}
    for fold in expected:
        held=[indexed[k] for k in fold['heldout_ids']]
        assert len(fold['train_ids'])==6 and len(held)==2 and {r['source_method'] for r in held}==set(audit.SOURCES)
        assert all(r['replica']==fold['replica'] for r in held)
        assert not(set(fold['train_ids'])&set(fold['heldout_ids']))
    wrong=deepcopy(capsule);wrong['examples'][0]['targets']['REPAIR_GATE'][0]+=1
    _,checks=audit.source_models(wrong,directory);WORK.update(source_model_files_read=16,compact_label_rows_read=64)
    assert not checks['source_labels']


def test_one_actual_fold_matches_independent_warm_lms_and_reset_counters(fixture):
    directory,capsule=fixture;models,checks=audit.source_models(capsule,directory);WORK.update(source_model_files_read=16,compact_label_rows_read=64)
    folds=runner.build_folds(capsule['roots'])[:1];metadata=runner.fit_models(capsule,folds,directory)
    WORK['real_lms_updates']+=384
    fitted,checks=audit.audit_fits(capsule['examples'],folds,metadata,models,directory);WORK['independent_lms_updates']+=384
    assert not checks['fit_model_roster']  # The finite fixture deliberately contains two of the required 64 fits.
    assert all(value for name,value in checks.items() if name!='fit_model_roster'),checks
    assert len(fitted)==2 and all(m['new_updates']==192 for m in metadata)
    assert all(m['frozen_state']['updates']==m['before']['updates']+192 for m in metadata)
    assert all(m['fit_counts']['root_predictions']==192 and m['total_counts']['checkpoint_saves']==1 for m in metadata)
    assert all(m['root_ids']==folds[0]['train_ids'] for m in metadata)


def test_all_readonly_predictions_are_independently_verified_and_old_is_computed_once(fixture):
    directory,capsule=fixture;olds,checks=audit.source_models(capsule,directory);WORK.update(source_model_files_read=16,compact_label_rows_read=64)
    folds=runner.build_folds(capsule['roots']);fitted={};metadata=[]
    for fold in folds:
        for ai,arm in enumerate(audit.ARMS):
            payload=deepcopy(olds[fold['life'],fold['query']]['payload']);model=RootConsequences.from_payload(payload)
            model._weights[-1]=(fold['replica']/10-ai,.1,0.);model.updates+=192;model.freeze()
            ref=f'prediction_models/{fold["life"]}/{fold["query"]}/{fold["replica"]}/{arm}.json';(directory/ref).parent.mkdir(parents=True,exist_ok=True);runner.save(directory/ref,model.to_payload())
            WORK['fixture_checkpoint_saves']+=1
            meta=dict(**{k:fold[k] for k in ('fold_id','life','query','replica')},arm=arm,model_ref=ref,frozen_state=model.state())
            metadata.append(meta);fitted[fold['fold_id'],arm]=dict(metadata=meta,weights=dict(model.weights))
    rows,evaluation=runner.evaluate(capsule,folds,metadata,directory);WORK['real_frozen_predictions']+=576
    checks,work=audit.audit_predictions(capsule,folds,rows,evaluation,olds,fitted);WORK['independent_predictions']+=work['oracle_root_predictions']
    assert all(checks.values()),checks
    assert len(rows)==512 and evaluation['root_predictions']==work['oracle_root_predictions']==576
    assert len(evaluation['models'])==72 and all(r['before']==r['after'] for r in evaluation['models'])
    assert all(r['counts']['root_predictions']==8 for r in evaluation['models'])
    assert Counter(r['split'] for r in rows)=={'train':384,'heldout':128}
    result=audit.aggregate(rows);assert result['primary_complete']
    assert all(result['groups']['heldout'][query]['ALL'][arm]['records']==32 for query in audit.QUERIES for arm in audit.ARMS)
