"""Finite law separation fixtures, independent of the V294 science streams."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.native_continuation_v285 import NativeContinuation
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/conditional_bellman_v294/runtime/native_continuation_tests'
QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)
BOARD=[1,0,0,0,0,1]+[0]*10
SEEDS=[29400003001,29400003002]


@pytest.fixture(scope='module')
def leaf():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    model=QueryTD(QueryParent(source,QUERY,QUERY,.5),'PRIOR',BUILD)
    model.freeze()
    return model


def reference(leaf,first_action,model_p,environment_p,draws):
    planner=FrozenLeafPlanner(leaf,depth=2,build_dir=BUILD)
    planner.spawn_probabilities=1.-model_p,model_p
    board,score,first,status=tuple(BOARD),0,0,'ACTIVE'
    counts=Counter()
    for step,(cell_draw,rank_draw) in enumerate(draws):
        action=first_action if step==0 else planner.choose(board)['action']
        after,gained,changed=ground.swipe_board_v1(board,ground.Swipe2048Action(action))
        assert changed
        empty=[cell for cell,rank in enumerate(after) if not rank]
        board=list(after)
        board[empty[int(cell_draw*len(empty))]]=1 if rank_draw<1.-environment_p else 2
        board=tuple(board)
        score+=gained
        if step==0:first=gained
        counts.update(sampled_transitions=1,environment_random_draws=2,
            ground_explicit_swipe_calls=1,ground_swipe_calls=1,ground_state_status_calls=1)
        if max(board)>=leaf.radix:status='WON'
        else:
            counts.update(ground_status_internal_swipe_calls=4,ground_swipe_calls=4)
            if not ground.legal_actions_v1(board):status='LOST'
        if status!='ACTIVE':break
    if status=='ACTIVE':status='CUTOFF'
    bonus=4. if status=='WON' else -4. if status=='LOST' else 0.
    row=dict(first_score=first,total_score=score,steps=step+1,
        suffix_utility=(score-first)/2048.+bonus,total_utility=score/2048.+bonus,
        status=status,final_board=list(board))
    planning={key:value for key,value in planner.counts.items() if key!='choose_calls' and value}
    return row,counts,planning


@pytest.mark.parametrize('model_p,environment_p',[(0.,1.),(1.,0.)])
def test_model_probability_and_environment_law_use_separate_paths(leaf,model_p,environment_p):
    engine=NativeContinuation(leaf,BUILD)
    actions=['DOWN','LEFT','RIGHT','UP']
    before=leaf.weights.copy()
    actual=engine.evaluate(BOARD,actions,model_p,SEEDS,16,environment_p_four=environment_p)
    environment,planning=Counter(),Counter()
    leaked_policy_differences=0
    for index,row in enumerate(actual['rollouts']):
        action,replica=divmod(index,len(SEEDS))
        draws=engine.common_draws(SEEDS[replica],16)
        expected,world,compute=reference(leaf,actions[action],model_p,environment_p,
            draws)
        leaked,_,_=reference(leaf,actions[action],environment_p,environment_p,draws)
        leaked_policy_differences+=expected!=leaked
        assert row==dict(expected,action=actions[action],replica_index=replica,seed=SEEDS[replica])
        environment.update(world);planning.update(compute)
    assert actual['counts']['environment']==dict(environment)
    assert actual['counts']['planning']==dict(planning)
    assert leaked_policy_differences>0
    np.testing.assert_array_equal(leaf.weights,before)
    assert not leaf.weights.flags.writeable and leaf.updates==0


def test_omitted_environment_law_retains_existing_equal_law_call(leaf):
    engine=NativeContinuation(leaf,BUILD)
    default=engine.evaluate(BOARD,['LEFT','RIGHT'],.37,SEEDS,8)
    explicit=engine.evaluate(BOARD,['LEFT','RIGHT'],.37,SEEDS,8,environment_p_four=.37)
    assert default['rollouts']==explicit['rollouts']
    assert default['counts']==explicit['counts']
