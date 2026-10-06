"""Gradient correctness and train-only normalization for the matched objectives."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_candidate_learning_v100 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    p=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_candidate_learning_v100.checks.json'
    r=json.loads(p.read_text()) if p.exists() else dict(attempts=[])
    r['attempts'].append(dict(failures=request.session.testsfailed-before,work=dict(WORK),
        new_environment_transitions=0,new_synthetic_transitions=0,scope='Synthetic gradients and small neural fits.'))
    p.write_text(json.dumps(r,indent=2)+'\n')


@pytest.mark.parametrize('family',m.FAMILIES)
def test_analytic_gradient_including_h2_centering_and_all_pairs(family):
    rng=np.random.default_rng(4); x=rng.normal(size=(3,5,4)); y=rng.normal(size=(3,5));y[:,0]=0
    p=m.initialize(4); _,gradient=m.objective(p,x,y,family)
    WORK['objective_evaluations']+=1
    for a,index in [(0,(2,3)),(0,(0,0)),(1,(3,)),(2,(4,))]:
        original=p[a][index]; eps=1e-6
        p[a][index]=original+eps; upper=m.objective(p,x,y,family)[0]
        p[a][index]=original-eps; lower=m.objective(p,x,y,family)[0];p[a][index]=original
        WORK['objective_evaluations']+=2
        assert gradient[a][index]==pytest.approx((upper-lower)/(2*eps),rel=2e-5,abs=1e-7)


def test_rank_ties_have_zero_mass_and_correct_order_lowers_data_loss(monkeypatch):
    monkeypatch.setattr(m,'L2',0.)
    x=np.array([[[0.],[1.],[2.],[3.],[4.]]]); y=np.array([[0.,1.,2.,3.,4.]])
    p=[np.ones((1,16))*.1,np.zeros(16),np.ones(16)]
    good=m.objective(p,x,y,'PAIRWISE_RANK')[0]
    bad=m.objective([p[0],p[1],-p[2]],x,y,'PAIRWISE_RANK')[0]
    loss,grad=m.objective(p,x,np.zeros_like(y),'PAIRWISE_RANK')
    WORK['objective_evaluations']+=3
    assert good<bad and loss==0 and all(np.all(g==0) for g in grad)


def test_heldout_future_excluded_from_normalization_and_models(monkeypatch):
    monkeypatch.setattr(m,'STEPS',12)
    rng=np.random.default_rng(7)
    rows=[dict(query=q,episode=e,features=rng.normal(size=(5,4)).tolist(),utilities=[0.,1.,-.5,2.,-.2])
        for q in ('reward','risk_goal') for e in (0,1,4,6)]
    a,log=m.fit_models(rows,5)
    changed=deepcopy(rows)
    for r in changed:
        if r['episode'] in (4,6):
            r['features']=(np.asarray(r['features'])*100000).tolist(); r['utilities']=[0,999,555,-111,777]
    b,other=m.fit_models(changed,5)
    WORK.update(neural_model_fits=4,optimizer_steps=48)
    assert log['training_roots']==log['normalization_training_roots']==4
    assert log['training_episodes']=={'reward':[0,1],'risk_goal':[0,1]}
    for family in m.FAMILIES:
        assert a[family].to_payload()==b[family].to_payload()
        saved=m.CandidateModel.from_payload(a[family].to_payload())
        scores=saved.score_candidates(rows[0]['features'])
        assert scores[0]==0 and scores==a[family].score_candidates(rows[0]['features'])
        assert ('utility_mse' in log['models'][family]['heldout'])==(family=='UTILITY_MSE')


def test_identical_initialization_and_lower_synthetic_training_losses(monkeypatch):
    monkeypatch.setattr(m,'STEPS',80)
    x=np.eye(5).tolist()
    rows=[dict(query=q,episode=e,features=x,utilities=[0,2,-1,1,-2])
          for q in ('reward','risk_goal') for e in (0,1)]
    models,log=m.fit_models(rows,2)
    WORK.update(neural_model_fits=2,optimizer_steps=160)
    for family,row in log['models'].items():
        assert row['final_loss']<row['initial_loss']
        assert np.argmax(models[family].score_candidates(x))==1
    for p,q in zip(m.initialize(5),m.initialize(5)):
        assert np.array_equal(p,q)
