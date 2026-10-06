"""Finite search arithmetic, shared physical work and selection separation."""
from collections import Counter
from copy import deepcopy
from statistics import mean

import pytest

from acfqp.science import direct_strategy_v297 as core


def test_source_incumbent_and_paired_unique_proposals():
    seed=297000030001
    left,draws=core.propose(core.ZERO,[0.]*4,[.25]*4,seed)
    right,_=core.propose(core.ZERO,[0.]*4,[.25]*4,seed)
    assert left==right and len(set(left))==8 and left[0]==core.ZERO and draws==7
    incumbent=(.1,.2,.3,.4)
    shifted,n=core.propose(incumbent,[.1]*4,[.1]*4,seed)
    assert shifted[:2]==[core.ZERO,incumbent] and n==6
    assert all(-1<=v<=1 for theta in shifted for v in theta)


def test_literal_elite_mean_population_spread_and_random_control():
    candidates=[core.ZERO,(.4,.4,.4,.4),(-.8,)*4,(.8,)*4]
    fitness=[-3.,-1.,-4.,-2.]
    cem=core.decide('CEM',candidates,fitness,[0.]*4,[.25]*4)
    assert cem['winner_index']==1 and cem['elite_indices']==[1,3]
    assert cem['mean_after']==pytest.approx([.3]*4)
    assert cem['sigma_after']==pytest.approx([.225]*4)
    control=core.decide('RANDOM_SEARCH',candidates,fitness,[.9]*4,[.4]*4)
    assert control['winner_theta']==list(candidates[1])
    assert control['mean_after']==[0.]*4 and control['sigma_after']==[.25]*4
    tied=core.decide('CEM',candidates,[-1.]*4,[0.]*4,[.025]*4)
    assert tied['winner_theta']==list(core.ZERO)


class CompleteGameEngine:
    def __init__(self):self.calls=[]
    def evaluate(self,theta,p,environment,seeds,max_steps):
        assert p==.105 and environment==.1 and max_steps==8192
        self.calls.append((tuple(theta),tuple(seeds)))
        games=[dict(seed=s,score=0,steps=3,status='LOST',utility=sum(theta)-4.,final_board=[1,2]*8,
                    strategy_counts={}) for s in seeds]
        return dict(game_summaries=games,counts=dict(environment={'raw_tile_productions':5*len(seeds)},
            planning={},strategy={}),seconds=.2,cpu_seconds=.1)


def test_complete_training_reuses_equal_programs_and_selects_only_training_returns(monkeypatch):
    monkeypatch.setattr(core,'training_seed',lambda l,r,i:297000031000+r*10+i)
    monkeypatch.setattr(core,'proposal_seed',lambda l,r:297000032000+r)
    engine=CompleteGameEngine();events=[]
    states,rounds,refs,costs=core._train(engine,0,.105,events.append)
    assert len(rounds)==4 and len(engine.calls)==len(refs)==len(set(engine.calls))
    assert len(refs)<=53 and len(refs)>=8
    assert len(rounds[0]['arms']['CEM']['reference_ids'])==8
    assert rounds[0]['arms']['CEM']['reference_ids']==rounds[0]['arms']['RANDOM_SEARCH']['reference_ids']
    for method in core.METHODS:
        assert costs[method]['game_references']==128 and costs[method]['cutoff_games']==0
        assert costs[method]['counts']['environment']['raw_tile_productions']==128*5
        assert states[method]['incumbent']==tuple(rounds[-1]['arms'][method]['winner_theta'])
        for row in rounds:
            detail=row['arms'][method]
            assert detail['fitnesses']==[mean(g['utility'] for g in refs[i]['game_summaries'])
                                       for i in detail['reference_ids']]
    assert sum(e['kind']=='TRAIN_EVALUATION' for e in events)==len(refs)
    assert sum(e['kind']=='SEARCH_ROUND' for e in events)==4


def test_learning_probability_is_source_fitted_fraction_not_environment_law():
    source={'rule':{'spawn_distribution':[[1,8075,9026],[2,951,9026]]}}
    assert core.learned_probability(source)==951/9026 and core.learned_probability(source)!=.1


def test_accounting_separates_physical_and_logical_games_and_shared_source_cost():
    ref=dict(game_summaries=[{'status':'LOST'}]*4,counts=dict(environment={'raw_tile_productions':20},
        planning={},strategy={}),cpu_seconds=.1)
    life=dict(training_references={'T0':ref},science_references={'S0':ref},
        training_costs_per_arm={m:dict(counts=deepcopy(ref['counts'])) for m in core.METHODS})
    parent=dict(source_setup={'cpu_seconds':.2},native_setup_seconds=.3,worker_cpu_seconds=.4,
                compiler_cpu_seconds=.5,trace_bytes=50)
    costs=core.build_accounting([life],[parent],{'source_training_raw_tiles':100,'dynamics_raw_tiles':10},.6,.7)
    assert costs['physical_training_games']==4 and costs['physical_science_games']==4
    assert costs['economic_training_raw_tiles_per_arm']=={'SOURCE':110,'CEM':130,'RANDOM_SEARCH':130}
    assert costs['physical_training_counts']['environment']['raw_tile_productions']==20
    assert costs['source_setup_cpu_seconds']==.2 and costs['new_source_value_updates']==0


def test_parent_executes_frozen_final_programs_and_saves_only_physical_science(tmp_path,monkeypatch):
    import gzip
    import json
    from types import SimpleNamespace
    import numpy as np
    from acfqp.science import native_strategy_v297 as native
    monkeypatch.setattr(core,'training_seed',lambda l,r,i:297000033000+l*100+r*10+i)
    monkeypatch.setattr(core,'proposal_seed',lambda l,r:297000034000+l*10+r)
    monkeypatch.setattr(core,'science_seed',lambda l,i:297000035000+l*100+i)
    leaf=SimpleNamespace(weights=np.zeros(1),updates=0);leaf.weights.flags.writeable=False
    monkeypatch.setattr(core,'load_leaf',lambda s,r:(leaf,{'cpu_seconds':.1,'setup_counts':{}}))
    class Engine(CompleteGameEngine):
        def __init__(self,leaf,runtime):
            super().__init__();self.setup_counts={};self.setup_seconds=0.
    monkeypatch.setattr(native,'NativeStrategy',Engine)
    source={'parent':0,'rule':{'spawn_distribution':[[1,895,1000],[2,105,1000]]}}
    parent=core._run_parent(source,tmp_path)
    assert parent['source_weights_readonly'] and parent['source_updates_after']==0
    assert [l['lifecycle'] for l in parent['lifecycles']]==[0,4,8,12]
    with gzip.open(parent['trace_file'],'rt') as f:events=[json.loads(line) for line in f]
    assert sum(e['kind']=='SEARCH_ROUND' for e in events)==16
    assert sum(e['kind']=='SCIENCE_EVALUATION' for e in events)==sum(
        len(l['science_references']) for l in parent['lifecycles'])
    for life in parent['lifecycles']:
        for arm in core.METHODS:
            assert life['arms'][arm]['theta']==life['search_rounds'][-1]['arms'][arm]['winner_theta']
            assert len(life['arms'][arm]['game_summaries'])==32
