"""Observed routes remain causal even when their game labels are excluded."""
from collections import Counter
from copy import deepcopy
import gzip
import json

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import conditional_carrier_data_v294 as retained
from acfqp.science import routed_carrier_data_v295 as routed
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.retained_actor_data_v287 import _memory_state


def action(board):
    return min((score,a.value,after) for a in ground.ACTION_ORDER
        for after,score,changed in [ground.swipe_board_v1(tuple(board),a)] if changed)


def warm_game():
    board=[0]*16; raw=[]; actions=[]; scores=[]
    for cell in (0,15):
        board[cell]=2; raw.append(dict(kind='INITIAL',cell=cell,rank=2))
    while ground.state_from_board_v1(tuple(board)).status.value=='ACTIVE':
        score,a,after=action(board); cell=next(i for i,r in enumerate(after) if r==0)
        board=list(after); board[cell]=2
        raw.append(dict(kind='POST_ACTION',cell=cell,rank=2)); actions.append(a); scores.append(score)
    return dict(kind='WARMUP',lifecycle=0,raw_spawns=raw,actions=actions,scores=scores,
        final_board=board,summary=dict(steps=len(actions),score=sum(scores),status='LOST'))


@pytest.fixture(scope='module')
def receipt_fixture():
    block=1027; memory=SpawnMemory('LIBRARY'); rows=[]
    while memory.observations_seen<256:
        game=warm_game(); rows.append(game)
        for spawn in game['raw_spawns']: memory.observe(spawn['rank'])
    warm_raw=memory.observations_seen; warm_counts=dict(memory.counts)
    warm_modules=deepcopy(memory.modules); warm_active=memory.module_id
    state=dict(board=[0]*16,pending_afterstate=None,pending_bank_id=None,episode=-1,
        step=0,return_score=0,status='NOT_STARTED',initial_count=0,raw_tiles=0,
        post_action_spawns=0,game_start_raw=0,stream_seed=1,random_draw_position=0)
    phases={}; start_phase=deepcopy(state); acquired=Counter(); facts={}
    while state['raw_tiles']<3*block:
        before=deepcopy(state); phase_i=state['raw_tiles']//block; phase=routed.PHASES[phase_i]
        p,mod=memory.predict(),memory.module_id
        capacity=min(64-memory.pending_n,(phase_i+1)*block-state['raw_tiles'])
        raw=[]; actions=[]; scores=[]; events=[]; completed=[]
        for _ in range(capacity):
            position=state['raw_tiles']
            rank=1 if block-128<=position<2*block else 2
            if state['status'] in ('NOT_STARTED','LOST','WON'):
                state.update(board=[0]*16,episode=state['episode']+1,step=0,return_score=0,
                    status='INITIALIZING',initial_count=0,game_start_raw=position,
                    pending_afterstate=None,pending_bank_id=None)
            if state['status']=='INITIALIZING':
                kind='INITIAL'; cell=0 if state['initial_count']==0 else 15
                state['board'][cell]=rank; state['initial_count']+=1
                if state['initial_count']==2: state['status']='ACTIVE'
            else:
                facts.setdefault(state['episode'],[]).append((p,mod,position))
                score,a,after=action(state['board']); cell=next(i for i,r in enumerate(after) if r==0)
                actions.append(a); scores.append(score); kind='POST_ACTION'
                state['board']=list(after); state['board'][cell]=rank
                state['step']+=1; state['return_score']+=score; state['post_action_spawns']+=1
                state['status']=ground.state_from_board_v1(tuple(state['board'])).status.value
                state['pending_afterstate']=list(after) if state['status']=='ACTIVE' else None
                state['pending_bank_id']=0 if state['status']=='ACTIVE' else None
            raw.append(dict(kind=kind,cell=cell,rank=rank,episode=state['episode']))
            state['raw_tiles']+=1; state['random_draw_position']+=2
            event=memory.observe(rank)
            if event is not None: events.append(event)
            if state['status'] in ('WON','LOST'):
                completed.append(dict(episode=state['episode'],stream_seed=1,
                    start_raw=state['game_start_raw'],end_raw=state['raw_tiles'],steps=state['step'],
                    score=state['return_score'],status=state['status']))
                break
        work=dict(raw_tile_productions=len(raw),initial_spawns=len(raw)-len(actions),
            post_action_spawns=len(actions),sampled_transitions=len(actions)); acquired.update(work)
        rows.append(dict(kind='CARRIER_TRAIN',lifecycle=0,phase=phase,module_id_before=mod,
            model_p_four=p,actor_weights_readonly=True,leaf_updates_before=0,leaf_updates_after=0,
            start=before,end=deepcopy(state),raw_spawns=raw,actions=actions,scores=scores,
            completed_games=completed,memory_events=events,
            counts=dict(environment=work,planning={},learning={})))
        if state['raw_tiles']==(phase_i+1)*block:
            phases[phase]=dict(training=dict(before_stream=start_phase),snapshot=dict(
                stream=deepcopy(state),memory=_memory_state(memory),estimated_p_four=memory.predict()))
            start_phase=deepcopy(state)
    rows.append(dict(kind='VALIDATION_GAME',lifecycle=0,outcome_label=999999))
    expected={0:dict(lifecycle=0,parent=0,warmup=dict(raw_tiles=warm_raw,environment_counts={},
        direct_counts={},memory_counts=warm_counts),carrier=dict(phases=phases,
        final_stream=deepcopy(state),training_counts=dict(environment=dict(acquired),planning={},learning={}))) }
    return rows,expected,facts,block,warm_modules,warm_active


def load(tmp_path,monkeypatch,fixture,loader=routed.load_parent):
    rows,expected,_,block,_,_=fixture
    monkeypatch.setattr(retained,'RAW_PER_PHASE',block)
    path=tmp_path/'carrier.jsonl.gz'
    with gzip.open(path,'wt') as stream:
        for row in rows: stream.write(json.dumps(row)+'\n')
    return loader(path,expected)[0]


def test_before_chunk_modules_align_with_actions_and_do_not_use_terminal_feedback(receipt_fixture,tmp_path,monkeypatch):
    data=load(tmp_path,monkeypatch,receipt_fixture); rows,_,facts,_,_,_=receipt_fixture
    for phase in data['phases'].values():
        for game in phase['fit_games']+phase['heldout_games']:
            assert game['module_ids'].dtype==np.int64
            assert game['module_ids'].tolist()==[mod for _,mod,_ in facts[game['metadata']['episode']]]
            assert game['model_p_four'].tolist()==[p for p,_,_ in facts[game['metadata']['episode']]]
        for anchor in phase['anchors']:
            assert anchor['module_id']==facts[anchor['episode']][anchor['step']][1]
    switching=next(r for r in rows if r['kind']=='CARRIER_TRAIN' and r['actions']
        and any(e['kind']=='created' for e in r['memory_events']))
    assert switching['module_id_before']!=switching['memory_events'][-1]['module_id']
    game_facts=facts[switching['raw_spawns'][-1]['episode']]
    in_chunk=[mod for _,mod,pos in game_facts if switching['start']['raw_tiles']<=pos<switching['end']['raw_tiles']]
    assert in_chunk and all(mod==switching['module_id_before'] for mod in in_chunk)


def test_route_inventory_includes_heldout_mixed_tail_and_return_reactivation(receipt_fixture,tmp_path,monkeypatch):
    data=load(tmp_path,monkeypatch,receipt_fixture); _,_,_,block,warm_modules,warm_active=receipt_fixture
    assert data['warmup_modules']==warm_modules and data['warmup_module_ids']==[m['id'] for m in warm_modules]
    assert data['initial_active_module_id']==warm_active
    timeline=[e for p in routed.PHASES for e in data['routing_timeline'][p]]
    assert [e['raw_index'] for e in timeline]==sorted(e['raw_index'] for e in timeline)
    created=next(e for e in timeline if e['kind']=='created')
    assert created['raw_index']>block-128 and created['raw_index']<block
    assert any(e['kind']=='reactivated' and e['module_id']==warm_active
               for e in data['routing_timeline']['A_prime'])
    assert any(e['kind']=='GAME_COMPLETE' and e['exclusion_reason']=='MIXED_PHASE' and not e['fit'] for e in timeline)
    for phase in routed.PHASES:
        fit_ids={(g['metadata']['episode'],g['metadata']['end_raw']) for g in data['phases'][phase]['fit_games']}
        complete=[e for e in data['routing_timeline'][phase] if e['kind']=='GAME_COMPLETE']
        assert {(e['metadata']['episode'],e['metadata']['end_raw']) for e in complete if e['fit']}==fit_ids
        assert any(not e['fit'] and e['pure_phase']==phase for e in complete)
    assert not any(e['kind']=='GAME_COMPLETE' and e['fit'] for e in data['routing_timeline']['A'] if e['raw_index']>=created['raw_index'])
    original_events=[e for r in receipt_fixture[0] if r['kind']=='CARRIER_TRAIN' for e in r['memory_events']]
    assert data['costs']['routing_event_inventory']==dict(Counter(e['kind'] for e in original_events))
    assert data['costs']['new_environment_raw_tiles']==0 and data['costs']['reused_carrier_raw_tiles']==3*block


def test_routing_precedes_same_raw_complete_commit_and_preserves_V294_game_split(receipt_fixture,tmp_path,monkeypatch):
    data=load(tmp_path,monkeypatch,receipt_fixture)
    original=load(tmp_path,monkeypatch,receipt_fixture,retained.load_parent)
    for phase in routed.PHASES:
        for split in ('fit_games','heldout_games'):
            new=data['phases'][phase][split]; old=original['phases'][phase][split]
            assert [g['metadata'] for g in new]==[g['metadata'] for g in old]
            for a,b in zip(new,old):
                for field in ('afterstates','rewards','model_p_four'):
                    assert np.array_equal(a[field],b[field])
        timeline=data['routing_timeline'][phase]
        for i,event in enumerate(timeline):
            if event['kind']=='GAME_COMPLETE':
                assert not any(e['kind']!='GAME_COMPLETE' and e['raw_index']==event['raw_index'] for e in timeline[i+1:])


def test_future_validation_labels_and_wrong_after_spawn_route_cannot_enter_training(receipt_fixture,tmp_path,monkeypatch):
    rows,expected,facts,block,modules,active=deepcopy(receipt_fixture)
    rows[-1]['outcome_label']=-999999
    data=load(tmp_path,monkeypatch,(rows,expected,facts,block,modules,active))
    assert data['routing_timeline']['A']
    changed=next(r for r in rows if r['kind']=='CARRIER_TRAIN'
        and any(e['kind']=='created' for e in r['memory_events']))
    changed['module_id_before']=changed['memory_events'][-1]['module_id']
    with pytest.raises(ValueError,match='preceding observed raw prefix'):
        load(tmp_path,monkeypatch,(rows,expected,facts,block,modules,active))
