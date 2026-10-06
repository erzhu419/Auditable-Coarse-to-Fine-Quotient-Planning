"""New continuation wiring and first-observed task-belief tests."""
from fractions import Fraction
from pathlib import Path
import numpy as np
import pytest

from acfqp.science import continual_v303 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import predict_components

BUILD=Path(__file__).resolve().parents[1]/'reports/continual_v303/runtime/tests_driver'


def fixture():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    template=QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD); template.freeze()
    board=np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    return template,board


def data(board,stage):
    memory=SpawnMemory('LIBRARY')
    for i in range(256): memory.observe(1 if stage=='A1' else 2 if stage=='B' else 1+i%2)
    return dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),
        costs={'excluded_tail_raw_tiles':3},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST') for i in range(3)])


def acquisition():
    return dict(warmup=dict(raw_tiles=7,environment_counts={},direct_counts={},memory_counts={}),
        training=dict(raw_tiles=20,counts=dict(environment={},planning={},learning={}),memory_counts={}),
        reconstruction=dict(counts={},memory_counts={},cpu_seconds=.1),cpu_seconds=.3,
        native_setup_counts={},native_setup_seconds=.01)


def result(p,true,seeds):
    assert p==(1/258 if true==.1 else 257/258)
    return dict(game_summaries=[dict(seed=seed,status='LOST',utility=-4.,steps=1) for seed in seeds],
        counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


class Evaluator:
    def state(self): return 0
    def evaluate_games(self,leaf,p,true,seeds,depth,max_steps):
        assert depth==2 and max_steps==8192 and not leaf.weights.flags.writeable
        return result(p,true,seeds)


def split_eval(leaf,p,true,seeds,runtime,max_steps):
    assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
    return dict(result(p,true,seeds),representation_counts={},setup_counts={})


def run_fixture(monkeypatch):
    template,board=fixture(); calls=[]
    def acquire(leaf,life,parent,emit,runtime,**kw):
        stage=kw['phase']; calls.append(stage)
        assert leaf is template and not leaf.weights.flags.writeable
        assert kw['p_four']==core.PROBABILITIES[core.TASKS[stage]]
        assert kw['warmup_seed_base']==core.warmup_seed_base(stage)
        assert kw['training_seed_base']==core.training_seed_base(stage)
        return dict(dataset=data(board,stage),acquisition=acquisition())
    monkeypatch.setattr(core,'acquire_dataset',acquire)
    monkeypatch.setattr(core,'evaluate_split',split_eval)
    return template,board,calls


def test_same_native_arrays_and_values_continue_without_reinitialization(monkeypatch):
    template,board,calls=run_fixture(monkeypatch); created=[]; fits=[]
    ctor,nativefit=core.SplitLeaf,core.fit_split
    def once(*args):
        leaf=ctor(*args); created.append(leaf); return leaf
    def fit(leaf,dataset,runtime,alpha):
        probability=predict_components(leaf,board)['risk_probability']
        fitted=nativefit(leaf,dataset,runtime,alpha=alpha)
        assert fitted['first_sample']['risk_probability']==probability
        fits.append((leaf,leaf.reward_weights,leaf.risk_weights,probability))
        return fitted
    monkeypatch.setattr(core,'SplitLeaf',once); monkeypatch.setattr(core,'fit_split',fit)
    row=core._run_lifecycle(template,0,0,BUILD,Evaluator(),lambda row:None)
    assert len(created)==1 and calls==['A1','B','A2']
    assert all(f[0] is created[0] and f[1] is fits[0][1] and f[2] is fits[0][2] for f in fits)
    assert fits[0][3]==.5 and fits[2][3]<fits[1][3]<.5
    for index,stage in enumerate(core.STAGES):
        for arm in ('MC','LOCAL_RISK'):
            saved=row['stages'][stage]['arms'][arm]
            assert saved['head_updates_before']==4*index and saved['head_updates_after']==4*(index+1)
            assert saved['parameters_retained'] and saved['processed_training_samples']==4
    assert template.updates==template.parent.source.updates==0


def test_first_observed_task_beliefs_and_checkpoint_seeds_are_fixed(monkeypatch):
    template,board,calls=run_fixture(monkeypatch)
    row=core._run_lifecycle(template,0,0,BUILD,Evaluator(),lambda row:None)
    assert row['stages']['A2']['fit_snapshot']['estimated_p_four']==.5
    assert row['evaluation_beliefs']['A']['estimated_p_four']==1/258
    for stage in core.STAGES:
        for arm in core.ARMS:
            evaluated=row['stages'][stage]['arms'][arm]['evaluations']
            assert set(evaluated)==({'A'} if stage=='A1' else {'A','B'})
            for task,value in evaluated.items():
                assert value['estimated_p_four']==row['evaluation_beliefs'][task]['estimated_p_four']
                assert [g['seed'] for g in value['game_summaries']]==[core.evaluation_seed(0,task,e) for e in range(32)]


def test_sequence_costs_allocate_heads_once_and_pay_all_three_carriers(monkeypatch):
    template,board,calls=run_fixture(monkeypatch)
    row=core._run_lifecycle(template,0,0,BUILD,Evaluator(),lambda row:None)
    inherited=dict(source_training_raw_tiles=100,source_training_games=4,source_training_environment_counts={},
        source_training_seconds=1.,dynamics_raw_tiles=5,dynamics_costs={})
    old=dict(accounting=dict(inherited_costs_per_arm={'SOURCE':inherited},
        new_training_environment_observations=999,evaluation_counts={}))
    cost=core.build_accounting(old,[row],[dict(trace_bytes=11,cpu_seconds=1.,compiler_cpu_seconds=.2)],.05,1.)
    assert cost['physical_acquisitions']==3 and cost['new_training_environment_observations']==81
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,186)
    assert cost['processed_training_samples']==cost['final_cumulative_updates']=={'SOURCE':0,'MC':12,'LOCAL_RISK':12}
    assert cost['private_head_weight_bytes_created']['LOCAL_RISK']==row['head_setup']['LOCAL_RISK']['private_weight_bytes']
    assert cost['excluded_tail_raw_tiles']==9 and cost['development_reference']['previous_target_raw_tiles']==999
    assert cost['fit_counts']['LOCAL_RISK']['table_updates']==2*cost['fit_counts']['MC']['table_updates']


def test_new_seed_ranges_and_final_retained_task_primary(tmp_path):
    config=core.configuration(tmp_path/'summary.json')
    assert config['primary']=='LOCAL_RISK_minus_SOURCE_FINAL_AB_COMPLETE_GAME_UTILITY'
    warm={core.warmup_seed_base(s)+l*1000000+e for s in core.STAGES for l in range(64) for e in range(128)}
    train={core.training_seed_base(s)+l*10000000 for s in core.STAGES for l in range(64)}
    evaluated={core.evaluation_seed(l,t,e) for l in range(64) for t in ('A','B') for e in range(32)}
    assert len(warm)==24576 and len(train)==192 and len(evaluated)==4096
    assert not warm&train and not warm&evaluated and not train&evaluated
    assert config['model_probability']=='FIRST_ENCOUNTER_OBSERVED_FIT_PREFIX_FIXED_BY_TASK'


def test_new_checkpoint_evaluator_rejects_feedback():
    template,board=fixture()
    class Feedback(Evaluator):
        cursor=0
        def state(self): return self.cursor
        def evaluate_games(self,*args,**kw):
            result=super().evaluate_games(*args,**kw); self.cursor+=1; return result
    with pytest.raises(ValueError,match='Static checkpoint'):
        core._evaluate(template,'SOURCE',0,'A',{'estimated_p_four':1/258},BUILD,Feedback())
