"""Actual five-arm native integration, target labels and shared evaluation cost."""
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import conditional_bellman_v294 as driver
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_value_stream_v286 import NativeValueStream
from acfqp.science.online_episode_stream_v292 import _GameBuffer


def test_factual_labels_exclude_current_reward_and_include_terminal_once():
    game={'rewards':np.asarray([2.,3.,5.]),'terminal_code':1}
    assert driver.factual_suffix(game).tolist()==[12.,9.,4.]
    game['terminal_code']=-1
    assert driver.factual_suffix(game).tolist()==[4.,1.,-4.]


def test_formal_science_and_ranking_streams_are_disjoint_from_fixtures_and_v293():
    science={driver.evaluation_seed(l,p,g) for l in range(16) for p in range(3) for g in range(32)}
    ranking={driver.ranking_seed(l,p,a,r) for l in range(16) for p in range(3) for a in range(3) for r in range(32)}
    assert len(science)==1536 and len(ranking)==4608 and not science&ranking
    assert min(science)==294900010000 and min(ranking)==294600010000
    assert not (science|ranking)&set(range(29400003000,29400004000))
    old={293900010000+l*1000000+p*100000+g for l in range(16) for p in range(3) for g in range(32)}
    assert not (science|ranking)&old
    config=driver.configuration('fixture',{})
    assert config['new_training_raw_tiles']==0 and config['scientific_games']==14848
    assert config['logical_scientific_game_references']==17920


def test_actual_native_five_arm_three_phase_pipeline_and_immutable_conditional_A(monkeypatch):
    runtime=Path(__file__).resolve().parents[1]/'reports/conditional_bellman_v294/runtime/driver_fixture'
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    native=NtupleValue(rule,runtime);native.weights.flags.writeable=False
    template=QueryTD(QueryParent(native,driver.QUERY,driver.QUERY,.5),'PRIOR',runtime);template.freeze()
    carrier=NativeValueStream(template,29400003101,runtime)
    buffer=_GameBuffer(carrier.state(),4,True)
    data={'phases':{},'carrier_snapshots':{},'costs':{}}
    try:
        for index,(phase,env_p) in enumerate(driver.PHASES):
            games,anchors=[],[]
            for game_index in range(2):
                chunks=[];terminal=None
                while terminal is None:
                    state=carrier.state()
                    receipt=carrier.advance(template,0,template if state['pending_bank_id'] is not None else None,
                        .1 if index!=1 else .5,env_p,64,stop_on_game_end=True)
                    chunks.append(receipt);terminal=buffer.ingest(receipt)
                completion,arrays=terminal
                game=dict(afterstates=arrays['afterstates'],rewards=arrays['rewards'],
                    model_p_four=np.full(completion['steps'],.1 if index!=1 else .5),
                    terminal_code=1 if completion['status']=='WON' else -1,metadata=dict(completion,phase=phase))
                games.append(game)
                if game_index==1:
                    board=[0]*16
                    for spawn in chunks[0]['raw_spawns'][:2]:board[spawn['cell']]=spawn['rank']
                    anchors=[dict(lifecycle=0,parent=0,phase=phase,anchor_index=0,episode=completion['episode'],
                        step=0,anchor_id='fixture-'+phase,board_before_action=board,model_p_four=game['model_p_four'][0])]
            data['phases'][phase]=dict(fit_games=games[:1],heldout_games=games[1:],anchors=anchors)
            data['carrier_snapshots'][phase]={'estimated_p_four':.1 if index!=1 else .5}
    finally:carrier.close()
    monkeypatch.setattr(driver,'EVALUATION_GAMES',2);monkeypatch.setattr(driver,'RANK_REPLICAS',2)
    monkeypatch.setattr(driver,'evaluation_seed',lambda l,p,g:29400003200+p*10+g)
    monkeypatch.setattr(driver,'ranking_seed',lambda l,p,a,r:29400003300+p*10+r)
    engine=NativeValueStream(template,0,runtime);rows=[]
    try:result=driver._run_lifecycle(template,data,0,0,runtime,engine,rows.append)
    finally:engine.close()
    assert template.updates==0 and not template.weights.flags.writeable
    assert sum(row['kind']=='RANKING_ANCHOR' for row in rows)==3
    assert sum(row['kind']=='FIT_GAME' for row in rows)==12
    assert len(result['retained_A_setups'])==4 and len(result['materializations'])==24
    for arm,value in result['arms'].items():
        b=value['phases']['B'];a=value['phases']['A']
        assert b['a_head_on_B']['model_p_four']==.5
        assert b['retention_probe']['model_p_four']==.1
        assert a['retention_probe']['shared_with_current']
        assert b['a_head_on_B']['shared_with_current']==(arm=='FROZEN')
        assert len(value['phases']['A_prime']['game_summaries'])==2
        if arm!='FROZEN':
            snapshot=next(s for s in result['materializations'] if s['purpose']==arm+'_B_A_PARAMETERS')
            assert snapshot['origin_residual_updates']==a['snapshot']['value_updates']>0
    costs=dict(reused_carrier_raw_tiles=30,warmup_raw_tiles=7,carrier_acquisition_counts={
        'environment':{'raw_tile_productions':30},'planning':{},'learning':{}},
        warmup_environment_counts={},warmup_direct_counts={},warmup_memory_counts={},processing_counts={},
        processing_cpu_seconds=.1,excluded_games=[],excluded_tail={'raw_tiles':3})
    result['dataset']['costs']=costs
    old={'accounting':dict(inherited_costs_per_arm={'FROZEN_H2':dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)},
        physical_validation_raw_tiles={},physical_deployment_raw_tiles={},evaluation_counts={})}
    parent=dict(cpu_seconds=1.,compiler_cpu_seconds=.1,trace_bytes=1,native_evaluation_setup={'counts':{},'seconds':0.})
    accounting=driver.build_accounting(old,[result],[parent],.1,1.)
    assert accounting['new_training_environment_raw_tiles']==0
    assert accounting['economic_training_raw_tiles_per_arm']==dict.fromkeys(driver.ARMS,142)
    assert accounting['physical_evaluation_games']==58 and accounting['logical_evaluation_game_references']==70
    samples=accounting['processed_training_samples_per_arm']
    assert samples['FROZEN']==0 and len(set(samples[a] for a in driver.ARMS[1:]))==1
