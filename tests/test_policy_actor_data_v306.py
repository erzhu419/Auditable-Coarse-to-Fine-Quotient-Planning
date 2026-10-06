"""Factual complete-game splits, paid tails and immutable full-policy acquisition."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import pytest

from acfqp.science import policy_actor_data_v306 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD=Path(__file__).resolve().parents[1]/'reports/policy_alignment_v306/runtime/tests/data'
QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)


@pytest.fixture(scope='module')
def actual():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',11)
    template=QueryTD(QueryParent(NtupleValue(rule,BUILD),QUERY,QUERY,.5),'PRIOR',BUILD)
    leaf=SplitLeaf(template,'LOCAL_RISK',BUILD);leaf.freeze();rows=[]
    result=core.acquire_policy_data(leaf,0,0,'SOURCE_DATA',.1,rows.append,BUILD,raw_budget=8192)
    return result,rows,leaf


def test_complete_games_chronological_split_and_actual_budget(actual):
    result,rows,leaf=actual;data=result['dataset'];training=result['acquisition']['training'];n=len(data['games'])
    assert n>=3 and data['fit_game_count']==4*n//5
    assert data['fit_step_end']==sum(g['steps'] for g in data['games'][:data['fit_game_count']])
    assert len(data['afterstates'])==sum(g['steps'] for g in data['games'])
    assert training['raw_tiles']==8192 and training['after_stream']['random_draw_position']==16384
    assert sum(len(r['raw_spawns']) for r in rows if r['kind']=='TRAIN')==8192
    assert data['costs']['fit_raw_tiles']+data['costs']['heldout_raw_tiles']+data['costs']['excluded_tail_raw_tiles']==8192
    assert result['acquisition']['warmup']['raw_tiles']==0 and leaf.updates==0


def test_observed_pool_and_no_actor_learning_or_planning_probability_feedback(actual):
    result,rows,leaf=actual;data=result['dataset'];memory=data['fit_memory']
    assert memory['method']=='POOLED' and memory['observations_seen']==data['fit_end_raw']
    assert memory['modules'][0]['alpha']+memory['modules'][0]['beta']-2==data['fit_end_raw']
    assert data['actor_memory_A_end']['observations_seen']==8192
    assert all(r['model_p_four']==.1 and r['actor_head_updates']==0 for r in rows)
    assert all(not r['counts']['learning'] and not r['bank_update_counts'] and not r['td_examples'] for r in rows if r['kind']=='TRAIN')
    assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable


def test_first_wrong_actual_action_score_is_detected(actual):
    _,rows,_=actual;row=deepcopy(next(r for r in rows if r['kind']=='TRAIN' and r['actions']))
    row['scores'][0]+=4
    with pytest.raises(ValueError,match='legality or score'):
        core.FixedPolicyData(0,0).consume(row)


def test_stream_state_discontinuity_is_detected(actual):
    _,rows,_=actual;train=[r for r in rows if r['kind']=='TRAIN'];replay=core.FixedPolicyData(0,0)
    replay.consume(train[0]);row=deepcopy(train[1]);row['start']['raw_tiles']+=1
    with pytest.raises(ValueError,match='changed state'): replay.consume(row)
