"""Native context-bank persistence and same-facts reuse wiring."""
from fractions import Fraction
from pathlib import Path
import numpy as np
import pytest

from acfqp.science import continual_v303 as prior
from acfqp.science import context_continual_v305 as core
from acfqp.science import history_control_v304 as history
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/context_continual_v305/runtime/tests_driver'


def dataset(stage):
    memory=SpawnMemory('LIBRARY')
    for i in range(256): memory.observe(1+i%2 if stage=='B' else 1)
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
    template=QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD); template.freeze()
    def acquisition(leaf,life,parent,emit,runtime,**kw):
        return dict(dataset=dataset(kw['phase']),acquisition=dict(warmup={'raw_tiles':7},training={'raw_tiles':20}))
    def split(leaf,p,true,seeds,runtime,max_steps):
        assert not leaf.risk_weights.flags.writeable
        return dict(Evaluator().evaluate_games(leaf,p,true,seeds,2,max_steps),representation_counts={},setup_counts={})
    monkeypatch.setattr(prior,'acquire_dataset',acquisition); monkeypatch.setattr(prior,'evaluate_split',split)
    old=prior._run_lifecycle(template,0,0,BUILD,Evaluator(),lambda r:None)
    fresh=history._run_lifecycle(template,{'A1':dataset('A1'),'B':dataset('B')},old,BUILD,Evaluator())
    return template,old,fresh,iter((0,s,dataset(s)) for s in core.STAGES)


def test_reuses_A_arrays_and_leaves_B_parameters_untouched_on_return(monkeypatch):
    template,old,fresh,stages=fixture(monkeypatch); calls=[]; fit=core.fit_split
    def tracked(leaf,data,runtime,alpha):
        nonlocal saved_B_reward,saved_B_risk
        calls.append((leaf,leaf.reward_weights,leaf.risk_weights,leaf.updates))
        if len(calls)==3:
            assert calls[1][0].updates==4
            assert np.array_equal(calls[1][1],saved_B_reward) and np.array_equal(calls[1][2],saved_B_risk)
        result=fit(leaf,data,runtime,alpha=alpha)
        if len(calls)==2:
            saved_B_reward=leaf.reward_weights.copy(); saved_B_risk=leaf.risk_weights.copy()
        return result
    saved_B_reward=saved_B_risk=None
    monkeypatch.setattr(core,'fit_split',tracked)
    row=core._run_lifecycle(template,old,fresh,stages,BUILD,Evaluator())
    assert calls[0][0] is calls[2][0] and calls[0][1] is calls[2][1] and calls[0][2] is calls[2][2]
    assert calls[1][0] is not calls[0][0] and [c[3] for c in calls]==[0,0,4]
    assert [row['stages'][s]['context_route']['context_id'] for s in core.STAGES]==[0,1,0]
    assert [b['head_updates'] for b in row['context_bank']['banks']]==[8,4]
    assert row['context_bank']['counts']['observe_calls']==3 and row['context_bank']['counts']['select_calls']==5
    for stage in ('B','A2'):
        assert {t:r['context_id'] for t,r in row['stages'][stage]['evaluation_routes'].items()}==dict(A=0,B=1)
    assert row['stages']['B']['arms']['CONTEXT_LOCAL']['evaluations']['A']==row['stages']['A1']['arms']['CONTEXT_LOCAL']['evaluations']['A']
    assert row['stages']['A2']['arms']['CONTEXT_LOCAL']['evaluations']['B']==row['stages']['B']['arms']['CONTEXT_LOCAL']['evaluations']['B']


def test_old_controls_are_reused_not_fitted_or_evaluated(monkeypatch):
    template,old,fresh,stages=fixture(monkeypatch)
    row=core._run_lifecycle(template,old,fresh,stages,BUILD,Evaluator())
    for stage in core.STAGES:
        for name,original in [('SOURCE','SOURCE'),('SHARED_LOCAL','LOCAL_RISK')]:
            arm=row['stages'][stage]['arms'][name]
            assert not arm['evaluation_is_new'] and not arm['heldout_is_new']
            assert arm['evaluations'] is old['stages'][stage]['arms'][original]['evaluations']
    assert template.updates==0


def test_changed_fresh_B_numerical_anchor_is_rejected(monkeypatch):
    template,old,fresh,stages=fixture(monkeypatch)
    fresh['arms']['LOCAL_FRESH_B']['fit_by_stage']['B']['first_sample']['reward_error']+=1
    with pytest.raises(ValueError,match='fresh B numerical'):
        core._run_lifecycle(template,old,fresh,stages,BUILD,Evaluator())


def test_context_costs_charge_extra_parameters_and_only_actual_new_work(monkeypatch):
    template,old,fresh,stages=fixture(monkeypatch);row=core._run_lifecycle(template,old,fresh,stages,BUILD,Evaluator())
    base=dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)
    old_document=dict(by_lifecycle=[old],accounting=dict(inherited_costs_per_arm={'SOURCE':base},canonical_trace_bytes=11),
        recovery={'training_raw_tiles_physical_lower_bound':99})
    parent=dict(reconstruction=dict(canonical_rows_read=10,reconstructed_stages=3,cpu_seconds=.1,counts={}),cpu_seconds=1.,compiler_cpu_seconds=.2)
    cost=core.build_accounting(old_document,[row],[parent],.05,1.)
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,186)
    assert cost['new_training_environment_observations']==cost['physical_acquisitions']==0
    assert cost['new_processed_training_samples']==dict(SOURCE=0,SHARED_LOCAL=0,CONTEXT_LOCAL=12)
    assert cost['new_evaluation_games']==160 and cost['reused_evaluation_games']==320
    assert cost['total_contexts_created']==2
    assert cost['context_private_weight_bytes_created']==2*cost['inherited_shared_private_weight_bytes_per_lifecycle']
    assert cost['peak_context_private_weight_bytes_per_lifecycle']==cost['context_private_weight_bytes_created']
    assert not cost['historical_total_compute_closed']


def test_configuration_keeps_shared_planning_and_observed_context_primary():
    settings=core.configuration(BUILD/'v303.json',BUILD/'v304.json')
    assert settings['primary']=='CONTEXT_LOCAL_minus_SHARED_LOCAL_FINAL_AB'
    assert settings['planning_probability']=='UNCHANGED_V303_FIRST_OBSERVED_TASK_BELIEF'
    assert settings['log_bayes_factor_threshold']==0 and settings['new_training_acquisitions']==0
