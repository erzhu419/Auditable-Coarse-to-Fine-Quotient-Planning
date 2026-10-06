"""Retained width and cumulative age binding in the capacity comparison."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_capacity_ranking_v103 as m
from acfqp.science import controlled_predictive_candidate_data_v100 as prefixes


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    p=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_capacity_runner_v103.checks.json'
    data=json.loads(p.read_text()) if p.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0,new_model_transitions=0,new_neural_model_fits=0,
        scope='Mock data/fits/prefixes; retained width, model age, cumulative records and ordinal deployment.'))
    p.write_text(json.dumps(data,indent=2)+'\n')


def payload(checkpoint, size, family='MEAN_SIGN', hidden=16):
    return dict(checkpoint=checkpoint,parameters=[[size]],mean=[0],scale=[1],family=family,
        hidden=hidden,uniform_gamma=.3,
        training_episodes={q:[0] if size==2 else [0,3] for q in m.QUERIES})


def model(row):
    return SimpleNamespace(**row,to_payload=lambda:deepcopy(row))


def test_retained_baseline_binds_width_family_gamma_and_roster():
    saved=payload(5,4)
    fitted=model(saved)
    assert m.baseline_matches(fitted,saved)
    for field,value in (('parameters',[[5]]),('scale',[2]),('checkpoint',6),('hidden',4),
                        ('family','REPLICA'),('uniform_gamma',.9),
                        ('training_episodes',{'reward':[4],'risk_goal':[0]})):
        changed=deepcopy(saved);changed[field]=value
        assert not m.baseline_matches(fitted,changed)


def test_only_narrow_models_fit_and_both_widths_keep_cumulative_age(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'BUDGETS',(20,40))
    source=tmp_path/'v102';monkeypatch.setattr(m,'REPLICA_SOURCE',source)
    for budget,cutoff,size,suffix in ((20,2,2,'_frozen_half'),(40,5,4,'')):
        folder=source/'life_9'/'replicas_4'/f'budget_{budget}'
        folder.mkdir(parents=True)
        for family in m.FAMILIES:
            (folder/f'r4_{family.lower()}_direct{suffix}_model.json').write_text(
                json.dumps(payload(cutoff,size,family)))
        (folder/'construction.json').write_text(json.dumps(dict(fit_log=dict(retained=True))))
    loads,fits=[],[]
    def load(original,output):
        budget=int(original.name.split('_')[-1]);loads.append((budget,original,output))
        episode=0 if budget==20 else 3
        return [dict(query=q,episode=episode) for q in m.QUERIES],dict(
            start_cursor=0 if budget==20 else 2,next_cursor=2 if budget==20 else 8,
            episode_cutoff=2 if budget==20 else 5,inherited_acquisition=dict(used_transitions=20))
    def fit(records,checkpoint,hidden):
        assert hidden==4
        fits.append((deepcopy(records),checkpoint))
        rows={f:payload(checkpoint,len(records),f,hidden) for f in m.FAMILIES}
        return {f:model(row) for f,row in rows.items()},dict(training_roots=len(records),
            training_episodes=rows['MEAN_SIGN']['training_episodes'],
            counts=dict(neural_model_fits=3),models={f:dict(final_loss=1) for f in m.FAMILIES})
    monkeypatch.setattr(m,'load_batch',load);monkeypatch.setattr(m,'fit_models',fit)
    monkeypatch.setattr(m.CandidateModel,'from_payload',model)
    allocation=m.construct_allocation(9,4,tmp_path,{})
    assert [x[0] for x in loads]==[20,40] and [len(rows) for rows,_ in fits]==[2,4]
    assert all(x[1].is_relative_to(source) for x in loads)
    assert all(all(s['baseline_equivalence'].values()) for s in allocation['construction'])
    assert allocation['new_neural_model_fits']==6 and allocation['frozen_model_payloads_reused']==6
    assert allocation['new_training_environment_transitions']==0
    assert all(s['frozen_fit_log']==dict(retained=True) for s in allocation['construction'])
    names=('H2_ONLY','PREFIX_ONLY_DIRECT')+tuple(allocation['model_metadata'])
    monkeypatch.setattr(m,'METHODS',names)
    monkeypatch.setattr(m.LearnedDynamics,'from_payload',lambda _:None)
    def evaluate(life,budget,folder,models,rule):
        for name in names[2:]:
            assert models[name].parameters==[[2 if name.endswith('_FROZEN_HALF') else 4]]
            assert models[name].hidden==(4 if '_H4_' in name else 16)
        return dict(methods={}),[],[]
    monkeypatch.setattr(m,'evaluate_checkpoint',evaluate)
    monkeypatch.setattr(m,'validate_roots',lambda *args:dict(roots=[]))
    result=m.lifecycle_evaluation(9,tmp_path,{},[allocation])
    assert result['evaluation']['model_metadata']==allocation['model_metadata']


def test_ordinal_selector_keeps_same_prefix_inputs_at_both_widths(monkeypatch):
    log=dict(model_work={},planning_counts={},feature_counts={},outcomes={},wiring={},replicas=1,trajectories=0)
    monkeypatch.setattr(prefixes,'build_candidates',lambda *args:([[0]]*5,[0,.2,.1,-.1,-.2],[],log))
    for hidden in m.WIDTHS:
        for family in m.FAMILIES:
            fitted=SimpleNamespace(checkpoint=5,family=family,hidden=hidden,
                score_candidates=lambda x,work:[0,-1,2,1,0])
            selected=m.CandidateSelector(fitted,None,4,replicas=1).select([0]*16,'reward')
            assert selected['option']=='SNAKE_1' and selected['score_semantics']=='rank_score'
            assert selected['predicted_advantage'] is None
    selected=m.CandidateSelector(None,None,4,replicas=1).select([0]*16,'reward')
    assert selected['option']=='SPACE_1' and selected['score_semantics']=='prefix_utility'
