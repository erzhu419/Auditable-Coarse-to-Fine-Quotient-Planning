"""Independent finite risk examples and one complete standard-2048 hand closure."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_causal_audit_v66 as A
from acfqp.science.controlled_predictive_causal_forgetting_v66 import build_model
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel,Outcome,Query,Plan,compile_full_state,plan

ROOT=Path(__file__).resolve().parents[1]
WORK=Counter()


@pytest.fixture(scope='session',autouse=True)
def ledger():
    yield
    (ROOT/'reports/controlled_predictive_causal_v66.audit_checks.json').write_text(json.dumps(dict(
        schema='acfqp.controlled_predictive_causal_audit_checks.v66',development_work=dict(WORK,
            random_samples=0,main_root_evaluations=0,
            scope='Tiny hand finite kernels plus one horizon-one standard 2048 root; ground DP is reused across abstraction arms.')),indent=2)+'\n')


def reference(closure,queries):
    result=A.compute_reference(closure,queries)
    WORK.update(result.counts);WORK['reference_calls']+=1
    return result


def solve(build,queries):
    compiled=compile_full_state(build.model);WORK['singleton_compilations']+=1
    solutions={}
    for name,query in queries.items():
        solutions[name]=plan(compiled,query)
        WORK.update({'candidate_plan_'+n:value for n,value in solutions[name].counts.items()})
    return compiled,solutions


def audited(build,closure,queries,solutions,ref,compiled):
    result=A.audit_build(build,closure,queries,solutions,ref,compiled)
    WORK.update(result['counts']);WORK['audit_calls']+=1
    return result


def hand_fixture(monkeypatch,model):
    # This hand finite kernel isolates the audit; actual board encoding is exercised separately below.
    monkeypatch.setattr(A,'encode_key',lambda board,h,rule:(h,board))
    boards={state:(state,) for state in model.layers}
    closure=SimpleNamespace(model=model,boards=boards,root_names=tuple(f'root_{r}' for r in model.roots))
    build=SimpleNamespace(model=model,state_index={(model.layers[s],boards[s]):s for s in model.layers},rule=None)
    return closure,build


def risk_model():
    return FiniteModel({0:2,1:1,2:1,3:0,4:0,5:0},
        {0:'ACTIVE',1:'ACTIVE',2:'ACTIVE',3:'WON',4:'LOST',5:'CUTOFF'},
        {(0,'risky'):(Outcome(1.,1,0.),),(0,'safe'):(Outcome(1.,2,0.),),
         (1,'finish'):(Outcome(.5,3,2.),Outcome(.5,4,2.)),(2,'finish'):(Outcome(1.,5,1.),)},(0,))


def test_two_step_risk_metrics_and_strict_query_switch(monkeypatch):
    closure,build=hand_fixture(monkeypatch,risk_model())
    queries={'reward':Query(),'risk':Query(failure_penalty=4.)}
    ref=reference(closure,queries);compiled,solutions=solve(build,queries)
    result=audited(build,closure,queries,solutions,ref,compiled)
    assert result['valid'] and result['strict_query_switches']==dict(required=1,violations=0,preserved=True)
    assert result['queries']['reward']['root_metrics'][0]['actual']==dict(reward=2.,failure=.5,success=.5,value=2.)
    assert result['queries']['risk']['root_metrics'][0]['actual']==dict(reward=1.,failure=0.,success=0.,value=1.)
    unsafe=dict(solutions)
    unsafe['risk']=Plan(dict(solutions['risk'].values),dict(solutions['reward'].policy),{})
    changed=audited(build,closure,queries,unsafe,ref,compiled)
    assert not changed['valid'] and changed['structural_valid']
    assert changed['queries']['risk']['maximum_value_loss']==1.
    assert changed['strict_query_switches']['violations']==1


def test_joint_reward_successor_check_rejects_equal_marginals(monkeypatch):
    ground=FiniteModel({0:1,1:0,2:0},{0:'ACTIVE',1:'WON',2:'LOST'},
        {(0,'a'):(Outcome(.5,1,2.),Outcome(.5,2,0.))},(0,))
    closure,build=hand_fixture(monkeypatch,ground)
    build.model=replace(ground,rows={(0,'a'):(Outcome(.5,1,0.),Outcome(.5,2,2.))})
    queries={'reward':Query()};ref=reference(closure,queries);compiled,solutions=solve(build,queries)
    result=audited(build,closure,queries,solutions,ref,compiled)
    assert not result['valid'] and result['errors']=={'reward_successor_joint_distribution':1}
    assert result['maximum_joint_total_variation']==1.
    assert result['queries']['reward']['maximum_value_loss']==0.
    assert result['queries']['reward']['maximum_metric_prediction_error']==0.


def test_missing_encoded_target_is_failure_with_unavailable_metrics(monkeypatch):
    closure,build=hand_fixture(monkeypatch,risk_model())
    del build.state_index[(1,(1,))]
    queries={'reward':Query()};ref=reference(closure,queries);compiled,solutions=solve(build,queries)
    result=audited(build,closure,queries,solutions,ref,compiled)
    assert not result['valid'] and result['errors']['missing_encoded_state']==1
    assert result['errors']['missing_pushforward_target']==1
    assert result['worst_counterexample']['reason']=='missing_encoded_state'
    assert result['queries']['reward']['root_metrics'][0]['actual'] is None
    assert result['queries']['reward']['maximum_value_loss'] is None


def test_real_small_2048_closure_preserves_causal_but_rejects_unsafe():
    board=(8,6,9,7,5,9,7,10,9,7,10,8,1,3,4,0)
    closure=build_development_closure(horizon=1,max_nodes=100,boards={'hand_spawn_partner':board})
    WORK.update({'ground_closure_'+n:value for n,value in closure.counts.items()})
    queries={'reward':Query(),'risk':Query(failure_penalty=1.)}
    ref=reference(closure,queries)
    results={}
    for variant in ('BASELINE','CAUSAL','UNSAFE'):
        build=build_model(board,1,variant,max_states=100)
        WORK.update({'candidate_build_'+n:value for n,value in build.counts.items()})
        compiled,solutions=solve(build,queries)
        results[variant]=audited(build,closure,queries,solutions,ref,compiled)
    assert results['BASELINE']['valid'] and results['CAUSAL']['valid']
    assert not results['UNSAFE']['valid'] and not results['UNSAFE']['structural_valid']
    assert results['UNSAFE']['worst_counterexample'] is not None
