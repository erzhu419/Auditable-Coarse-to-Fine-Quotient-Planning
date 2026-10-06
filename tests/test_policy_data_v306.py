"""Matched initial critic, policy-data assignment and cost scope with real fits."""
from fractions import Fraction
from pathlib import Path
import numpy as np
import pytest

from acfqp.science import policy_data_v306 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/policy_alignment_v306/runtime/tests/driver'


def dataset(reward=.1):
    memory=SpawnMemory('POOLED')
    for i in range(256): memory.observe(1)
    return dict(lifecycle=0,parent=0,afterstates=np.tile([1,1,0,0]+[0]*12,(7,1)).astype(np.int32),
        rewards=np.full(7,reward),ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),
        costs=dict(excluded_tail_raw_tiles=3),games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST',steps=2 if i<2 else 3) for i in range(3)])


def fixture(monkeypatch):
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',11)
    template=QueryTD(QueryParent(NtupleValue(rule,BUILD),core.QUERY,core.QUERY,.5),'PRIOR',BUILD);template.freeze()
    initial,setup=core.new_head(template,BUILD);fit=core.fit_split(initial,dataset(),BUILD,alpha=.0025);initial.freeze()
    memory=SpawnMemory.from_payload(dataset()['fit_memory']);p=memory.predict()
    old=dict(lifecycle=0,parent=0,evaluation_beliefs={'A':dict(memory=memory.to_payload(),estimated_p_four=p)},
        stages={'A1':dict(arms={'LOCAL_RISK':dict(fit=fit)},acquisition=dict(warmup={'raw_tiles':7},training={'raw_tiles':20}))})
    calls=[]
    def acquire(leaf,life,parent,arm,p,emit,runtime):
        assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
        calls.append((arm,leaf.updates,leaf.risk_weights[0,0]))
        stream=dict(raw_tiles=core.RAW_BUDGET,random_draw_position=2*core.RAW_BUDGET,stream_seed=306200000000)
        return dict(dataset=dataset(.1 if arm=='SOURCE_DATA' else .8),acquisition=dict(
            training=dict(raw_tiles=core.RAW_BUDGET,after_stream=stream,counts=dict(environment={},planning={}),representation_counts={}),
            reconstruction=dict(counts={},memory_counts={},cpu_seconds=.1),native_setup_counts={},cpu_seconds=.3))
    def evaluate(leaf,p,true,seeds,runtime,max_steps):
        assert p==1/258 and true==.1 and max_steps==8192
        return dict(game_summaries=[dict(seed=s,status='LOST',utility=-4.,steps=1) for s in seeds],
            counts=dict(environment={},planning={}),representation_counts={},setup_counts={},seconds=0.,cpu_seconds=0.)
    monkeypatch.setattr(core,'acquire_policy_data',acquire);monkeypatch.setattr(core,'evaluate_split',evaluate)
    return template,old,calls


def test_source_and_current_actors_frozen_then_identical_A1_copies_fit_their_own_data(monkeypatch):
    template,old,calls=fixture(monkeypatch);fits=[];native=core.fit_split
    def tracked(leaf,data,runtime,alpha):
        fits.append((leaf.updates,float(data['rewards'][0]),leaf.reward_weights.copy(),leaf.risk_weights.copy()))
        return native(leaf,data,runtime,alpha=alpha)
    monkeypatch.setattr(core,'fit_split',tracked)
    result=core._run_lifecycle(template,old,dataset(),BUILD,lambda r:None)
    assert [(a,n) for a,n,r in calls]==[('SOURCE_DATA',0),('CURRENT_DATA',4)]
    assert fits[1][:2]==(4,.1) and fits[2][:2]==(4,.8)
    assert np.array_equal(fits[1][2],fits[2][2]) and np.array_equal(fits[1][3],fits[2][3])
    assert result['arms']['A1_FROZEN']['head_updates_after']==4
    for arm in core.DATASETS:
        row=result['arms'][arm]
        assert (row['head_updates_before'],row['head_updates_after'])==(4,8)
        assert row['head_setup']['setup_counts']['a1_weight_bytes_copied']==row['head_setup']['private_weight_bytes']
    assert result['arms']['SOURCE']['head_updates_after']==0 and template.updates==0


def test_changed_retained_initial_fit_cannot_start_new_cohorts(monkeypatch):
    template,old,calls=fixture(monkeypatch);old['stages']['A1']['arms']['LOCAL_RISK']['fit']['alpha']=.01
    with pytest.raises(ValueError,match='Initial A1'): core._run_lifecycle(template,old,dataset(),BUILD,lambda r:None)
    assert not calls


def test_economic_budget_matches_new_actor_raw_not_fitted_games(monkeypatch):
    template,old,calls=fixture(monkeypatch);row=core._run_lifecycle(template,old,dataset(),BUILD,lambda r:None)
    original=dict(accounting={'inherited_costs_per_arm':{'SOURCE':dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)}},by_lifecycle=[old])
    parent=dict(trace_bytes=10,initial_reconstruction=dict(cpu_seconds=.1,counts={}),cpu_seconds=1.,compiler_cpu_seconds=.2)
    cost=core.build_accounting(original,[row],[parent],.1,1.)
    assert cost['new_training_environment_observations']==2*core.RAW_BUDGET and cost['physical_acquisitions']==2
    assert cost['economic_training_raw_tiles_per_arm']==dict(SOURCE=132,A1_FROZEN=132,SOURCE_DATA=132+core.RAW_BUDGET,CURRENT_DATA=132+core.RAW_BUDGET)
    assert cost['initial_replayed_training_samples']==4
    assert cost['new_processed_training_samples']==dict(SOURCE=0,A1_FROZEN=0,SOURCE_DATA=4,CURRENT_DATA=4)
    assert cost['new_evaluation_games']==128
    assert cost['head_setup_counts']['A1_FROZEN']==row['initial_head_setup']['setup_counts']
    assert cost['private_head_weight_bytes_created']['SOURCE_DATA']==cost['private_head_weight_bytes_created']['A1_FROZEN']


def test_freeze_new_pairing_and_full_policy_representation():
    settings=core.configuration(BUILD/'v303.json')
    assert settings['seed_training']==306200000000 and settings['seed_evaluation']==306900000000
    assert settings['actor_policy']=='FULL_SPLIT_H2_WITH_FROZEN_REWARD_AND_RISK'
    assert settings['new_training_raw_tiles']==16777216 and settings['new_evaluation_games']==8192
    assert settings['primary']=='CURRENT_DATA_minus_SOURCE_DATA'
    assert settings['interval_scope']==core.INTERVAL_SCOPE
