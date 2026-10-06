"""New representation driver uses retained observations and frozen fresh evaluations."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import split_risk_v301 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/split_risk_v301/runtime/tests_driver'


def fixture():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    template=QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD)
    template.freeze()
    memory,final=SpawnMemory('LIBRARY'),SpawnMemory('LIBRARY')
    for _ in range(256): memory.observe(1)
    for i in range(512): final.observe(1+i%2)
    board=np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    data=dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),
        actor_memory_B_end=final.to_payload(),costs={},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST') for i in range(3)])
    mc=QueryTD(template.parent,'PRIOR',BUILD)
    fit=core.fit_consolidated(mc,data,'EPISODE_MEAN_MC',BUILD); mc.freeze()
    snapshot=SpawnMemory.from_payload(data['fit_memory']); p=snapshot.predict()
    old=dict(lifecycle=0,parent=0,dataset=core.compact_dataset(data),
        evaluation_snapshot=dict(memory=snapshot.to_payload(),estimated_p_four=p),
        arms=dict(FROZEN=dict(heldout=core.score_retained(template,data,BUILD)),
            EPISODE_MEAN_MC=dict(fit=fit,heldout=core.score_retained(mc,data,BUILD))))
    return template,data,old


def game_result(seeds):
    return dict(game_summaries=[dict(seed=seed,status='LOST',utility=-4.,steps=1) for seed in seeds],
        counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


class Evaluator:
    def __init__(self): self.cursor=0; self.calls=[]
    def state(self): return self.cursor
    def evaluate_games(self,leaf,p,actual,seeds,depth,max_steps):
        assert p==1/258 and actual==.5 and depth==2 and max_steps==8192
        assert not leaf.weights.flags.writeable
        assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
        self.calls.append(leaf.updates)
        return game_result(seeds)


def evaluate_split(leaf,p,actual,seeds,runtime,max_steps):
    assert p==1/258 and actual==.5 and max_steps==8192
    assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
    assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
    return dict(game_result(seeds),representation_counts={'risk_sigmoid_calls':5},setup_counts={'cpp_library_cache_hits':1})


def test_fresh_reward_copies_bounded_heads_and_observed_belief_with_shared_reward_fit(monkeypatch):
    template,data,old=fixture(); initialized=[]
    native=core.SplitLeaf
    def fresh(template_,kind,runtime):
        head=native(template_,kind,runtime)
        np.testing.assert_array_equal(head.reward_weights,template.parent.source.weights)
        assert not np.any(head.risk_weights) and head.updates==0
        initialized.append(kind)
        return head
    monkeypatch.setattr(core,'SplitLeaf',fresh)
    monkeypatch.setattr(core,'evaluate_split',evaluate_split)
    engine=Evaluator(); row=core._run_lifecycle(template,data,old,BUILD,engine)
    assert initialized==['LOCAL_RISK','GLOBAL_RISK'] and engine.calls==[0,4]
    assert row['evaluation_snapshot']==old['evaluation_snapshot'] and engine.state()==0
    assert [row['arms'][arm]['sample_counter'] for arm in core.ARMS]==[0,4,4,4]
    assert template.updates==template.parent.source.updates==0
    local=row['arms']['LOCAL_RISK']['heldout']['component_game_metrics']
    global_=row['arms']['GLOBAL_RISK']['heldout']['component_game_metrics']
    assert all(left['reward_mse']==right['reward_mse'] for left,right in zip(local,global_))
    assert row['arms']['MC']['heldout']['game_metrics']==old['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics']


def test_driver_rejects_static_evaluation_feedback(monkeypatch):
    template,data,old=fixture()
    monkeypatch.setattr(core,'evaluate_split',evaluate_split)
    class Feedback(Evaluator):
        def evaluate_games(self,*args,**kwargs):
            result=super().evaluate_games(*args,**kwargs); self.cursor+=1
            return result
    with pytest.raises(ValueError,match='Static evaluation changed'):
        core._run_lifecycle(template,data,old,BUILD,Feedback())


def test_frozen_seed_family_and_substantively_different_head_settings(tmp_path):
    settings=core.configuration(tmp_path/'summary.json')
    assert settings['primary']=='GLOBAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY'
    assert settings['alpha']==.0025 and len(settings['global_feature_names'])==20
    assert settings['reward_target']=='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS'
    assert settings['risk_target']=='COMPLETE_FIT_GAME_WON_LABEL'
    fresh={core.evaluation_seed(l,e) for l in range(64) for e in range(32)}
    old={base+l*1000000+e for base in (298900000000,300900000000) for l in range(64) for e in range(32)}
    assert len(fresh)==2048 and not fresh.intersection(old)


def test_costs_keep_retained_input_and_actual_two_head_computation(monkeypatch):
    template,data,old_life=fixture()
    monkeypatch.setattr(core,'evaluate_split',evaluate_split)
    row=core._run_lifecycle(template,data,old_life,BUILD,Evaluator())
    inherited=dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)
    old=dict(accounting=dict(inherited_costs_per_arm={'FROZEN':inherited},
        economic_training_raw_tiles_per_arm={'FROZEN':132},new_training_environment_observations=27,
        new_actor_B_raw_tiles=20,new_warmup_raw_tiles=7,new_training_environment_counts={},new_actor_B_counts={},
        new_warmup_direct_counts={},excluded_tail_raw_tiles=3,canonical_trace_bytes=11))
    parent=dict(reconstruction=dict(canonical_rows_read=12,reconstruction_counts={'a':5},cpu_seconds=.1),
        cpu_seconds=1.,compiler_cpu_seconds=.2)
    result=core.build_accounting(old,[row],[parent],.05,1.)
    assert result['new_training_environment_observations']==result['physical_acquisitions']==0
    assert result['retained_B_acquisition_raw_tiles']==27 and result['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,132)
    assert result['processed_training_samples']=={'SOURCE':0,'MC':4,'LOCAL_RISK':4,'GLOBAL_RISK':4}
    assert result['fit_counts']['SOURCE']=={} and result['fit_counts']['GLOBAL_RISK']==row['arms']['GLOBAL_RISK']['fit']['learning_counts']
    assert result['evaluation_representation_counts']['SOURCE']=={} and result['evaluation_representation_counts']['GLOBAL_RISK']=={'risk_sigmoid_calls':5}
    assert result['private_head_weight_bytes_created']['LOCAL_RISK']>result['private_head_weight_bytes_created']['GLOBAL_RISK']
    assert result['processing_cpu_seconds_per_arm']['GLOBAL_RISK']['fit']>0.
    assert result['inherited_B_acquisition']['excluded_tail_raw_tiles']==3
