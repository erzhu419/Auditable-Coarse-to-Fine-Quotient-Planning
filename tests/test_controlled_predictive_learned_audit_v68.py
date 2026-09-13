"""Frozen-source policy audit on distinct target finite kernels."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_learned_audit_v68 as A
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel,Outcome,Query,compile_full_state,plan

ROOT=Path(__file__).resolve().parents[1]
WORK=Counter()


@pytest.fixture(scope='session',autouse=True)
def ledger():
    yield
    (ROOT/'reports/controlled_predictive_learned_v68.audit_checks.json').write_text(json.dumps(dict(
        schema='acfqp.controlled_predictive_learned_audit_checks.v68',development_work=dict(WORK,
            main_cohort_roots=0,training_updates=0,random_samples=0,target_model_updates=0,
            scope='Tiny hand finite kernels; frozen source plans, exact target reference and independent support/policy audits.')),indent=2)+'\n')


def source_model(model,queries):
    compiled=compile_full_state(model);WORK['source_singleton_compilations']+=1
    plans={name:plan(compiled,query) for name,query in queries.items()}
    for solution in plans.values():WORK.update({'source_plan_'+n:v for n,v in solution.counts.items()})
    support=A.recursive_support(model);WORK.update({'source_support_'+n:v for n,v in support.counts.items()})
    return compiled,plans,support


def audit(target,queries,source,encoded):
    closure=SimpleNamespace(model=target,root_names=tuple(f'target_{s}' for s in target.roots))
    reference=A.compute_reference(closure,queries);WORK.update(reference.counts)
    support=A.support_coverage(target,source[2]);WORK.update({'target_support_'+n:v for n,v in support['counts'].items()})
    result=A.audit_frozen(closure,queries,source[0],source[1],encoded,reference,source[2],target_support=support)
    WORK.update(result['counts']);WORK['audit_calls']+=1
    return result


def test_exact_frozen_source_transfer_preserves_two_step_risk_switch():
    source=FiniteModel({0:2,1:1,2:1,3:0,4:0,5:0},
        {0:'ACTIVE',1:'ACTIVE',2:'ACTIVE',3:'WON',4:'LOST',5:'CUTOFF'},
        {(0,'risky'):(Outcome(1.,1,0.),),(0,'safe'):(Outcome(1.,2,0.),),
         (1,'finish'):(Outcome(.5,3,2.),Outcome(.5,4,2.)),(2,'finish'):(Outcome(1.,5,1.),)},(0,))
    target=FiniteModel({s+10:h for s,h in source.layers.items()},{s+10:v for s,v in source.terminal.items()},
        {(s+10,a):tuple(Outcome(o.probability,o.next_state+10,o.reward) for o in row) for (s,a),row in source.rows.items()},(10,))
    queries={'reward':Query(),'risk':Query(failure_penalty=4.)}
    frozen=source_model(source,queries)
    result=audit(target,queries,frozen,{s+10:frozen[0].state_to_cell[s] for s in (0,1,2)})
    assert result['valid_evidence'] and result['exact_controlled_equivalence']
    assert result['strict_query_switches']==dict(required=1,violations=0,preserved=True)
    assert result['source_support']['source_supported_states']==3
    reward=result['queries']['reward']['root_metrics'][0]['actual']
    assert reward==dict(reward=2.,natural_failure=.5,unsupported=0.,success=.5,failure=.5,value=2.)
    cautious=result['queries']['risk']['root_metrics'][0]
    assert cautious['actual']['value']==1. and cautious['value_loss']==0.
    assert result['queries']['risk']['by_horizon']['2']['action_errors']==0


def test_illegal_or_missing_code_stops_operationally_at_correct_reach_probability():
    source=FiniteModel({0:2,1:1,2:1,3:0},{0:'ACTIVE',1:'ACTIVE',2:'LOST',3:'WON'},
        {(0,'go'):(Outcome(.25,1,2.),Outcome(.75,2,2.)),(1,'source_only'):(Outcome(1.,3,0.),)},(0,))
    target=replace(source,rows={(0,'go'):source.rows[0,'go'],(1,'target_only'):source.rows[1,'source_only']})
    queries={'risk':Query(failure_penalty=4.)};frozen=source_model(source,queries)
    original_rows=dict(target.rows)
    for child in (frozen[0].state_to_cell[1],None):
        result=audit(target,queries,frozen,{0:frozen[0].state_to_cell[0],1:child})
        assert result['valid_evidence'] and not result['exact_controlled_equivalence']
        metrics=result['queries']['risk']['root_metrics'][0]
        assert metrics['actual']==dict(reward=2.,natural_failure=.75,unsupported=.25,success=0.,failure=1.,value=-2.)
        assert metrics['value_loss']==1.
        assert result['queries']['risk']['by_horizon']['1']['illegal_or_missing_actions']==1
        assert result['queries']['risk']['by_horizon']['2']['action_errors']==0
    assert target.rows==original_rows


def test_missing_recursive_source_semantics_does_not_imply_policy_failure():
    source=FiniteModel({0:1,1:0},{0:'ACTIVE',1:'WON'},{(0,'only'):(Outcome(1.,1,1.),)},(0,))
    target=replace(source,rows={(0,'only'):(Outcome(1.,1,2.),)})
    queries={'reward':Query()};frozen=source_model(source,queries)
    registry=dict(frozen[2].registry)
    result=audit(target,queries,frozen,{0:frozen[0].state_to_cell[0]})
    assert result['valid_evidence'] and not result['exact_controlled_equivalence']
    assert result['source_support']['source_supported_states']==0
    assert result['source_support']['roots'][0]['source_supported'] is False
    root=result['queries']['reward']['root_metrics'][0]
    assert root['value_loss']==0. and root['prediction_error']==-1.
    assert root['actual']['unsupported']==0.
    assert frozen[2].registry==registry
