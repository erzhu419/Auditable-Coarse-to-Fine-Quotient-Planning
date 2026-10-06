"""Exercise fold dispatch and excluded-history scoring without new fitting."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_pooled_history_v110 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_pooled_runner_v110.checks.json'
    row = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    row['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        neural_model_fits=0, optimizer_steps=0, neural_candidate_predictions=0,
        new_environment_transitions=0, new_model_prefix_transitions=0,
        scope='Mock model fits/predictions; real fold dispatch, excluded-history filtering and cost aggregation.'))
    path.write_text(json.dumps(row, indent=2) + '\n')


def allocations():
    return [dict(life=life, construction=[dict(budget=b, acquisition=dict(used_transitions=256000,
        cost_partition={'training':{'total_transitions':200000},'heldout':{'total_transitions':50000},
                        'unincorporated':{'total_transitions':6000}})) for b in (256000,512000)]) for life in m.LIVES]


def fixture_source(tmp_path, monkeypatch):
    source, training = tmp_path / 'source', tmp_path / 'training'
    source.mkdir(); training.mkdir()
    previous = dict(status='complete', settings={'budgets':[256000,512000]},
        cohort={'roots':[dict(root_id=f'{life}_reward',life=life,features=[[life]]*5) for life in m.LIVES]})
    previous.update({f'inherited_v{v}_work':{'retained_version':v} for v in range(105,109)})
    (source/'run.json').write_text(json.dumps(previous))
    (source/'analysis.json').write_text(json.dumps(dict(primary_complete=True,actual_executed_work={'retained_version':109})))
    (training/'run.json').write_text(json.dumps(dict(status='complete',allocations=allocations())))
    bank = {life:[dict(source_life=life,query=q,episode=ep,is_half=half) for ep,half in ((0,True),(1,False))
                  for q in ('reward','risk_goal')] for life in m.LIVES}
    monkeypatch.setattr(m,'SOURCE',source);monkeypatch.setattr(m,'TRAIN_SOURCE',training)
    monkeypatch.setattr(m,'snapshot',lambda p:None)
    monkeypatch.setattr(m,'load_bank',lambda *a:(deepcopy(bank),dict(checks={'complete':True},counts={})))
    return previous


def fake_fit(records, hidden, stage, sources, half_payload=None):
    checkpoint=256000 if stage=='HALF' else 512000
    payload=dict(hidden=hidden,checkpoint=checkpoint,family='UNIFORM_SHRINK',optimizer_steps=1000,
        parameters=[[[.1]*hidden],[0.]*hidden,[.2]*hidden],mean=[float(sum(sources))],scale=[1.],uniform_gamma=.3)
    if stage=='FULL':
        assert half_payload is not None and half_payload['update']['heldout_life'] not in sources
        assert half_payload['update']['source_lives']==sources
        payload.update({k:deepcopy(half_payload[k]) for k in ('parameters','mean','scale','uniform_gamma')})
    model=SimpleNamespace(checkpoint=checkpoint,parameter_count=123*hidden,to_payload=lambda:deepcopy(payload))
    roster=[[r['source_life'],r['query'],r['episode']] for r in records if stage=='FULL' or r['is_half']]
    log=dict(stage=stage,source_lives=sources,statistics_roster=[r for r in roster if r[2]==0],
        training_roster=roster,optimizer_state='reset_zero_moments',new_optimizer_steps=1000,
        inherited_parameter_steps=1000 if stage=='FULL' else 0,parameter_lineage_steps=2000 if stage=='FULL' else 1000,
        initialization='half_parameters' if stage=='FULL' else 'original_initialization',checks={'bound':True})
    return model,log


def test_full_dispatch_excludes_target_and_retains_cohort(tmp_path,monkeypatch):
    prior=fixture_source(tmp_path,monkeypatch); calls=[]
    def fit(records,hidden,stage,sources,half_payload=None):
        calls.append((sources,hidden,stage))
        assert {r['source_life'] for r in records}==set(sources)
        return fake_fit(records,hidden,stage,sources,half_payload)
    def score(models,roots):
        assert len(models)==16 and roots==prior['cohort']['roots']
        return [],dict(counts={},checks={'complete':True})
    monkeypatch.setattr(m,'fit_stage',fit);monkeypatch.setattr(m,'score_models',score)
    out=tmp_path/'out';m.run(out)
    report=json.loads((out/'run.json').read_text())
    assert len(calls)==16 and report['status']=='complete'
    assert report['cohort']==prior['cohort'] and all(report['runner_checks'].values())
    assert report['inherited_work']['V109']=={'retained_version':109}
    for fold in report['folds']:
        assert fold['source_lives']==[life for life in m.LIVES if life!=fold['heldout_life']]
        assert len(fold['fit_logs'])==4


def test_scoring_only_visits_excluded_history_and_rejects_leaky_metadata(tmp_path,monkeypatch):
    path=tmp_path/'model.json'
    payload=dict(hidden=4,checkpoint=256000,family='UNIFORM_SHRINK',update=dict(
        stage='HALF',source_lives=[12,13,14],heldout_life=11))
    path.write_text(json.dumps(payload)); visited=[]
    def from_payload(row):
        def score(features,work):
            visited.append(features[0][0]);return [0.,1.,0.,0.,0.]
        return SimpleNamespace(**{k:v for k,v in row.items() if k!='update'},score_candidates=score)
    monkeypatch.setattr(m.CandidateModel,'from_payload',from_payload)
    row=dict(heldout_life=11,method='POOLED_H4_HALF',metadata=dict(path=str(path),hidden=4,
        checkpoint=256000,family='UNIFORM_SHRINK',stage='HALF',source_lives=[12,13,14],heldout_life=11))
    roots=[dict(life=life,root_id=str(life),features=[[life]]*5) for life in m.LIVES]
    decisions,log=m.score_models([row],roots)
    assert visited==[11] and len(decisions)==1 and all(log['checks'].values())
    payload['update']['source_lives']=[11,12,13];path.write_text(json.dumps(payload))
    decisions,log=m.score_models([row],roots)
    assert decisions==[] and not log['checks']['model_metadata_match'] and visited==[11]


def test_full_statistic_drift_stops_and_preserves_completed_fit(tmp_path,monkeypatch):
    fixture_source(tmp_path,monkeypatch)
    def fit(*args,**kwargs):
        model,log=fake_fit(*args,**kwargs)
        if args[2]=='FULL':
            payload=model.to_payload();payload['uniform_gamma']=.9
            model.to_payload=lambda:payload
        return model,log
    monkeypatch.setattr(m,'fit_stage',fit)
    monkeypatch.setattr(m,'score_models',lambda *a:pytest.fail('mismatched full statistics scored'))
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='frozen data'):
        m.run(out)
    report=json.loads((out/'run.json').read_text())
    assert len(report['models'])==2 and not report['runner_checks']['full_statistics_frozen']


def test_acquisition_accounting_counts_unique_history_once():
    cost=m.acquisition_accounting(allocations())
    assert cost['unique_inherited_training_transitions']==2048000
    assert all(row['half_transitions']==768000 and row['full_transitions']==1536000 for row in cost['per_fold'])
    assert sum(row['full_transitions'] for row in cost['per_fold'])==3*cost['unique_inherited_training_transitions']
    assert all(sum(part['total_transitions'] for part in row['cost_partition'].values())==row['full_transitions']
               for row in cost['per_history'])
