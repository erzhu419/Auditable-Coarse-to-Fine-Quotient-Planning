"""History intervention: native continuation, fresh start and retained cost scopes."""
from fractions import Fraction
from pathlib import Path
import numpy as np
import pytest

from acfqp.science import continual_v303 as prior
from acfqp.science import history_control_v304 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/history_control_v304/runtime/tests_driver'


def dataset(stage):
    memory=core.SpawnMemory('LIBRARY')
    for i in range(256): memory.observe(1 if stage=='A1' else 1+i%2)
    return dict(lifecycle=0,parent=0,afterstates=np.tile([1,1,0,0]+[0]*12,(7,1)).astype(np.int32),
        rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),ends=np.asarray([2,4,7],dtype=np.int64),
        terminal_codes=np.full(3,-1,dtype=np.int32),fit_game_count=2,fit_step_end=4,fit_end_raw=8,
        fit_memory=memory.to_payload(),costs={'excluded_tail_raw_tiles':3},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST',steps=2 if i<2 else 3) for i in range(3)])


class Evaluator:
    def state(self): return 0
    def evaluate_games(self,leaf,p,true,seeds,depth,max_steps):
        assert not leaf.weights.flags.writeable and depth==2 and max_steps==8192
        return dict(game_summaries=[dict(seed=s,status='LOST',utility=-4.,steps=1) for s in seeds],
            counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


def fixture(monkeypatch):
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    template=core.QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD); template.freeze()
    def acquisition(leaf,life,parent,emit,runtime,**kw):
        return dict(dataset=dataset(kw['phase']),acquisition=dict(warmup={'raw_tiles':7},training={'raw_tiles':20}))
    def split(leaf,p,true,seeds,runtime,max_steps):
        assert not leaf.risk_weights.flags.writeable
        return dict(Evaluator().evaluate_games(leaf,p,true,seeds,2,max_steps),representation_counts={},setup_counts={})
    monkeypatch.setattr(prior,'acquire_dataset',acquisition)
    monkeypatch.setattr(prior,'evaluate_split',split)
    old=prior._run_lifecycle(template,0,0,BUILD,Evaluator(),lambda r:None)
    return template,{'A1':dataset('A1'),'B':dataset('B')},old


def test_native_history_reproduces_and_fresh_starts_without_A1(monkeypatch):
    template,data,old=fixture(monkeypatch)
    result=core._run_lifecycle(template,data,old,BUILD,Evaluator())
    for family in ('MC','LOCAL'):
        fresh=result['arms'][family+'_FRESH_B']; inherited=result['arms'][family+'_AFTER_A1_B']
        assert fresh['head_updates']==4 and inherited['head_updates']==8
        assert fresh['head_updates_by_stage']=={'B':{'before':0,'after':4}}
        assert inherited['head_updates_by_stage']=={'A1':{'before':0,'after':4},'B':{'before':4,'after':8}}
        assert fresh['fit_by_stage']['B']['target_counts']==inherited['fit_by_stage']['B']['target_counts']
    fresh=result['arms']['LOCAL_FRESH_B']['fit_by_stage']['B']['first_sample']
    inherited=result['arms']['LOCAL_AFTER_A1_B']['fit_by_stage']['B']['first_sample']
    assert fresh['risk_probability']==.5 and inherited['risk_probability']<.5
    assert result['arms']['SOURCE']['evaluation'] is old['stages']['B']['arms']['SOURCE']['evaluations']['B']
    assert not result['arms']['SOURCE']['evaluation_is_new'] and template.updates==0
    assert result['evaluation_belief']==old['evaluation_beliefs']['B']


def test_changed_original_fit_is_rejected(monkeypatch):
    template,data,old=fixture(monkeypatch)
    old['stages']['A1']['arms']['MC']['fit']['first_sample']['error']+=1
    with pytest.raises(ValueError,match='Inherited fit'):
        core._run_lifecycle(template,data,old,BUILD,Evaluator())


def test_changed_retained_B_belief_is_rejected(monkeypatch):
    template,data,old=fixture(monkeypatch)
    old['evaluation_beliefs']['B']['estimated_p_four']=.9
    with pytest.raises(ValueError,match='evaluation belief'):
        core._run_lifecycle(template,data,old,BUILD,Evaluator())


def test_reused_SOURCE_work_and_additional_A1_history_are_separate(monkeypatch):
    template,data,old=fixture(monkeypatch); row=core._run_lifecycle(template,data,old,BUILD,Evaluator())
    base=dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)
    old_document=dict(by_lifecycle=[old],accounting=dict(inherited_costs_per_arm={'SOURCE':base},canonical_trace_bytes=11),
        recovery={'training_raw_tiles_physical_lower_bound':99})
    parent=dict(reconstruction=dict(canonical_rows_read=10,reconstructed_stages=2,cpu_seconds=.1,reconstruction_counts={}),
        cpu_seconds=1.,compiler_cpu_seconds=.2)
    account=core.build_accounting(old_document,[row],[parent],.05,1.)
    assert account['new_training_environment_observations']==account['physical_acquisitions']==0
    assert account['new_evaluation_games']==128 and account['reused_evaluation_games']==32
    assert account['economic_training_raw_tiles_per_arm']==dict(SOURCE=132,MC_FRESH_B=132,
        LOCAL_FRESH_B=132,MC_AFTER_A1_B=159,LOCAL_AFTER_A1_B=159)
    assert account['processing_cpu_seconds_per_arm']['SOURCE']==dict(fit=0,heldout=0,head_setup=0)
    assert account['evaluation_counts_per_arm']['SOURCE']==dict(environment={},planning={})
    assert account['processed_training_samples']==account['final_cumulative_updates']
    assert account['historical_sequence_physical_training_raw_tiles_lower_bound']==99
    assert not account['historical_total_compute_closed']


def test_configuration_retains_original_B_seeds_and_history_primary():
    config=core.configuration(BUILD/'source.json')
    assert config['seed_evaluation']==core.evaluation_seed(0,'B',0)==303900100000
    assert config['primary']=='LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B'
    assert config['retained_stages']==['A1','B'] and config['new_training_acquisitions']==0
    assert config['alpha']==.0025 and config['new_evaluation_games']==8192
