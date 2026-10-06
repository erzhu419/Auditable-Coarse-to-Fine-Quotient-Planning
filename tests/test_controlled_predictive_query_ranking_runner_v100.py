"""Incremental root groups and the deployed current/frozen scalar models."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from scripts import run_controlled_predictive_query_ranking_v100 as m


def test_same_roots_both_losses_and_both_model_ages(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'BUDGETS',(20,40))
    monkeypatch.setattr(m.LearnedDynamics,'from_payload',lambda p:None)
    loads,fits=[],[]
    def load(source,out,rule,life):
        budget=int(source.name.split('_')[-1]);loads.append(budget)
        episode=0 if budget==20 else 3
        return [dict(query=q,episode=episode,features=[[episode]*3]*5,utilities=[0,1,2,3,4])
                for q in m.QUERIES],dict(start_cursor=0 if budget==20 else 2,next_cursor=2 if budget==20 else 8,
                    episode_cutoff=2 if budget==20 else 5,inherited_acquisition=dict(used_transitions=20))
    def fit(rows,checkpoint):
        fits.append((deepcopy(rows),checkpoint))
        def model(family):
            return SimpleNamespace(to_payload=lambda:dict(family=family,checkpoint=checkpoint,marker=len(rows)))
        return {family:model(family) for family in m.FAMILIES},dict(training_roots=len(rows),
            counts=dict(neural_model_fits=2),models={family:dict(final_loss=1) for family in m.FAMILIES})
    monkeypatch.setattr(m,'load_batch',load);monkeypatch.setattr(m,'fit_models',fit)
    allocation=m.construct_allocation(9,4,tmp_path,{})
    assert loads==[20,40] and [len(x) for x,_ in fits]==[2,4]
    assert [c for _,c in fits]==[2,5] and allocation['new_neural_model_fits']==4
    assert allocation['new_training_environment_transitions']==0 and allocation['inherited_training_environment_transitions']==40
    names=('H2_ONLY','PREFIX_ONLY_DIRECT')+tuple(allocation['model_metadata'])
    monkeypatch.setattr(m,'METHODS',names)
    monkeypatch.setattr(m.CandidateModel,'from_payload',lambda p:SimpleNamespace(**p))
    def evaluate(life,budget,folder,models,rule):
        assert models['H2_ONLY'] is models['PREFIX_ONLY_DIRECT'] is None
        for name in names[2:]:
            assert models[name].marker==(2 if name.endswith('_FROZEN_HALF') else 4)
        return dict(methods={}),[],[]
    monkeypatch.setattr(m,'evaluate_checkpoint',evaluate)
    monkeypatch.setattr(m,'validate_roots',lambda *args:dict(roots=[]))
    result=m.lifecycle_evaluation(9,tmp_path,{},[allocation])
    assert result['evaluation']['model_metadata']==allocation['model_metadata']
