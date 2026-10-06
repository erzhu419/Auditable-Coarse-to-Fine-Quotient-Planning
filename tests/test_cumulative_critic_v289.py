"""Panel weighting, fixed-continuation readout and actual driver reproduction."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import cumulative_critic_v289 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ACTIONS
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_retained_critic_v287 import fit_retained, score_retained

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/cumulative_critic_v289/driver_tests'
QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)


def test_anchor_errors_weight_games_equally_instead_of_sample_counts():
    rows=[dict(episode=e,target=0.) for e in (1,2,2,2)]
    result=core.anchor_metrics(rows,[2.,4.,4.,4.])
    assert result['metrics']==dict(bias=3.,mse=10.,mae=3.)
    assert [g['count'] for g in result['game_metrics']]==[1,3]


def test_readout_utility_uses_independent_reference_instead_of_fitted_scores():
    board=dict(state_id='fixed',board=[0]*16,reference_q={'LEFT':2.,'RIGHT':1.})
    frozen=dict(rows=[dict(state_id='fixed',action='LEFT',action_values={'LEFT':0.,'RIGHT':-1.})])
    current=dict(rows=[dict(state_id='fixed',action='RIGHT',action_values={'LEFT':5.,'RIGHT':8.})])
    result=core.h2_metrics([board],frozen,current)
    assert result['metrics']==dict(action_disagreement=1.,validation_utility_delta=-1.,
        frozen_reference_regret=0.,mc_reference_regret=1.,predicted_frozen_action_margin=-3.)
    assert core.h2_prefixes(7)==[0,2,4,6,7]


def test_fit_reproduction_rejects_changed_update_history():
    receipt=dict(learning_counts={'td_updates':2},first_update={'error':1.},
        last_update={'error':2.},target_counts={'suffix_games':1,'target_buffer_doubles_peak':2})
    actual=dict(receipt,target_counts={'suffix_games':1,'target_buffer_doubles_peak':3})
    core.compare_original_fit(actual,receipt)
    with pytest.raises(ValueError,match='learning_counts'):
        core.compare_original_fit(dict(actual,learning_counts={'td_updates':3}),receipt)


def test_driver_keeps_prefix_belief_and_reproduces_both_full_heldout_heads(monkeypatch):
    from acfqp.science import cumulative_critic_analysis_v289 as analysis
    # Actual small-radix native fits/planning; no formal random environment run.
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',3)
    native=NtupleValue(rule,BUILD/'runtime')
    template=QueryTD(QueryParent(native,QUERY,QUERY,.5),'PRIOR',BUILD/'runtime')
    template.freeze()
    memory=SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    board=[1,1,0,0]+[0]*12
    data=dict(afterstates=np.tile(np.asarray(board,dtype=np.int32),(7,1)),
        rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory=memory.to_payload(),costs={},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT') for i in range(3)])
    fitted=QueryTD(template.parent,'PRIOR',BUILD/'runtime')
    fit=fit_retained(fitted,data,'MC',BUILD/'runtime')
    old=dict(dataset=core.compact_dataset(data),evaluation_snapshot={'estimated_p_four':1/258},
        arms={'FROZEN':{'heldout':score_retained(template,data,BUILD/'runtime')},
              'EPISODIC_MC':{'fit':fit,'heldout':score_retained(fitted,data,BUILD/'runtime'),
                            'new_value_updates':fitted.updates}})
    reference={action:float(index) for index,action in enumerate(ACTIONS)
        if ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(action))[2]}
    panel={0:[dict(state_id=f'fixed{i}',board=board,reference_q=reference) for i in range(4)]}
    monkeypatch.setattr(core,'load_retained_parent',lambda *args:{0:data})
    monkeypatch.setattr(core,'load_leaf',lambda *args:(template,{}))
    monkeypatch.setattr(analysis,'select_anchor_indices',lambda *args,**kwargs:np.asarray([4,5,6]))
    # Each test writes its own compact trace; no existing formal receipt is overwritten.
    out=BUILD/'integration'
    out.mkdir(parents=True,exist_ok=True)
    trace=out/'parent_0_predictions.jsonl.gz'
    trace.unlink(missing_ok=True)
    result=core._run_parent({'parent':0},{'lifecycle_ids':[0],'trace_file':'fixture'},
        {},{0:old},panel,out)
    life=result['lifecycles'][0]
    assert [row['completed_fit_games'] for row in life['snapshots']]==[0,1,2]
    assert all(row['model_p_four']==1/258 for row in life['h2_probes'])
    assert life['snapshots'][-1]['cumulative_updates']==4
    assert life['full_heldout']['EPISODIC_MC']['game_metrics']==old['arms']['EPISODIC_MC']['heldout']['game_metrics']
    assert all(life['reproduction'].values()) and not template.weights.flags.writeable
    np.testing.assert_array_equal(template.weights,native.weights)
