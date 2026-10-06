"""Actual native three-arm lifecycle and causal expert-copy integration."""
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import routed_bellman_v295 as driver
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics,RewriteProgram
from acfqp.science.native_value_stream_v286 import NativeValueStream
from acfqp.science.online_episode_stream_v292 import _GameBuffer


def test_frozen_science_reference_counts_and_new_seed_family():
    settings=driver.configuration('reports/shadow_deployment_v293/summary.json',{})
    seeds={driver.evaluation_seed(l,p,g) for l in range(16) for p in range(3) for g in range(32)}
    assert len(seeds)==1536 and min(seeds)==295900010000
    assert settings['scientific_games']==8704 and settings['logical_scientific_game_references']==10752
    assert settings['new_training_raw_tiles']==settings['new_ranking_rollouts']==0
    assert settings['denominator']=='WHOLE_GAME_ORIGINAL_ADDRESS_OCCURRENCES_ACROSS_ALL_MODULES'


def test_native_lifecycle_birth_before_game_commit_and_same_B_no_update_route(monkeypatch):
    runtime=Path(__file__).resolve().parents[1]/'reports/routed_bellman_v295/runtime/driver_fixture'
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    native=NtupleValue(rule,runtime);native.weights.flags.writeable=False
    template=QueryTD(QueryParent(native,driver.QUERY,driver.QUERY,.5),'PRIOR',runtime);template.freeze()
    carrier=NativeValueStream(template,29500003101,runtime);buffer=_GameBuffer(carrier.state(),4,True)
    data=dict(phases={},carrier_snapshots={},routing_timeline={},warmup_module_ids=[0],
        warmup_modules=[dict(id=0,alpha=10,beta=90)],initial_active_module_id=0,costs={})
    try:
        for index,(phase,p) in enumerate(driver.PHASES):
            games=[];timeline=[]
            for i in range(3):
                terminal=None
                while terminal is None:
                    state=carrier.state()
                    receipt=carrier.advance(template,0,template if state['pending_bank_id'] is not None else None,
                        p,p,64,stop_on_game_end=True)
                    terminal=buffer.ingest(receipt)
                completion,arrays=terminal
                module=0 if index!=1 or i==0 else 1
                game=dict(afterstates=arrays['afterstates'],rewards=arrays['rewards'],
                    model_p_four=np.full(completion['steps'],p),module_ids=np.full(completion['steps'],module),
                    terminal_code=1 if completion['status']=='WON' else -1,metadata=dict(completion,phase=phase))
                games.append(game)
                if phase=='B' and i==0:
                    timeline.append(dict(kind='created',raw_index=completion['end_raw']-1,
                        previous_module_id=0,module_id=1))
                if phase=='A_prime' and i==0:
                    timeline.append(dict(kind='reactivated',raw_index=completion['start_raw']+1,
                        previous_module_id=1,module_id=0))
                timeline.append(dict(kind='GAME_COMPLETE',raw_index=completion['end_raw'],metadata=game['metadata'],
                    fit=i<2,pure_phase=phase,exclusion_reason=None))
            data['phases'][phase]=dict(fit_games=games[:2],heldout_games=games[2:],anchors=[])
            data['routing_timeline'][phase]=timeline
            data['carrier_snapshots'][phase]=dict(estimated_p_four=p,
                memory=dict(active_module_id=1 if phase=='B' else 0))
    finally:carrier.close()
    monkeypatch.setattr(driver,'EVALUATION_GAMES',2)
    monkeypatch.setattr(driver,'evaluation_seed',lambda l,p,g:29500003200+p*10+g)
    engine=NativeValueStream(template,0,runtime);rows=[]
    try:result=driver._run_lifecycle(template,data,0,0,runtime,engine,rows.append)
    finally:engine.close()
    assert template.updates==0 and not template.weights.flags.writeable
    assert len(result['expert_births'])==len(result['no_update_births'])==1
    a=result['arms']['ROUTED_BELLMAN']['phases']['A']['snapshot']
    birth=result['expert_births'][0]['receipt'];reference_birth=result['no_update_births'][0]['receipt']
    assert birth['origin_value_updates']==reference_birth['origin_value_updates']==a['expert_value_updates']['0']>0
    first_b=next(r for r in rows if r['kind']=='FIT_GAME' and r['phase']=='B' and r['arm']=='ROUTED_BELLMAN')
    assert first_b['fit']['by_module']['1']['trained_afterstates']==0
    assert first_b['fit']['by_module']['1']['old_value_updates']==a['expert_value_updates']['0']
    second_b=[r for r in rows if r['kind']=='FIT_GAME' and r['phase']=='B' and r['arm']=='ROUTED_BELLMAN'][1]
    assert second_b['fit']['by_module']['1']['old_value_updates']==a['expert_value_updates']['0']
    assert second_b['fit']['by_module']['0']['trained_afterstates']==0
    b=result['arms']['ROUTED_BELLMAN']['phases']['B']
    assert b['a_head_on_B']['model_p_four']==.5 and b['a_head_on_B']['selected_value_module_id']==1
    assert b['retention_probe']['model_p_four']==.1 and b['retention_probe']['selected_value_module_id']==0
    assert result['arms']['ROUTED_BELLMAN']['phases']['A_prime']['snapshot']['selected_value_module_id']==0
    assert len(result['materializations'])==12 and len(result['retained_A_copies'])==2
    data_costs=dict(reused_carrier_raw_tiles=30,warmup_raw_tiles=7,
        carrier_acquisition_counts=dict(environment={},planning={},learning={}),warmup_environment_counts={},
        warmup_direct_counts={},warmup_memory_counts={},processing_counts={},processing_memory_counts={},
        processing_cpu_seconds=.1,routing_event_inventory=dict(created=1,reactivated=1),
        excluded_games=[],excluded_tail=dict(raw_tiles=3))
    result['dataset']['costs']=data_costs
    old=dict(accounting=dict(inherited_costs_per_arm=dict(FROZEN_H2=dict(source_training_raw_tiles=100,dynamics_raw_tiles=5))))
    parent=dict(cpu_seconds=1.,compiler_cpu_seconds=.1,trace_bytes=1,native_evaluation_setup=dict(counts={},seconds=0.))
    costs=driver.build_accounting(old,[result],[parent],.1,1.)
    assert costs['physical_evaluation_games']==34 and costs['logical_evaluation_game_references']==42
    assert costs['new_training_environment_raw_tiles']==costs['new_ranking_rollouts']==0
    assert costs['economic_training_raw_tiles_per_arm']==dict.fromkeys(driver.ARMS,142)
    assert costs['actual_experts_created']==costs['no_update_experts_created']==1
    own=costs['processed_training_samples_per_arm']
    assert own['FROZEN']==0 and own['ROUTED_BELLMAN']==own['SMOOTH_BELLMAN']
