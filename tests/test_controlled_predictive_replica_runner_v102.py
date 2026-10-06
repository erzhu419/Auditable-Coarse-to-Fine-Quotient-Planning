"""Frozen baseline, model ages and ordinal deployment for V102."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_replica_ranking_v102 as m
from acfqp.science import controlled_predictive_candidate_data_v100 as prefixes


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    p=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_replica_runner_v102.checks.json'
    data=json.loads(p.read_text()) if p.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0,new_model_transitions=0,new_neural_model_fits=0,
        scope='Mock data/fits and prefix generation; payload binding and model-age wiring.'))
    p.write_text(json.dumps(data,indent=2)+'\n')


def payload(checkpoint, size):
    return dict(checkpoint=checkpoint,parameters=[[size]],mean=[0],scale=[1],
        training_episodes={q:[0] if size==2 else [0,3] for q in m.QUERIES})


def test_frozen_baseline_compares_parameters_normalization_and_training_roster():
    saved=payload(5,4)
    model=SimpleNamespace(to_payload=lambda:dict(saved,family='MEAN_SIGN'))
    assert m.baseline_matches(model,saved)
    for field,value in (('parameters',[[5]]),('scale',[2]),('checkpoint',6),
                        ('training_episodes',{'reward':[4],'risk_goal':[0]})):
        changed=deepcopy(saved);changed[field]=value
        assert not m.baseline_matches(model,changed)


def test_both_ages_use_cumulative_records_and_match_frozen_mean_models(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'BUDGETS',(20,40))
    feature_source=tmp_path/'v100';monkeypatch.setattr(m,'FEATURE_SOURCE',feature_source)
    for budget,cutoff,size,suffix in ((20,2,2,'_frozen_half'),(40,5,4,'')):
        folder=feature_source/'life_9'/'replicas_4'/f'budget_{budget}'
        folder.mkdir(parents=True)
        (folder/f'r4_pairwise_rank_direct{suffix}_model.json').write_text(json.dumps(payload(cutoff,size)))
    loads,fits=[],[]
    def load(original,features,output):
        budget=int(original.name.split('_')[-1]);loads.append((budget,features,output))
        episode=0 if budget==20 else 3
        return [dict(query=q,episode=episode,features=[[episode]*3]*5,utilities=[0,1,2,3,4],
                     replica_utilities=[[0,1,2,3,4]]*4) for q in m.QUERIES],dict(
            start_cursor=0 if budget==20 else 2,next_cursor=2 if budget==20 else 8,
            episode_cutoff=2 if budget==20 else 5,inherited_acquisition=dict(used_transitions=20))
    def fit(records,checkpoint):
        fits.append((deepcopy(records),checkpoint))
        def model(family):
            return SimpleNamespace(to_payload=lambda:dict(payload(checkpoint,len(records)),family=family))
        return {f:model(f) for f in m.FAMILIES},dict(training_roots=len(records),
            counts=dict(neural_model_fits=3),models={f:dict(final_loss=1) for f in m.FAMILIES})
    monkeypatch.setattr(m,'load_batch',load);monkeypatch.setattr(m,'fit_models',fit)
    allocation=m.construct_allocation(9,4,tmp_path,{})
    assert [x[0] for x in loads]==[20,40] and [len(rows) for rows,_ in fits]==[2,4]
    assert all(x[1].is_relative_to(feature_source) for x in loads)
    assert all(s['baseline_equivalence'] for s in allocation['construction'])
    assert allocation['new_neural_model_fits']==6
    assert allocation['new_training_environment_transitions']==0
    names=('H2_ONLY','PREFIX_ONLY_DIRECT')+tuple(allocation['model_metadata'])
    monkeypatch.setattr(m,'METHODS',names)
    monkeypatch.setattr(m.LearnedDynamics,'from_payload',lambda _:None)
    monkeypatch.setattr(m.CandidateModel,'from_payload',lambda p:SimpleNamespace(**p))
    def evaluate(life,budget,folder,models,rule):
        for name in names[2:]:
            assert models[name].parameters==[[2 if name.endswith('_FROZEN_HALF') else 4]]
        return dict(methods={}),[],[]
    monkeypatch.setattr(m,'evaluate_checkpoint',evaluate)
    monkeypatch.setattr(m,'validate_roots',lambda *args:dict(roots=[]))
    result=m.lifecycle_evaluation(9,tmp_path,{},[allocation])
    assert result['evaluation']['model_metadata']==allocation['model_metadata']


def test_all_learned_scores_are_ordinal_with_same_prefix_selector(monkeypatch):
    log=dict(model_work={},planning_counts={},feature_counts={},outcomes={},wiring={},replicas=1,trajectories=0)
    monkeypatch.setattr(prefixes,'build_candidates',lambda *args:([[0]]*5,[0,.2,.1,-.1,-.2],[],log))
    for family in m.FAMILIES:
        model=SimpleNamespace(checkpoint=5,family=family,score_candidates=lambda x,work:[0,-1,2,1,0])
        selected=m.CandidateSelector(model,None,4,replicas=1).select([0]*16,'reward')
        assert selected['option']=='SNAKE_1' and selected['score_semantics']=='rank_score'
        assert selected['predicted_advantage'] is None
    selected=m.CandidateSelector(None,None,4,replicas=1).select([0]*16,'reward')
    assert selected['option']=='SPACE_1' and selected['score_semantics']=='prefix_utility'
