"""Finite V317 coupled-greedy reader, exact branch choices and paid new operator work."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_greedy_targets_v317 as audit
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import SplitLeaf
from acfqp.science.native_local_targets_v314 import fit_local_targets
from acfqp.science.native_greedy_targets_v317 import fit_greedy_targets
from acfqp.science.closed_loop_versions_v313 import snapshot_weights
from acfqp.science.greedy_target_run_v317 import configuration

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/greedy_targets_v317/runtime/tests/independent_audit'


@pytest.fixture(scope='module')
def actual(tmp_path_factory):
    out=tmp_path_factory.mktemp('v317_coupled_reader')
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)
    template=QueryTD(QueryParent(source,query,query,.5),'PRIOR',BUILD);template.freeze()
    greedy,sarsa=SplitLeaf(template,'LOCAL_RISK',BUILD),SplitLeaf(template,'LOCAL_RISK',BUILD)
    rng=np.random.default_rng(317003)
    r=rng.normal(0.,.015,greedy.reward_weights.shape);p=rng.normal(0.,.25,greedy.risk_weights.shape)
    for leaf in (greedy,sarsa):
        leaf.reward_weights[:]=r;leaf.risk_weights[:]=p
    active=[1,0,2,0,0,1,0,0,3,0,0,0,0,0,0,0];activepost=list(active);activepost[15]=1
    lost=[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1];lostafter=list(lost);lostafter[15]=0
    prewin=[3,3]+[0]*14;prewinpost=list(prewin);prewinpost[15]=1
    won=[4]+[0]*15;wonpost=list(won);wonpost[15]=1
    boards=np.asarray([active,lostafter,prewin,won,active,lostafter],dtype=np.int32)
    post=np.asarray([activepost,lost,prewinpost,wonpost,activepost,lost],dtype=np.int32)
    games=[dict(steps=2,status='LOST'),dict(steps=2,status='WON'),dict(steps=2,status='LOST')]
    rewards=np.asarray([.11,.22,.33,.44,.55,.66])
    dataset=dict(afterstates=boards,postspawn_boards=post,rewards=rewards,ends=np.asarray([2,4,6],dtype=np.int64),
        terminal_codes=np.asarray([-1,1,-1],dtype=np.int32),fit_game_count=2,fit_step_end=4)
    version=dict(file='FIRST_LOCAL_v0.npz',arm='FIRST_LOCAL',version=0,updates=0)
    snapshot=snapshot_weights(greedy)
    fit=fit_greedy_targets(greedy,dataset,snapshot,BUILD,out/'greedy.npz',bootstrap_version=version)
    sarsa_fit=fit_local_targets(sarsa,dataset,snapshot_weights(sarsa),BUILD,out/'sarsa.npz',bootstrap_version=version)
    head=SimpleNamespace(reward=snapshot['reward'].reshape(-1),terminal=snapshot['terminal'].reshape(-1))
    return SimpleNamespace(out=out,fit=fit,sarsa_fit=sarsa_fit,head=head,version=version,boards=boards,
        post=post,games=games,rewards=rewards,leaf=greedy)


def read(actual,fit=None,post=None,head=None):
    return audit.check_greedy_targets(actual.fit if fit is None else fit,actual.boards,
        actual.post if post is None else post,actual.games,2,actual.head if head is None else head,actual.version,radix=4)


def test_actual_native_greedy_arrays_actions_targets_and_all_costs_match_independent_reader(actual):
    targets=read(actual)
    assert targets[2].tolist()==[1,3,2,0] and targets[3][1]==targets[3][3]==-1
    assert targets[0][1]==targets[1][1]==targets[0][3]==targets[1][3]==0.
    assert targets[0][2]==16/2048. and targets[1][2]==1.
    inventory=audit.address_inventory(actual.boards,actual.games,2,radix=4)
    audit.check_complete_fit(actual.fit,actual.boards,actual.rewards,actual.games,2,inventory,targets)
    audit.check_td_targets(actual.sarsa_fit,actual.boards,actual.rewards,actual.games,2,actual.head,actual.version,radix=4)
    audit.check_equal_fit_work(actual.sarsa_fit,actual.fit)


def test_vector_four_swipes_and_first_max_ties_match_literal_physics():
    boards=np.asarray([[1,1,0,0]+[0]*12,[1,2,1,2]*4,[3,3]+[0]*14,[0]*16],dtype=np.int32)
    moved,scores,legal=audit.vector_swipes(boards,radix=4)
    for row,board in enumerate(boards):
        for index,action in enumerate(audit.ACTIONS):
            after,score=audit.swipe(board.tolist(),action)
            assert moved[row,index].tolist()==after and scores[row,index]==score
            assert bool(legal[row,index])==(after!=board.tolist())
    head=SimpleNamespace(reward=np.zeros(4*4**6),terminal=np.zeros(4*4**6))
    current=np.asarray([[1]+[0]*15],dtype=np.int32)
    observed=np.asarray([[1,0,2,0]+[0]*12],dtype=np.int32)
    target=audit.greedy_targets(current,observed,[dict(steps=1,status='LOST')],1,head,radix=4)
    chosen=audit.literal_choose(observed[0].tolist(),head.reward,head.terminal,'LOCAL_RISK',.5,depth='DIRECT',radix=4)
    assert target[3][0]==audit.ACTIONS.index(chosen['action'])


@pytest.mark.parametrize('key',('targetreward','targetwin','targetkind','selected_action'))
def test_wrong_native_target_or_decoupled_action_is_rejected(actual,key):
    fit=deepcopy(actual.fit)
    with np.load(fit['target_artifact']['file']) as saved:
        arrays={name:saved[name].copy() for name in saved.files}
    arrays[key][0]+=1 if key in ('targetkind','selected_action') else .2
    path=actual.out/(key+'.npz');np.savez_compressed(path,**arrays)
    fit['target_artifact']['file']=str(path);fit['target_artifact']['saved_bytes']=path.stat().st_size
    with pytest.raises(ValueError,match='every saved greedy'):
        read(actual,fit)


def test_wrong_actual_postspawn_or_current_updated_head_cannot_supply_targets(actual):
    post=actual.post.copy();post[0]=0;post[0,0]=1
    with pytest.raises(ValueError,match='every saved greedy'):
        read(actual,post=post)
    wrong=SimpleNamespace(reward=actual.head.reward+.1,terminal=actual.head.terminal)
    with pytest.raises(ValueError,match='every saved greedy'):
        read(actual,head=wrong)


def test_greedy_counterfactual_candidates_and_reads_cannot_be_omitted(actual):
    fit=deepcopy(actual.fit);fit['bootstrap_counts']['action_candidates']-=4
    with pytest.raises(ValueError,match='all four greedy candidates'):
        read(actual,fit)
    fit=deepcopy(actual.fit);fit['bootstrap_planning_counts']['learned_swipe_calls']-=4
    with pytest.raises(ValueError,match='counterfactual greedy branch swipes'):
        read(actual,fit)


def test_current_factual_reward_and_heldout_board_do_not_enter_greedy_targets(actual):
    changed=actual.post.copy();changed[4:]=0
    expected=audit.greedy_targets(actual.boards,actual.post,actual.games,2,actual.head,radix=4)
    other=audit.greedy_targets(actual.boards,changed,actual.games,2,actual.head,radix=4)
    for first,second in zip(expected[:4],other[:4]):
        assert np.array_equal(first,second)
    assert expected[0][0]!=actual.rewards[0]


def test_new_operator_freeze_cost_schema_and_seed_families_match_driver():
    source=ROOT/'reports/fresh_source_v312/source_summary.json'
    audit.equal_tree(json.loads(json.dumps(configuration(source))),audit.expected_configuration(source),'exact V317 freeze')
    assert audit.evaluation_seed(7,'B',31)==317907100031
    assert audit.post_seed(7,'B',2)==317571200000
    assert audit.expected_configuration(source)['primary']=='GREEDY_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
