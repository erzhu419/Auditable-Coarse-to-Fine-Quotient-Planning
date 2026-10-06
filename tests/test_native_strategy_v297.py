"""Finite source-parity, strategy-state and real-accounting checks."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS,NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics,RewriteProgram
from acfqp.science.native_strategy_v297 import NativeStrategy
from acfqp.science.native_value_stream_v286 import NativeValueStream

BUILD=Path(__file__).resolve().parents[1]/'reports/direct_strategy_v297/runtime/tests'
QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)


def leaf():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(6,7)),(2,Fraction(1,7))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    source.weights[:]=np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    result=QueryTD(QueryParent(source,QUERY,QUERY,.5),'PRIOR',BUILD)
    result.freeze()
    return result


def actual_afterstates(board):
    moved,legal=[],[]
    for action in ACTIONS:
        after,_,changed=ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(action))
        moved.append(after);legal.append(changed)
    return moved,legal


def board_with_empty(n):
    board=[1]*16
    for i in (0,3,12,5)[:n]:board[i]=0
    board[15]=3
    return board


def test_zero_theta_exactly_reproduces_old_source_games_counts_rng_and_winning_spawns():
    source=leaf();before=source.weights.copy()
    engine=NativeStrategy(source,BUILD)
    old=NativeValueStream(source,0,BUILD)
    seeds=[297000030000+i for i in range(3)]
    expected=old.evaluate_games(source,.23,.6,seeds,depth=2,max_steps=128)
    actual=engine.evaluate([0.,0.,0.,0.],.23,.6,seeds,max_steps=128)
    assert [{k:v for k,v in row.items() if k!='strategy_counts'} for row in actual['game_summaries']]==expected['game_summaries']
    assert actual['counts']['environment']==expected['counts']['environment']
    assert actual['counts']['planning']==expected['counts']['planning']
    assert actual['counts']['strategy']['zero_source_games']==3
    assert actual['counts']['strategy'].get('feature_evaluations',0)==0
    assert actual['counts']['strategy'].get('strategy_memory_writes',0)==0
    env=actual['counts']['environment'];steps=sum(g['steps'] for g in actual['game_summaries'])
    assert env['initial_spawns']==6 and env['post_action_spawns']==steps
    assert env['raw_tile_productions']==6+steps and env['environment_random_draws']==2*(6+steps)
    assert any(g['status']=='WON' for g in actual['game_summaries'])
    np.testing.assert_array_equal(source.weights,before)
    assert source.updates==0 and not source.weights.flags.writeable
    old.close()


def test_build_guard_locks_corner_hysteresis_rescue_and_repeat_state():
    engine=NativeStrategy(leaf(),BUILD)
    board=board_with_empty(4);board[15]=1;board[6]=board[9]=3
    moved,legal=actual_afterstates(board)
    first=engine._selection(board,moved,legal,[0.]*4,0,[0.,0.,0.,1.])
    # Max cells 6 and 9 tie; index 6 captures nearest corner 3.
    assert first['state'][0:2]==[3,1] and first['counts']['mode_entries']==1
    assert first['action']==0 and first['state'][2]==0
    sparse=board_with_empty(3);moved,legal=actual_afterstates(sparse)
    held=engine._selection(sparse,moved,legal,[0.,.5,0.,0.],1,[0.,0.,0.,1.],first['state'])
    assert held['state'][0:2]==[3,1] and held['action']==0
    assert held['counts']['action_changes']==1 and held['counts'].get('mode_entries',0)==0
    dense=board_with_empty(2);moved,legal=actual_afterstates(dense)
    exit_=engine._selection(dense,moved,legal,[0.]*4,1,[0.,0.,0.,1.],held['state'])
    assert exit_['action']==1 and exit_['state']==[-1,0,-1]
    assert exit_['counts']['mode_exits']==1 and exit_['counts'].get('feature_evaluations',0)==0
    moved,legal=actual_afterstates(sparse)
    inactive=engine._selection(sparse,moved,legal,[0.]*4,2,[0.,0.,0.,1.],exit_['state'])
    assert inactive['action']==2 and inactive['state']==[-1,0,-1]
    assert inactive['counts'].get('mode_entries',0)==0
    board=board_with_empty(4);moved,legal=actual_afterstates(board)
    entered=engine._selection(board,moved,legal,[0.]*4,0,[0.,0.,0.,1.],inactive['state'])
    assert entered['state'][0:2]==[15,1] and entered['counts']['mode_entries']==1


def test_features_use_closest_max_tile_weighted_rank_and_lexical_legal_ties():
    engine=NativeStrategy(leaf(),BUILD)
    after=[0]*16;after[3]=after[4]=3
    result=engine._selection(board_with_empty(4),[after]*4,[0,1,0,1],[0.]*4,1,
        [1.,0.,0.,0.],[0,1,3])
    assert result['action']==1 and result['state']==[0,1,1]
    np.testing.assert_array_equal(result['features'][1],[14/16.,-1/6.,24/(16.*6.*4),0.])
    np.testing.assert_array_equal(result['features'][3],[14/16.,-1/6.,24/(16.*6.*4),1.])
    assert result['counts']['feature_evaluations']==2
    assert result['counts']['dot_product_multiplications']==8
    assert result['counts']['dot_product_additions']==8
    assert result['counts']['strategy_memory_writes']==1


def test_model_and_environment_laws_separate_with_exact_full_initial_raw_accounting():
    engine=NativeStrategy(leaf(),BUILD)
    seeds=[297000030100,297000030101]
    low=engine.evaluate([0.]*4,.23,0.,seeds,max_steps=1)
    high=engine.evaluate([0.]*4,.23,1.,seeds,max_steps=1)
    for evaluated,mass in ((low,6),(high,12)):
        assert all(sum((1<<rank) if rank else 0 for rank in g['final_board'])==mass
                   for g in evaluated['game_summaries'])
        assert all(g['status']=='CUTOFF' and g['steps']==1 for g in evaluated['game_summaries'])
        assert evaluated['counts']['environment']['raw_tile_productions']==6
        assert evaluated['counts']['environment']['initial_spawns']==4
        assert evaluated['counts']['environment']['post_action_spawns']==2
        assert evaluated['counts']['environment']['environment_random_draws']==12
        assert all(g['utility']==g['score']/2048. for g in evaluated['game_summaries'])


def test_nonzero_program_resets_per_game_and_behavior_counts_cover_actual_steps():
    source=leaf();before=source.weights.copy()
    engine=NativeStrategy(source,BUILD)
    evaluated=engine.evaluate([.2,-.3,.4,.8],.19,.1,[297000030200]*2,max_steps=128)
    left,right=evaluated['game_summaries']
    assert left==right
    counts=evaluated['counts']['strategy']
    assert counts['game_memory_resets']==2 and counts['mode_entries']>=2
    assert counts['active_choices']>0
    assert counts['active_choices']+counts.get('source_fallback_choices',0)==left['steps']+right['steps']
    assert counts['mode_guard_checks']==left['steps']+right['steps']
    assert counts['feature_evaluations']*4==counts['dot_product_multiplications']
    for key,value in counts.items():
        assert value==left['strategy_counts'][key]+right['strategy_counts'][key]
    np.testing.assert_array_equal(source.weights,before)
    assert source.updates==0 and not source.weights.flags.writeable
    with pytest.raises(ValueError,match='four finite'):
        engine.evaluate([1.01,0.,0.,0.],.19,.1,[297000030201])
