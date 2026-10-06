"""Target-only driver: retained fit identity, observed belief, static new eval and costs."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import b_control_v300 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/b_control_v300/runtime/tests_driver'


def fixture():
    rule = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',3)
    native = NtupleValue(rule,BUILD)
    template = QueryTD(QueryParent(native,core.QUERY,core.QUERY,.5),'PRIOR',BUILD)
    template.freeze()
    prefix, final = SpawnMemory('LIBRARY'), SpawnMemory('LIBRARY')
    for _ in range(256): prefix.observe(1)
    for i in range(512): final.observe(1+i%2)
    board = np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    data = dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=prefix.to_payload(),
        actor_memory_B_end=final.to_payload(),costs={},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT') for i in range(3)])
    mc = QueryTD(template.parent,'PRIOR',BUILD)
    fit = core.fit_consolidated(mc,data,'EPISODE_MEAN_MC',BUILD)
    mc.freeze()
    snapshot_memory=SpawnMemory.from_payload(data['fit_memory'])
    snapshot_probability=snapshot_memory.predict()
    old = dict(lifecycle=0,parent=0,dataset=core.compact_dataset(data),
        evaluation_snapshot=dict(memory=snapshot_memory.to_payload(),estimated_p_four=snapshot_probability),
        arms=dict(FROZEN=dict(heldout=core.score_retained(template,data,BUILD)),
            EPISODE_MEAN_MC=dict(fit=fit,heldout=core.score_retained(mc,data,BUILD))))
    return template,data,old


class Evaluator:
    def __init__(self): self.stream = {'cursor':0}; self.calls=[]
    def state(self): return dict(self.stream)
    def evaluate_games(self,leaf,p,actual,seeds,depth,max_steps):
        assert p==1/258 and actual==.5 and not leaf.weights.flags.writeable
        assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
        assert depth==2 and max_steps==8192
        self.calls.append(leaf.updates)
        return dict(game_summaries=[dict(seed=seed,status='LOST',utility=-4.,steps=1) for seed in seeds],
            counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


def test_same_retained_data_fresh_source_heads_fixed_observed_target_and_static_eval(monkeypatch):
    template,data,old = fixture()
    fresh_counts, target_probs = [],[]
    def fresh(parent,kind,runtime):
        head=QueryTD(parent,kind,runtime)
        np.testing.assert_array_equal(head.weights,template.weights)
        fresh_counts.append(head.updates)
        return head
    native_target = core.fit_control
    def control(head,dataset,p,runtime):
        target_probs.append(p)
        return native_target(head,dataset,p,runtime)
    monkeypatch.setattr(core,'QueryTD',fresh)
    monkeypatch.setattr(core,'fit_control',control)
    engine=Evaluator()
    row=core._run_lifecycle(template,data,old,BUILD,engine)
    assert fresh_counts==[0,0] and target_probs==[1/258]
    assert engine.calls==[0,4,4] and engine.state()=={'cursor':0}
    assert row['dataset']==old['dataset'] and row['evaluation_snapshot']==old['evaluation_snapshot']
    assert row['arms']['MC']['heldout']['game_metrics']==old['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics']
    assert all(row['arms'][a]['sample_counter']==row['arms'][a]['processed_training_samples'] for a in core.ARMS)
    assert all(row['arms'][a]['static_evaluation_valid'] for a in core.ARMS)
    assert row['arms']['EXPECTED_CONTROL']['fit']['game_head_targets_frozen']
    assert template.updates==template.parent.source.updates==0


def test_driver_rejects_evaluation_feedback():
    template,data,old = fixture()
    class Feedback(Evaluator):
        def evaluate_games(self,*args,**kwargs):
            result=super().evaluate_games(*args,**kwargs)
            self.stream['cursor']+=1
            return result
    with pytest.raises(ValueError,match='Static scoring/evaluation'):
        core._run_lifecycle(template,data,old,BUILD,Feedback())


def test_new_seed_family_and_no_true_probability_in_training_settings(tmp_path):
    settings=core.configuration(tmp_path/'summary.json')
    assert settings['alpha']==.0025 and settings['source_initialization']=='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES'
    assert settings['target_probability']=='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION'
    assert settings['primary']=='EXPECTED_CONTROL_minus_SOURCE_COMPLETE_GAME_UTILITY'
    seeds=[core.evaluation_seed(l,e) for l in range(64) for e in range(32)]
    previous={298900000000+l*1000000+e for l in range(64) for e in range(32)}
    assert len(set(seeds))==2048 and not set(seeds).intersection(previous)


def test_costs_inherit_all_raw_once_and_charge_target_planning_and_processing():
    template,data,old_life = fixture()
    life=core._run_lifecycle(template,data,old_life,BUILD,Evaluator())
    inherited=dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)
    old=dict(accounting=dict(inherited_costs_per_arm={'FROZEN':inherited},
        economic_training_raw_tiles_per_arm={'FROZEN':132},new_training_environment_observations=27,
        new_actor_B_raw_tiles=20,new_warmup_raw_tiles=7,new_training_environment_counts={'raw_tile_productions':27},
        new_actor_B_counts={},new_warmup_direct_counts={},excluded_tail_raw_tiles=3,canonical_trace_bytes=11))
    parent=dict(reconstruction=dict(canonical_rows_read=12,reconstruction_counts={'a':5},cpu_seconds=.1),
        cpu_seconds=1.,compiler_cpu_seconds=.2)
    result=core.build_accounting(old,[life],[parent],.05,1.)
    assert result['new_training_environment_observations']==result['physical_acquisitions']==0
    assert result['retained_B_acquisition_raw_tiles']==27 and result['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,132)
    assert result['inherited_B_acquisition']['excluded_tail_raw_tiles']==3
    assert result['processed_training_samples']=={'SOURCE':0,'MC':4,'EXPECTED_CONTROL':4}
    assert result['fit_planning_counts']['SOURCE']==result['fit_planning_counts']['MC']=={}
    assert result['fit_planning_counts']['EXPECTED_CONTROL']['expected_control_target_assignments']==4
    assert result['processing_cpu_seconds_per_arm']['EXPECTED_CONTROL']['fit']>0.
    assert result['head_setup_counts']['EXPECTED_CONTROL']['source_weight_bytes_copied']>0
    assert result['private_head_weight_bytes_created']['SOURCE']==0 and result['fit_counts']['SOURCE']=={}
    assert result['worker_cpu_seconds']==1. and result['compiler_cpu_seconds']==.2 and result['reconstruction_cpu_seconds']==.1
