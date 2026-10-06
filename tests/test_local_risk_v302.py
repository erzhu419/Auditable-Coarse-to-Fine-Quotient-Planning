"""V302-only routing, initialization, fit-belief and fresh-cost checks."""
from fractions import Fraction
from pathlib import Path
import numpy as np

from acfqp.science import local_risk_v302 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/local_risk_v302/runtime/tests_driver'


def fixture():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    source.weights[0]=.2
    template=QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD)
    template.freeze()
    memory,final=SpawnMemory('LIBRARY'),SpawnMemory('LIBRARY')
    for _ in range(256): memory.observe(1)
    for i in range(512): final.observe(1+i%2)
    board=np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    data=dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),
        actor_memory_B_end=final.to_payload(),costs={'excluded_tail_raw_tiles':3},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST') for i in range(3)])
    acquisition=dict(warmup=dict(raw_tiles=7,environment_counts={},direct_counts={},memory_counts={}),
        training=dict(raw_tiles=20,counts=dict(environment={},planning={},learning={}),memory_counts={}),
        reconstruction=dict(counts={},memory_counts={},cpu_seconds=.1),cpu_seconds=.3,
        native_setup_counts={},native_setup_seconds=.01)
    return template,data,acquisition


def result(seeds):
    return dict(game_summaries=[dict(seed=seed,status='LOST',utility=-4.,steps=1) for seed in seeds],
        counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


class Evaluator:
    setup_counts={}; setup_seconds=0.
    def state(self): return 0
    def close(self): pass
    def evaluate_games(self,leaf,p,actual,seeds,depth,max_steps):
        assert p==1/258 and actual==.5 and depth==2 and max_steps==8192
        assert not leaf.weights.flags.writeable
        assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
        return result(seeds)


def split_eval(leaf,p,actual,seeds,runtime,max_steps):
    assert p==1/258 and actual==.5 and max_steps==8192
    assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
    assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
    return dict(result(seeds),representation_counts={'risk_sigmoid_calls':5},setup_counts={})


def test_original_source_initialization_and_same_factual_inventory_fit_belief(monkeypatch):
    template,data,acquisition=fixture(); initialized=[]
    native=core.SplitLeaf
    def fresh(template_,kind,runtime):
        leaf=native(template_,kind,runtime)
        np.testing.assert_array_equal(leaf.reward_weights,template.parent.source.weights)
        assert not np.any(leaf.risk_weights) and leaf.updates==0
        initialized.append(kind)
        return leaf
    monkeypatch.setattr(core,'SplitLeaf',fresh)
    monkeypatch.setattr(core,'evaluate_split',split_eval)
    row=core._run_lifecycle(template,data,acquisition,0,0,BUILD,Evaluator())
    assert initialized==['LOCAL_RISK']
    assert [row['arms'][a]['sample_counter'] for a in core.ARMS]==[0,4,4]
    assert template.updates==template.parent.source.updates==0
    expected=SpawnMemory.from_payload(data['fit_memory'])
    assert row['evaluation_snapshot']['estimated_p_four']==expected.predict()
    assert row['evaluation_snapshot']['memory']==expected.to_payload()
    assert row['acquisition'] is acquisition
    assert row['arms']['LOCAL_RISK']['fit']['frozen_game_start_targets']


def test_frozen_primary_and_new_seed_families(tmp_path):
    settings=core.configuration(tmp_path/'summary.json')
    assert settings['primary']=='LOCAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY'
    assert settings['alpha']==.0025 and settings['raw_budget']==131072
    assert settings['canonical_acquisition_arm']=='FROZEN'
    fresh={core.evaluation_seed(l,e) for l in range(64) for e in range(32)}
    old={base+l*1000000+e for base in (298900000000,301900000000) for l in range(64) for e in range(32)}
    assert len(fresh)==2048 and not fresh.intersection(old)
    assert settings['seed_warmup']==302100000000 and settings['seed_training']==302200000000


def test_fresh_costs_exclude_old_b_and_include_actual_two_head_work(monkeypatch):
    template,data,acquisition=fixture()
    monkeypatch.setattr(core,'evaluate_split',split_eval)
    row=core._run_lifecycle(template,data,acquisition,0,0,BUILD,Evaluator())
    inherited=dict(source_training_raw_tiles=100,source_training_games=4,source_training_environment_counts={},
        source_training_seconds=1.,dynamics_raw_tiles=5,dynamics_costs={})
    old=dict(accounting=dict(inherited_costs_per_arm={'SOURCE':inherited},
        retained_B_acquisition_raw_tiles=999,evaluation_counts={'environment':{'raw_tile_productions':888}}))
    parent=dict(trace_bytes=11,cpu_seconds=1.,compiler_cpu_seconds=.2)
    cost=core.build_accounting(old,[row],[parent],.05,1.)
    assert cost['new_training_environment_observations']==27 and cost['physical_acquisitions']==1
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,132)
    assert cost['development_reference']['previous_B_acquisition_raw_tiles']==999
    assert cost['excluded_tail_raw_tiles']==3
    assert cost['processed_training_samples']=={'SOURCE':0,'MC':4,'LOCAL_RISK':4}
    assert cost['fit_counts']['LOCAL_RISK']['table_updates']==2*cost['fit_counts']['MC']['table_updates']
    assert cost['evaluation_representation_counts']['LOCAL_RISK']=={'risk_sigmoid_calls':5}
    assert cost['private_head_weight_bytes_created']['LOCAL_RISK']==2*cost['private_head_weight_bytes_created']['MC']


def test_parent_uses_named_new_b_acquisition_once_per_lifecycle(monkeypatch,tmp_path):
    calls=[]; template=object()
    monkeypatch.setattr(core,'load_leaf',lambda source,runtime:(template,{}))
    monkeypatch.setattr(core,'NativeValueStream',lambda *args:Evaluator())
    def acquire(leaf,life,parent,emit,runtime,**kwargs):
        assert leaf is template and parent==2 and life%4==2
        assert kwargs==dict(phase='B',p_four=.5,warmup_seed_base=302100000000,training_seed_base=302200000000)
        calls.append(life); emit({'lifecycle':life})
        return dict(dataset={},acquisition={})
    monkeypatch.setattr(core,'acquire_dataset',acquire)
    monkeypatch.setattr(core,'_run_lifecycle',lambda template,data,acquisition,life,parent,runtime,engine:dict(lifecycle=life))
    receipt=core._run_parent({'parent':2},tmp_path)
    assert calls==list(range(2,64,4))
    assert len(receipt['lifecycles'])==16 and receipt['trace_bytes']>0
