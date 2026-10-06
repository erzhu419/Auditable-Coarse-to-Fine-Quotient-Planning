"""Driver boundaries and economic acquisition for the fixed-history study."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import retained_critic_v287 as core
from acfqp.science import retained_actor_data_v287 as data_core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/retained_critic_v287/runtime/driver_tests'


def test_new_evaluation_seed_family_is_disjoint_and_paired():
    seeds = {core.evaluation_seed(life, episode) for life in range(16) for episode in range(16)}
    old_eval = {286500000000+life*1000000+phase*100000+episode
        for life in range(16) for phase in range(3) for episode in range(16)}
    old_train = {286200000000+life*10000000 for life in range(16)}
    old_warm = {286100000000+life*1000000 for life in range(16)}
    assert len(seeds) == 256 and not seeds & (old_eval | old_train | old_warm)


def test_acquisition_costs_include_source_initial_holdout_and_censored_tail():
    inherited = dict(source_training_raw_tiles=100, source_training_games=2,
        source_training_environment_counts={'sampled_transitions':96,'initial_spawns':4},
        source_training_seconds=1., dynamics_raw_tiles=10, dynamics_costs={},
        warmup_raw_tiles=8, warmup_environment_counts={}, warmup_direct_counts={}, warmup_memory_counts={})
    old_life = dict(lifecycle=0, arms={'FROZEN':{'phases':{'A':{'training':{'counts':{
        'environment':{'raw_tile_productions':20,'sampled_transitions':16,'initial_spawns':4},
        'planning':{'choose_calls':16},'learning':{}}}}}}})
    arms = {a:dict(new_value_updates=0 if a=='FROZEN' else 6,
        fit={'learning_counts':{},'target_counts':{}},heldout={'prediction_counts':{},'target_counts':{}},
        evaluation_counts={'environment':{'raw_tile_productions':12},'planning':{}},
        head_setup={'private_weight_bytes':0 if a=='FROZEN' else 32}) for a in core.ARMS}
    life = dict(lifecycle=0, dataset={'costs':{'retained_raw':20,'excluded_tail_raw':4}},arms=arms)
    original = dict(by_lifecycle=[old_life],accounting={'inherited_costs_per_arm':{'FROZEN':inherited}})
    costs = core.build_accounting(original,[life],[{'cpu_seconds':3.,'compiler_cpu_seconds':.5}],.1,4.)
    assert costs['economic_training_raw_tiles_per_arm'] == {a:138 for a in core.ARMS}
    assert costs['new_training_environment_observations'] == 0
    assert costs['retained_physical_A_raw_tiles'] == 20
    assert costs['evaluation_counts']['environment']['raw_tile_productions'] == 36
    assert costs['new_value_updates'] == dict(FROZEN=0,SHADOW_TD=6,EPISODIC_MC=6)


def test_driver_connects_factual_fit_and_fixed_prefix_belief_to_static_evaluation(monkeypatch):
    # A small-radix native controller tests actual API plumbing; this is not a formal V287 draw.
    rule = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',3)
    source = NtupleValue(rule,BUILD)
    template = QueryTD(QueryParent(source,core.QUERY,core.QUERY,.5),'PRIOR',BUILD)
    template.freeze()
    memory = SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    board = np.asarray(([1,2]*8),dtype=np.int32)
    board[-1] = 0
    dataset = dict(afterstates=np.tile(board,(5,1)),rewards=np.zeros(5),
        ends=np.arange(1,6,dtype=np.int64),terminal_codes=np.full(5,-1,dtype=np.int32),
        fit_game_count=4,fit_step_end=4,fit_memory=memory.to_payload(),costs={},
        games=[dict(episode=i,split='fit' if i<4 else 'heldout') for i in range(5)])
    monkeypatch.setattr(data_core,'load_retained_parent',lambda *args:{0:dataset})
    monkeypatch.setattr(core,'load_leaf',lambda *args:(template,{'checkpoint_loads':1}))
    weights_before = template.weights.copy()
    result = core._run_parent({'parent':0},{'lifecycle_ids':[0],'trace_file':'unused'},
        {},ROOT/'reports/retained_critic_v287/driver_integration')
    row = result['lifecycles'][0]
    assert row['evaluation_snapshot']['estimated_p_four'] == 1/258
    assert row['dataset']['fit_memory'] == dataset['fit_memory']
    assert not set(('afterstates','rewards','ends','terminal_codes')) & row['dataset'].keys()
    assert row['arms']['FROZEN']['new_value_updates'] == 0
    assert row['arms']['SHADOW_TD']['new_value_updates'] == row['arms']['EPISODIC_MC']['new_value_updates'] == 4
    assert all(len(a['game_summaries'])==16 and len(a['heldout']['game_metrics'])==1 for a in row['arms'].values())
    assert all(a['heldout']['prediction_counts'].get('td_updates',0)==0 for a in row['arms'].values())
    assert memory.to_payload()==dataset['fit_memory']
    np.testing.assert_array_equal(template.weights,weights_before)
