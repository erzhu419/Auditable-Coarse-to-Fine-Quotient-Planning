"""Real first-context fits, observed routing, and reuse without another fit."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import first_adapt_v308 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/first_adapt_v308/runtime/tests/driver'


def memory_for(probability):
    memory = SpawnMemory('LIBRARY')
    count = round(256*probability)
    for index in range(256):
        memory.observe(2 if index<count else 1)
    return memory


def dataset(stage):
    memory = memory_for(.5 if stage=='B' else 0.)
    scale = {'A1':1.,'B':2.,'A2':3.}[stage]
    return dict(lifecycle=0,parent=0,
        afterstates=np.tile([1,1,0,0]+[0]*12,(7,1)).astype(np.int32),
        rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7])*scale,
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),
        costs=dict(excluded_tail_raw_tiles=3),
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT',status='LOST',
                    steps=2 if i<2 else 3) for i in range(3)])


class Evaluator:
    def __init__(self,template):
        self.template = template
        self.calls = []

    def state(self):
        return 0

    def evaluate_games(self,leaf,p,true,seeds,depth,max_steps):
        assert not leaf.weights.flags.writeable and depth==2 and max_steps==8192
        if isinstance(leaf,core.SplitLeaf):
            assert not leaf.risk_weights.flags.writeable
            arm = 'CONTEXT_LOCAL'
        else:
            arm = 'SOURCE' if leaf is self.template else 'CONTEXT_MC'
        task = 'B' if true==.5 else 'A'
        assert true==core.PROBABILITIES[task]
        assert seeds==[core.evaluation_seed(0,task,episode) for episode in range(32)]
        self.calls.append(dict(arm=arm,task=task,p=p,leaf=leaf,weights=leaf.weights,
            risk=leaf.risk_weights if arm=='CONTEXT_LOCAL' else None))
        utility = float(leaf.weights.sum())
        if arm=='CONTEXT_LOCAL':
            utility+=float(leaf.risk_weights.sum())
        return dict(game_summaries=[dict(seed=seed,status='LOST',utility=utility,steps=1)
                    for seed in seeds],counts=dict(environment={},planning={}),seconds=0.,cpu_seconds=0.)


def fixture(monkeypatch,detectors=None):
    rule = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source = NtupleValue(rule,BUILD)
    template = QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD)
    template.freeze(); engine = Evaluator(template)
    detector_probabilities = detectors or dict(A1=0.,B=.5,A2=0.)
    events = []; acquisitions = []; facts = {}
    def acquire(leaf,life,parent,stage,router,emit,runtime,**kw):
        assert leaf is template and leaf.updates==0 and not leaf.weights.flags.writeable
        assert (life,parent)==(0,0) and kw['p_four']==core.PROBABILITIES[core.TASKS[stage]]
        index = core.STAGES.index(stage)
        assert kw['warmup_seed_base']==308100000000+index*100000
        assert kw['training_seed_base']==308200000000+index*100000
        assert kw['raw_budget']==131072
        memory = memory_for(detector_probabilities[stage]); p = memory.predict()
        payload = memory.to_payload()
        assert not set(payload).intersection(('task','stage','phase','true_p_four','context_id'))
        route = router.observe(payload)
        assert route['statistics']==dict(observations=256,fours=round(256*detector_probabilities[stage]))
        events.append((stage,'DETECTION',route['context_id']))
        data = dataset(stage) if route['created'] else None
        facts[stage] = data
        training = (dict(raw_tiles=20,counts=dict(environment={'actual_spawns':20},
            planning={'planning_calls':2},learning={})) if route['created'] else None)
        acquisition = dict(warmup=dict(raw_tiles=256,environment_counts={'actual_spawns':256},
            direct_counts={},memory_counts={}),training=training,native_setup_counts={},cpu_seconds=.2,
            reconstruction=dict(counts={},memory_counts={},cpu_seconds=.1))
        acquisitions.append((stage,route,data))
        return dict(route=route,detector_belief=dict(memory=payload,estimated_p_four=p),
                    dataset=data,acquisition=acquisition)
    def split(leaf,p,true,seeds,runtime,max_steps):
        return dict(engine.evaluate_games(leaf,p,true,seeds,2,max_steps),
                    representation_counts={},setup_counts={})
    monkeypatch.setattr(core,'acquire_stage',acquire)
    monkeypatch.setattr(core,'evaluate_split',split)
    fits = {arm:[] for arm in core.LEARNERS}
    native_mc, native_local = core.fit_consolidated, core.fit_split
    def record(arm,leaf,data):
        stage = next(stage for stage,value in facts.items() if value is data)
        assert events[-1][0]==stage and events[-1][1] in ('DETECTION','FIT')
        assert leaf.updates==0
        np.testing.assert_array_equal(leaf.weights,template.parent.source.weights)
        if arm=='CONTEXT_LOCAL':
            assert not np.any(leaf.risk_weights)
        fits[arm].append(dict(stage=stage,leaf=leaf,data=data,weights=leaf.weights,
            risk=leaf.risk_weights if arm=='CONTEXT_LOCAL' else None))
        events.append((stage,'FIT',arm))
    def mc(leaf,data,method,runtime,alpha):
        record('CONTEXT_MC',leaf,data)
        assert method=='EPISODE_MEAN_MC' and alpha==.0025
        return native_mc(leaf,data,method,runtime,alpha=alpha)
    def local(leaf,data,runtime,alpha):
        record('CONTEXT_LOCAL',leaf,data)
        assert alpha==.0025
        return native_local(leaf,data,runtime,alpha=alpha)
    monkeypatch.setattr(core,'fit_consolidated',mc)
    monkeypatch.setattr(core,'fit_split',local)
    return template,engine,acquisitions,fits,events


def run_fixture(values):
    template,engine,_,_,_ = values
    return core._run_lifecycle(template,0,0,BUILD,engine,lambda row:None)


def test_new_banks_start_from_source_and_return_a_reuses_original_arrays_without_fit(monkeypatch):
    values = fixture(monkeypatch); row = run_fixture(values)
    template,engine,acquisitions,fits,events = values
    assert [route['context_id'] for _,route,_ in acquisitions]==[0,1,0]
    assert [route['created'] for _,route,_ in acquisitions]==[True,True,False]
    assert acquisitions[2][2] is None and row['stages']['A2']['dataset'] is None
    assert events==[('A1','DETECTION',0),('A1','FIT','CONTEXT_MC'),('A1','FIT','CONTEXT_LOCAL'),
        ('B','DETECTION',1),('B','FIT','CONTEXT_MC'),('B','FIT','CONTEXT_LOCAL'),('A2','DETECTION',0)]
    assert template.updates==0
    for arm in core.LEARNERS:
        assert [record['stage'] for record in fits[arm]]==['A1','B']
        assert [record['leaf'].updates for record in fits[arm]]==[4,4]
        a_evaluations = [call for call in engine.calls if call['arm']==arm and call['task']=='A']
        assert len(a_evaluations)==3
        assert all(call['weights'] is fits[arm][0]['weights'] for call in a_evaluations)
        if arm=='CONTEXT_LOCAL':
            assert all(call['risk'] is fits[arm][0]['risk'] for call in a_evaluations)
        b_evaluations = [call for call in engine.calls if call['arm']==arm and call['task']=='B']
        assert len(b_evaluations)==2 and all(call['weights'] is fits[arm][1]['weights'] for call in b_evaluations)
        assert row['stages']['A2']['arms'][arm]['fit']['method']=='NONE'
        assert row['stages']['A2']['context_updates_before'][arm]==row['stages']['A2']['context_updates_after'][arm]
    assert [bank['head_updates'] for bank in row['context_bank']['banks']]==[
        dict(CONTEXT_MC=4,CONTEXT_LOCAL=4),dict(CONTEXT_MC=4,CONTEXT_LOCAL=4)]
    assert row['context_bank']['counts']['observe_calls']==3
    assert row['context_bank']['counts']['prototype_commits']==3
    assert row['context_bank']['counts']['select_calls']==2


def test_learners_fit_same_actual_facts_and_observed_route_scores_precede_fits(monkeypatch):
    values = fixture(monkeypatch); row = run_fixture(values)
    _,_,acquisitions,fits,_ = values
    for index in range(2):
        assert fits['CONTEXT_MC'][index]['data'] is fits['CONTEXT_LOCAL'][index]['data']
        assert fits['CONTEXT_MC'][index]['data'] is acquisitions[index][2]
    b = row['stages']['B']['context_route']
    assert b['statistics']==dict(observations=256,fours=128)
    assert b['scores'][0]['log_bayes_factor']<0. and b['created']
    assert row['stages']['A2']['context_route']['prototype_after']['observations']==512
    for stage in ('A1','B'):
        assert {arm:row['stages'][stage]['arms'][arm]['processed_training_samples'] for arm in core.LEARNERS}==dict(CONTEXT_MC=4,CONTEXT_LOCAL=4)


def test_false_new_a2_context_is_paid_fitted_and_actual_return_route_enters_evaluation(monkeypatch):
    values = fixture(monkeypatch,dict(A1=0.,B=.5,A2=1.)); row = run_fixture(values)
    _,engine,acquisitions,fits,_ = values
    assert [route['context_id'] for _,route,_ in acquisitions]==[0,1,2]
    assert row['stages']['A2']['context_route']['created']
    assert row['stages']['A2']['dataset'] is not None
    assert row['stages']['A2']['evaluation_routes']['A']==dict(kind='ACTUAL_STAGE_ROUTE',context_id=2)
    assert row['stages']['A2']['evaluation_routes']['B']['kind']=='READ_ONLY_FIRST_DETECTOR'
    assert row['stages']['A2']['evaluation_routes']['B']['context_id']==1
    for arm in core.LEARNERS:
        assert [record['stage'] for record in fits[arm]]==['A1','B','A2']
        assert all(record['leaf'].updates==4 for record in fits[arm])
        a_evaluations = [call for call in engine.calls if call['arm']==arm and call['task']=='A']
        assert a_evaluations[-1]['weights'] is fits[arm][2]['weights']
        assert a_evaluations[-1]['weights'] is not fits[arm][0]['weights']
        assert row['stages']['A2']['context_updates_after'][arm]=={'0':4,'1':4,'2':4}
    assert len(row['context_bank']['banks'])==3


def test_false_b_merge_reuses_actual_context_and_keeps_detector_belief_without_oracle_bank(monkeypatch):
    values = fixture(monkeypatch,dict(A1=0.,B=0.,A2=0.)); row = run_fixture(values)
    _,engine,acquisitions,fits,_ = values
    assert [route['context_id'] for _,route,_ in acquisitions]==[0,0,0]
    assert acquisitions[1][2] is None
    assert row['stages']['B']['dataset'] is None and row['stages']['B']['fit_snapshot'] is None
    assert row['evaluation_beliefs']['B']==row['stages']['B']['detector_belief']
    assert row['stages']['B']['evaluation_routes']['B']==dict(kind='ACTUAL_STAGE_ROUTE',context_id=0)
    assert len(row['context_bank']['banks'])==1
    for arm in core.LEARNERS:
        assert len(fits[arm])==1
        b_evaluations = [call for call in engine.calls if call['arm']==arm and call['task']=='B']
        assert all(call['weights'] is fits[arm][0]['weights'] for call in b_evaluations)
        assert row['stages']['B']['arms'][arm]['fit']['method']=='NONE'


def test_first_beliefs_stay_fixed_and_source_unchanged_banks_repeat_exact_evaluations(monkeypatch):
    values = fixture(monkeypatch); row = run_fixture(values)
    _,engine,_,_,_ = values
    assert row['evaluation_beliefs']['A']['estimated_p_four']==1/258
    assert row['evaluation_beliefs']['B']['estimated_p_four']==.5
    for call in engine.calls:
        assert call['p']==row['evaluation_beliefs'][call['task']]['estimated_p_four']
    for arm in core.ARMS:
        a = row['stages']['A1']['arms'][arm]['evaluations']['A']
        assert row['stages']['B']['arms'][arm]['evaluations']['A']==a
        assert row['stages']['A2']['arms'][arm]['evaluations']['A']==a
        assert row['stages']['A2']['arms'][arm]['evaluations']['B']==row['stages']['B']['arms'][arm]['evaluations']['B']


def test_economics_charge_detection_actual_new_cohorts_and_tails_with_two_local_heads(monkeypatch):
    row = run_fixture(fixture(monkeypatch))
    inherited = dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)
    parent = dict(trace_bytes=11,cpu_seconds=1.,compiler_cpu_seconds=.2)
    cost = core.build_accounting(inherited,[row],[parent],.1,1.)
    assert cost['physical_detection_stages']==3 and cost['physical_acquisitions']==2
    assert cost['new_warmup_raw_tiles']==3*256 and cost['new_actor_raw_tiles']==2*20
    assert cost['new_training_environment_observations']==808
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,913)
    assert cost['excluded_tail_raw_tiles']==6 and cost['old_target_training_raw_reused']==0
    assert cost['processed_training_samples']==dict(SOURCE=0,CONTEXT_MC=8,CONTEXT_LOCAL=8)
    assert cost['new_evaluation_games']==480 and cost['total_contexts_created']==2
    assert cost['private_head_weight_bytes_created']['CONTEXT_LOCAL']==2*cost['private_head_weight_bytes_created']['CONTEXT_MC']
    assert cost['new_sequence_compute_closed']


def test_configuration_freezes_fresh_target_sequences_observed_reuse_and_matched_mc_structure():
    settings = core.configuration(BUILD/'sources.json')
    assert settings['seed_evaluation']==308900000000
    assert settings['old_target_training_raw_reused']==0 and settings['new_evaluation_games']==30720
    assert settings['source_inputs']=='ORIGINAL_SOURCE_PROVENANCE_AND_COSTS_ONLY_NO_OLD_TARGET_FACTS'
    assert settings['adaptation']=='ONE_FIT_ONLY_ON_FIRST_OBSERVED_CONTEXT_CREATION_REUSE_WITHOUT_REFIT'
    assert settings['context_baseline']=='MC_USES_IDENTICAL_ROUTING_BANKS_AND_FACTUAL_FIT_SAMPLES'
    assert settings['context_statistics']=='CURRENT_STAGE_WARMUP_RAW_SPAWNS_ONLY_COMMITTED_ONCE_BEFORE_TRAINING'
    assert settings['primary']=='CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB'
    assert settings['log_bayes_factor_threshold']==0. and settings['interval_scope']==core.INTERVAL_SCOPE
    assert core.evaluation_seed(5,'B',31)==308905100031
