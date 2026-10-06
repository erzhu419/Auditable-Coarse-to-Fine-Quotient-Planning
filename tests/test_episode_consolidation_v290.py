"""Fresh paired evaluation, real four-head plumbing and acquisition ledger."""
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import episode_consolidation_v290 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_retained_critic_v287 import fit_retained, score_retained

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/episode_consolidation_v290/driver_tests'


def test_fresh_seed_family_is_paired_and_disjoint_from_previous_games():
    seeds={core.evaluation_seed(life,episode) for life in range(16) for episode in range(16)}
    previous={287500000000+life*1000000+episode for life in range(16) for episode in range(16)}
    assert len(seeds)==256 and not seeds&previous
    assert len(core.ARMS)==4 and core.EVALUATION_GAMES==16


def test_costs_keep_equal_acquisition_and_separate_actual_writes_from_samples():
    def arm(samples,writes,peak):
        return dict(processed_training_samples=samples,fit={'learning_counts':{
            'td_updates':samples,'table_updates':writes},'target_counts':{'suffix_games':2,
            'target_buffer_doubles_peak':peak},'consolidation_counts':{'parameter_write_events':writes,
            'native_bytes_peak':peak*8}},heldout={'prediction_counts':{'value_predictions':3},
            'target_counts':{'suffix_games':1,'target_buffer_doubles_peak':3}},
            evaluation_counts={'environment':{'raw_tile_productions':10},'planning':{}},
            head_setup={'private_weight_bytes':0 if samples==0 else 32})
    old={'accounting':{'inherited_costs_per_arm':{'FROZEN':{'source_training_raw_tiles':100,
        'retained_actor_A_raw_tiles':20}},'economic_training_raw_tiles_per_arm':{'FROZEN':120},
        'retained_physical_A_raw_tiles':20,'retained_physical_A_counts':{}}}
    lives=[dict(lifecycle=i,dataset={'costs':{}},arms={a:arm(0 if a=='FROZEN' else 6,
        0 if a=='FROZEN' else 2 if a=='EPISODE_MEAN_MC' else 5,4+i) for a in core.ARMS}) for i in range(2)]
    result=core.build_accounting(old,lives,[{'cpu_seconds':3.,'compiler_cpu_seconds':.5}],.2,4.)
    assert result['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,120)
    assert result['new_training_environment_observations']==0
    assert result['retained_physical_A_raw_tiles']==20
    assert result['processed_training_samples']['EPISODE_MEAN_MC']==12
    assert result['fit_counts']['EPISODE_MEAN_MC']['table_updates']==4
    assert result['consolidation_buffer_peaks']['EPISODE_MEAN_MC']['native_bytes_peak']==40
    assert result['consolidation_counts']['EPISODE_MEAN_MC']['parameter_write_events']==4
    assert result['evaluation_counts']['environment']['raw_tile_productions']==80


def test_real_driver_shares_fit_prefix_belief_and_preserves_original_critics(monkeypatch):
    # A small native fixture detects target/arm API errors without a formal draw.
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',3)
    native=NtupleValue(rule,BUILD/'runtime')
    template=QueryTD(QueryParent(native,core.QUERY,core.QUERY,.5),'PRIOR',BUILD/'runtime')
    template.freeze()
    memory=SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    board=np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    data=dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),costs={},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT') for i in range(3)])
    old_mc=QueryTD(template.parent,'PRIOR',BUILD/'runtime')
    old_fit=fit_retained(old_mc,data,'MC',BUILD/'runtime')
    old=dict(dataset=core.compact_dataset(data),evaluation_snapshot={'estimated_p_four':1/258},
        arms={'FROZEN':{'heldout':score_retained(template,data,BUILD/'runtime')},
              'EPISODIC_MC':{'fit':old_fit,'heldout':score_retained(old_mc,data,BUILD/'runtime')}})
    monkeypatch.setattr(core,'load_retained_parent',lambda *args:{0:data})
    monkeypatch.setattr(core,'load_leaf',lambda *args:(template,{}))
    result=core._run_parent({'parent':0},{'lifecycle_ids':[0],'trace_file':'fixture'},
        {},{0:old},BUILD/'integration')
    life=result['lifecycles'][0]
    assert life['evaluation_snapshot']['estimated_p_four']==1/258
    assert life['original_frozen_and_mc_heldout_exact'] and life['original_mc_fit_exact']
    assert [life['arms'][a]['processed_training_samples'] for a in core.ARMS]==[0,4,4,4]
    assert all(len(life['arms'][a]['game_summaries'])==16 for a in core.ARMS)
    assert all(life['arms'][a]['sample_counter']==life['arms'][a]['processed_training_samples'] for a in core.ARMS)
    assert not template.weights.flags.writeable
    np.testing.assert_array_equal(template.weights,native.weights)
