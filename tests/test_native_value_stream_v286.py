"""Finite independent ground/SARSA references; no V286 campaign draws."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import native_value_stream_v286 as core
from acfqp.science import controlled_predictive_frozen_leaf_planning_v135 as v135
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/natural_online_value_v286/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def make_leaf(source_query=QUERY, constant=.5, goal=4):
    rule = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))), 'uniform',goal)
    source = NtupleValue(rule,BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    return QueryTD(QueryParent(source,source_query,QUERY,constant),'PRIOR',BUILD)


def original_choose(leaf, board, p_four, depth=2):
    if depth==1:
        return leaf.choose(tuple(board))
    library = v135._backend(BUILD,Counter())
    native = leaf.model
    moved, scores = np.empty((4,16),dtype=np.int32), np.zeros(4,dtype=np.int64)
    tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4,dtype=np.int32)
    counts = np.zeros(len(v135.COUNT_NAMES),dtype=np.uint64)
    raw = leaf.source_query if leaf.kind=='PRIOR' else leaf.target_query
    best = library.frozen_leaf_choose_v135(np.asarray(board,dtype=np.int32),native.patterns,
        np.zeros((4,8),dtype=np.int32),leaf.radix,-1,leaf.weights,native.table,native.scores,
        native.cells,float(raw['goal_bonus']),float(QUERY['goal_bonus']),float(QUERY['failure_penalty']),
        leaf.failure_shift,leaf.success_shift,1.-p_four,p_four,
        int(not core._same_query(leaf.source_query,leaf.target_query)),moved,scores,tails,values,legal,counts)
    assert best>=0
    return dict(action=core.ACTIONS[best],value=float(values[best]))


def classify(board, goal):
    return 'WON' if max(board)>=goal else 'ACTIVE' if ground.legal_actions_v1(tuple(board)) else 'LOST'


def python_stream(leaf, draws, model_p, environment_p, max_steps):
    board, pending, status = [0]*16, None, 'NOT_STARTED'
    episode, step, initial, score, raw_index = -1,0,0,0,0
    actions, scores, spawns, updates, games = [],[],[],[],[]
    for cell_draw,rank_draw in draws:
        if status not in ('ACTIVE','INITIALIZING'):
            episode+=1; board=[0]*16; pending=None; initial=step=score=0
            start_raw=raw_index; status='INITIALIZING'
        if status=='INITIALIZING':
            after,kind = board,'INITIAL'
        else:
            chosen = original_choose(leaf,board,model_p)
            after,gained,changed = ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(chosen['action']))
            assert changed
            if pending is not None and leaf.weights.flags.writeable:
                tail = QUERY['goal_bonus'] if max(after)>=leaf.radix else leaf.model.value(after)+leaf.failure_shift+leaf.success_shift
                fitted = leaf.update(pending,gained/2048.+tail)
                updates.append(dict(target=fitted['target'],raw_target=fitted['raw_target'],error=fitted['error']))
            pending = None if max(after)>=leaf.radix else tuple(after)
            actions.append(chosen['action']); scores.append(gained)
            score+=gained; step+=1; kind='POST_ACTION'
        empty = [i for i,rank in enumerate(after) if not rank]
        cell = empty[int(cell_draw*len(empty))]
        rank = 1 if rank_draw<1.-environment_p else 2
        board=list(after); board[cell]=rank
        spawns.append(dict(episode=episode,kind=kind,cell=cell,rank=rank)); raw_index+=1
        if kind=='INITIAL':
            initial+=1
            if initial==2:
                status=classify(board,leaf.radix)
        else:
            status=classify(board,leaf.radix)
            if status=='LOST' and pending is not None:
                if leaf.weights.flags.writeable:
                    fitted=leaf.update(pending,-QUERY['failure_penalty'])
                    updates.append(dict(target=fitted['target'],raw_target=fitted['raw_target'],error=fitted['error']))
                pending=None
            if status=='ACTIVE' and step==max_steps:
                status='CUTOFF'; pending=None
            if status!='ACTIVE':
                games.append(dict(episode=episode,start_raw=start_raw,end_raw=raw_index,
                    score=score,steps=step,status=status))
    return dict(board=board,pending=pending,status=status,actions=actions,scores=scores,
                raw_spawns=spawns,updates=updates,games=games)


@pytest.mark.parametrize('source_query,constant', [(QUERY,.5),
    (dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),.25)])
def test_native_training_matches_independent_ground_sarsa_with_query_offset(source_query,constant):
    leaf, reference = make_leaf(source_query,constant), make_leaf(source_query,constant)
    stream = core.NativeValueStream(leaf,28600001,BUILD,max_steps=5)
    actual = stream.advance(leaf,0,None,.37,.5,18)
    expected = python_stream(reference,stream.common_draws(28600001,18),.37,.5,5)
    assert actual['raw_spawns']==expected['raw_spawns']
    assert actual['actions']==expected['actions'] and actual['scores']==expected['scores']
    assert actual['end']['board']==expected['board'] and actual['end']['status']==expected['status']
    assert actual['end']['pending_afterstate']==(None if expected['pending'] is None else list(expected['pending']))
    assert [{key:u[key] for key in ('target','raw_target','error')} for u in actual['updates']]==expected['updates']
    np.testing.assert_array_equal(leaf.weights,reference.weights)
    assert leaf.updates==reference.updates==len(actual['updates'])
    assert leaf.counts['td_updates']==leaf.model.counts['td_updates']==leaf.updates
    assert leaf.counts['inner_td_updates']==leaf.updates
    assert actual['counts']['environment']['raw_tile_productions']==18
    assert actual['counts']['environment']['environment_random_draws']==36
    assert all(u['raw_target']==u['target']-leaf.offset for u in actual['updates'])
    assert all(a['next_afterstate_tail'] is None for a in actual['action_records'] if a['step']==0)
    stream.close()


def test_partial_initialization_and_chunk_splits_preserve_rng_pending_and_weights():
    whole, split = make_leaf(),make_leaf()
    a,b = core.NativeValueStream(whole,28600002,BUILD,max_steps=5),core.NativeValueStream(split,28600002,BUILD,max_steps=5)
    once=a.advance(whole,0,None,.1,.1,18)
    chunks=[]
    for amount in (1,1,3,5,8):
        chunks.append(b.advance(split,0,split,.1,.1,amount))
    assert chunks[0]['end']['status']=='INITIALIZING' and chunks[0]['end']['initial_count']==1
    assert chunks[0]['actions']==[] and chunks[0]['updates']==[]
    assert chunks[1]['end']['initial_count']==2 and chunks[1]['end']['status']=='ACTIVE'
    assert a.state()==b.state() and a.counts==b.counts
    assert once['raw_spawns']==[r for c in chunks for r in c['raw_spawns']]
    assert once['actions']==[r for c in chunks for r in c['actions']]
    np.testing.assert_array_equal(whole.weights,split.weights)
    assert whole.updates==split.updates
    a.close(); b.close()


def test_bank_switch_updates_old_table_from_new_bank_before_fixed_action_execution():
    old,new = make_leaf(),make_leaf()
    new.weights[:]+=.003
    stream=core.NativeValueStream(old,28600003,BUILD)
    first=stream.advance(old,7,None,.37,.5,3)
    state=first['end']
    assert state['pending_bank_id']==7
    expected_old=make_leaf(); expected_old.weights[:]=old.weights
    expected_new=make_leaf(); expected_new.weights[:]=new.weights
    chosen=original_choose(expected_new,state['board'],.37)
    after,score,changed=ground.swipe_board_v1(tuple(state['board']),ground.Swipe2048Action(chosen['action']))
    assert changed
    tail=QUERY['goal_bonus'] if max(after)>=new.radix else expected_new.model.value(after)
    fitted=expected_old.update(state['pending_afterstate'],score/2048.+tail)
    new_before=new.weights.copy()
    second=stream.advance(new,9,old,.37,.5,1)
    assert second['actions']==[chosen['action']]
    event=second['updates'][0]
    assert event['bank_id']==7 and event['kind']=='PREVIOUS_PENDING'
    assert event['target']==fitted['target'] and event['error']==fitted['error']
    assert event['target']!=chosen['value']  # SARSA uses chosen afterstate, not H2 expectation.
    np.testing.assert_array_equal(old.weights,expected_old.weights)
    np.testing.assert_array_equal(new.weights,new_before)
    assert old.updates==1 and new.updates==0
    assert second['end']['pending_bank_id']==9
    assert second['bank_learning']['7']['td_updates']==1
    stream.close()


def test_budget_and_phase_boundaries_keep_pending_but_true_cutoff_censors_it():
    leaf=make_leaf(); stream=core.NativeValueStream(leaf,28600004,BUILD,max_steps=5)
    first=stream.advance(leaf,0,None,.1,0.,1)
    second=stream.advance(leaf,0,None,.1,1.,1)
    assert first['raw_spawns'][0]['rank']==1 and second['raw_spawns'][0]['rank']==2
    assert first['end']['raw_tiles']==1 and second['start']==first['end']
    third=stream.advance(leaf,0,None,.1,0.,2)
    assert third['end']['pending_afterstate'] is not None and third['end']['status']=='ACTIVE'
    saved=third['end']
    fourth=stream.advance(leaf,0,leaf,.1,0.,3)
    assert fourth['start']==saved
    assert fourth['end']['status']=='CUTOFF' and fourth['end']['pending_afterstate'] is None
    assert fourth['completed_games'][0]['steps']==5
    assert fourth['counts']['learning']['censored_pending_updates']==1
    assert all(u['kind']=='PREVIOUS_PENDING' for u in fourth['updates'])
    stream.close()


def test_frozen_arm_reads_no_unused_td_tail_and_raw_rank_stream_matches_learning():
    frozen,train=make_leaf(),make_leaf()
    frozen.freeze(); before=frozen.weights.copy()
    a,b=core.NativeValueStream(frozen,28600005,BUILD,max_steps=5),core.NativeValueStream(train,28600005,BUILD,max_steps=5)
    rank_a,rank_b=[],[]
    for p,quota in ((.1,10),(.5,12),(.1,10)):
        ar=a.advance(frozen,0,frozen,.2,p,quota)
        br=b.advance(train,0,train,.2,p,quota)
        rank_a.extend(r['rank'] for r in ar['raw_spawns']); rank_b.extend(r['rank'] for r in br['raw_spawns'])
        assert ar['updates']==[]
        assert ar['counts']['learning'].get('value_predictions',0)==0
        assert all(r['next_afterstate_tail'] is None for r in ar['action_records'])
    assert rank_a==rank_b and len(rank_a)==32
    assert frozen.updates==0 and train.updates>0
    np.testing.assert_array_equal(frozen.weights,before)
    assert a.state()['random_draw_position']==b.state()['random_draw_position']==64
    a.close(); b.close()


def test_true_won_credits_previous_afterstate_and_never_fits_winning_afterstate():
    leaf=make_leaf(); leaf.weights[:]=0.
    stream=core.NativeValueStream(leaf,28600007,BUILD)
    receipt=stream.advance(leaf,0,None,.5,1.,64)
    won=next(g for g in receipt['completed_games'] if g['status']=='WON')
    action_index=next(i for i,a in enumerate(receipt['action_records'])
        if a['episode']==won['episode'] and a['step']==won['steps']-1)
    updates=[u for u in receipt['updates'] if u['episode']==won['episode']
             and u['step']==won['steps']-1]
    assert len(updates)==1 and updates[0]['kind']=='PREVIOUS_PENDING'
    assert updates[0]['target']==receipt['scores'][action_index]/2048.+4.
    assert receipt['action_records'][action_index]['next_afterstate_tail']==4.
    assert all(u['kind']!='TERMINAL_LOSS' for u in receipt['updates'] if u['episode']==won['episode'])
    stream.close()


def test_true_loss_fits_current_afterstate_once_to_terminal_penalty():
    leaf=make_leaf(goal=11); leaf.weights[:]=100.
    stream=core.NativeValueStream(leaf,28600008,BUILD)
    receipts=[]
    for _ in range(16):
        receipt=stream.advance(leaf,0,leaf,.5,.5,64)
        receipts.append(receipt)
        if any(g['status']=='LOST' for g in receipt['completed_games']):
            break
    lost=next(g for g in receipt['completed_games'] if g['status']=='LOST')
    terminal=[u for u in receipt['updates'] if u['episode']==lost['episode'] and u['kind']=='TERMINAL_LOSS']
    assert len(terminal)==1 and terminal[0]['target']==terminal[0]['raw_target']==-4.
    assert terminal[0]['step']==lost['steps']-1 and terminal[0]['bank_id']==0
    assert terminal[0]['raw_tiles_before_update']==lost['end_raw']
    assert leaf.updates==sum(len(r['updates']) for r in receipts)
    assert leaf.parent.source.updates==0
    assert leaf.parent.source.counts.get('td_updates',0)==0
    assert not np.shares_memory(leaf.weights,leaf.parent.source.weights)
    assert 'seed' not in lost and lost['stream_seed']==28600008
    stream.close()


@pytest.mark.parametrize('depth',[1,2])
def test_mutable_snapshot_eval_matches_original_policy_without_training_or_stream_changes(depth):
    leaf=make_leaf(); stream=core.NativeValueStream(leaf,28600006,BUILD)
    stream.advance(leaf,0,None,.1,.1,4)
    before=stream.state(),{k:v.copy() for k,v in stream.counts.items()},leaf.weights.copy(),leaf.updates
    evaluation=stream.evaluate_games(leaf,.37,.5,[31,47],depth=depth,max_steps=6)
    assert leaf.weights.flags.writeable and leaf.updates==before[3]
    np.testing.assert_array_equal(leaf.weights,before[2])
    assert stream.state()==before[0] and stream.counts==before[1]
    for row in evaluation['game_summaries']:
        board=[0]*16; score=0; status='ACTIVE'; draws=stream.common_draws(row['seed'],8)
        for index,(cell_draw,rank_draw) in enumerate(draws):
            if index>=2:
                chosen=original_choose(leaf,board,.37,depth)
                after,gained,_=ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(chosen['action']))
                score+=gained
            else:
                after=board
            empty=[i for i,r in enumerate(after) if not r]
            board=list(after); board[empty[int(cell_draw*len(empty))]]=1 if rank_draw<.5 else 2
            if index>=1:
                status=classify(board,leaf.radix)
                if status!='ACTIVE':
                    break
        if status=='ACTIVE':
            status='CUTOFF'
        assert row['score']==score and row['final_board']==board and row['status']==status
        assert row['steps']==index-1
    assert evaluation['counts']['environment']['initial_spawns']==4
    assert 'learning' not in evaluation['counts']
    stream.close()
