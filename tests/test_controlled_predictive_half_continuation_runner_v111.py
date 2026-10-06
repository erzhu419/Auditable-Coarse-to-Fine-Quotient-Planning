"""Bind cached half/full controls and dispatch only new half-data continuation."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_half_continuation_v111 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    path=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_half_continuation_runner_v111.checks.json'
    data=json.loads(path.read_text()) if path.exists() else {'attempts':[]}
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        neural_model_fits=0,optimizer_steps=0,neural_candidate_predictions=0,new_environment_transitions=0,
        new_model_prefix_transitions=0,scope='Mock fitting/scoring with actual half payload binding and cached-model reuse.'))
    path.write_text(json.dumps(data,indent=2)+'\n')


def sources(tmp_path,monkeypatch):
    original=tmp_path/'source';training=tmp_path/'training'
    original.mkdir();training.mkdir()
    bank={life:[dict(source_life=life,query=q,episode=e,is_half=e==0) for e in (0,1)
                for q in ('reward','risk_goal')] for life in m.LIVES}
    old=dict(status='complete',settings={},cohort={'roots':[dict(root_id=str(life),life=life) for life in m.LIVES]},
        inherited_work={'V105':{'sampled':2048000}},acquisition_accounting={'retained':True},folds=[],models=[],
        decisions=[{'cached':True}])
    for target in m.LIVES:
        records,data=m.pool_fold(bank,target); source_lives=data['source_lives']
        fold=dict(heldout_life=target,source_lives=source_lives,data_log=data,fit_logs={},model_metadata={})
        for width in m.WIDTHS:
            for stage in ('HALF','FULL'):
                name=f'POOLED_H{width}_{stage}'
                fit=dict(training_roster=data[stage.lower()]['training_roster'],heldout_roster=[],
                    statistics_roster=data['half']['training_roster'],source_lives=source_lives,
                    new_optimizer_steps=1000,inherited_parameter_steps=1000 if stage=='FULL' else 0,
                    initialization='half_parameters' if stage=='FULL' else 'original_initialization',
                    optimizer_state='reset_zero_moments',uniform_gamma=.3)
                payload=dict(hidden=width,checkpoint=256000 if stage=='HALF' else 512000,family='UNIFORM_SHRINK',
                    optimizer_steps=1000,parameters=[[[.1]*width],[0.]*width,[.2]*width],mean=[.5],scale=[1.],uniform_gamma=.3,
                    update=dict(stage=stage,source_lives=source_lives,heldout_life=target,
                        training_roster=fit['training_roster'],statistics_roster=fit['statistics_roster']))
                path=original/f'{target}_{name}.json';path.write_text(json.dumps(payload))
                metadata=dict(path=str(path),hidden=width,source_lives=source_lives,heldout_life=target)
                fold['fit_logs'][name]=fit;fold['model_metadata'][name]=metadata
                old['models'].append(dict(heldout_life=target,method=name,metadata=metadata))
        old['folds'].append(fold)
    (original/'run.json').write_text(json.dumps(old))
    (original/'analysis.json').write_text(json.dumps(dict(primary_complete=True,actual_executed_work={'fits':16})))
    (training/'run.json').write_text(json.dumps(dict(status='complete',allocations=[])))
    monkeypatch.setattr(m,'SOURCE',original);monkeypatch.setattr(m,'TRAIN_SOURCE',training)
    monkeypatch.setattr(m,'snapshot',lambda *a:None)
    monkeypatch.setattr(m,'load_bank',lambda *a:(deepcopy(bank),dict(checks={'bound':True})))
    return old


def fitted(records,width,lives,half):
    payload=deepcopy(half)
    model=SimpleNamespace(checkpoint=256000,parameter_count=123*width,to_payload=lambda:deepcopy(payload))
    log=dict(stage='HALF_CONTINUED',source_lives=lives,statistics_roster=half['update']['statistics_roster'],
        training_roster=half['update']['training_roster'],optimizer_state='reset_zero_moments',
        new_optimizer_steps=1000,inherited_parameter_steps=1000,parameter_lineage_steps=2000,checks={'bound':True})
    return model,log


def test_dispatches_only_eight_new_controls_and_preserves_all_cached_rows(tmp_path,monkeypatch):
    old=sources(tmp_path,monkeypatch);calls=[]
    def fit(records,width,lives,half):
        target=half['update']['heldout_life']
        assert target not in lives and {r['source_life'] for r in records}==set(lives)
        calls.append((target,width));return fitted(records,width,lives,half)
    def score(models,roots):
        assert len(models)==8 and {r['method'] for r in models}==set(m.NEW_METHODS)
        assert roots==old['cohort']['roots']
        return [{'new':True}]*8,dict(counts={},checks={'bound':True})
    monkeypatch.setattr(m,'fit_continuation',fit);monkeypatch.setattr(m,'score_models',score)
    out=tmp_path/'out';m.run(out);result=json.loads((out/'run.json').read_text())
    assert calls==[(life,h) for life in m.LIVES for h in m.WIDTHS]
    assert result['status']=='complete' and all(result['runner_checks'].values())
    assert result['models'][:16]==old['models'] and result['decisions'][:1]==old['decisions']
    assert result['inherited_folds']==old['folds'] and result['input_counts']['pooled_half_payload_files_read']==8
    assert result['inherited_work']['V110']=={'fits':16}


@pytest.mark.parametrize('wrong',('half_target','full_steps'))
def test_mismatched_inherited_control_stops_before_any_fit(tmp_path,monkeypatch,wrong):
    old=sources(tmp_path,monkeypatch)
    if wrong=='half_target':
        path=Path(old['folds'][0]['model_metadata']['POOLED_H4_HALF']['path'])
        payload=json.loads(path.read_text());payload['update']['heldout_life']=12;path.write_text(json.dumps(payload))
    else:
        old['folds'][0]['fit_logs']['POOLED_H4_FULL']['new_optimizer_steps']=500
        (m.SOURCE/'run.json').write_text(json.dumps(old))
    monkeypatch.setattr(m,'fit_continuation',lambda *a:pytest.fail('mismatched control fitted'))
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='inherited pooled half or full'):
        m.run(out)
    result=json.loads((out/'run.json').read_text())
    assert not all(result['runner_checks'].values()) and result['folds'][0]['fit_logs']=={}


def test_changed_statistics_retains_failed_fit_without_scoring(tmp_path,monkeypatch):
    sources(tmp_path,monkeypatch)
    def fit(*args):
        model,log=fitted(*args);payload=model.to_payload();payload['uniform_gamma']=.9
        model.to_payload=lambda:payload;return model,log
    monkeypatch.setattr(m,'fit_continuation',fit)
    monkeypatch.setattr(m,'score_models',lambda *a:pytest.fail('wrong statistics scored'))
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='frozen data'):
        m.run(out)
    result=json.loads((out/'run.json').read_text())
    assert not result['runner_checks']['half_statistics_frozen']
    assert len(result['folds'][0]['fit_logs'])==1 and len(list(out.glob('heldout_*/*_model.json')))==1
