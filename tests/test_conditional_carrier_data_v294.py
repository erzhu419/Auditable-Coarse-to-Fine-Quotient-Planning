"""Legal deterministic receipts verify chronology and observed-prefix inputs."""
from collections import Counter
from copy import deepcopy
import gzip
import json

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import conditional_carrier_data_v294 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.retained_actor_data_v287 import _memory_state


def events():
    board = (2,)+(0,)*14+(2,)
    raw = [(dict(kind='INITIAL', cell=0, rank=2), None, None),
           (dict(kind='INITIAL', cell=15, rank=2), None, None)]
    for _ in range(512):
        legal = [(score, action.value, after) for action in ground.ACTION_ORDER
            for after,score,changed in [ground.swipe_board_v1(board, action)] if changed]
        if not legal:
            break
        score,action,after = min(legal)
        cell = next(i for i,rank in enumerate(after) if rank==0)
        raw.append((dict(kind='POST_ACTION', cell=cell, rank=2), action, score))
        board = list(after); board[cell]=2; board=tuple(board)
        if ground.state_from_board_v1(board).status.value=='LOST':
            break
    assert ground.state_from_board_v1(board).status.value=='LOST'
    return raw, board


def fixture(monkeypatch):
    sequence,final = events(); block = 6*len(sequence)+3
    monkeypatch.setattr(core, 'RAW_PER_PHASE', block)
    memory, rows = SpawnMemory('LIBRARY'), []
    while memory.observations_seen<256:
        spawns = [dict(s) for s,_,_ in sequence]
        actions = [a for _,a,_ in sequence if a is not None]
        scores = [s for _,a,s in sequence if a is not None]
        for spawn in spawns:
            memory.observe(spawn['rank'])
        rows.append(dict(kind='WARMUP', lifecycle=0, raw_spawns=spawns, actions=actions, scores=scores,
            final_board=list(final), summary=dict(steps=len(actions), score=sum(scores), status='LOST')))
    warm_raw, warm_counts = memory.observations_seen, dict(memory.counts)
    state = dict(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
        episode=-1, step=0, return_score=0, status='NOT_STARTED', initial_count=0,
        raw_tiles=0, post_action_spawns=0, game_start_raw=0, stream_seed=1, random_draw_position=0)
    phases, acquired, cursor, start_phase = {}, Counter(), 0, deepcopy(state)
    facts = {}
    while cursor<3*block:
        index = cursor//block; phase = core.PHASES[index]
        before, p, module = deepcopy(state), memory.predict(), memory.module_id
        length = min(64-memory.pending_n, (index+1)*block-cursor, len(sequence)-cursor%len(sequence))
        chunk = sequence[cursor%len(sequence):cursor%len(sequence)+length]
        raw, actions, scores, completions, memory_events = [], [], [], [], []
        for spawn,action,score in chunk:
            episode = cursor//len(sequence); spawn=dict(spawn, episode=episode)
            raw.append(spawn)
            if spawn['kind']=='INITIAL':
                if state['status']!='INITIALIZING':
                    state.update(board=[0]*16, episode=episode, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=cursor,
                        pending_afterstate=None, pending_bank_id=None)
                state['initial_count']+=1; state['board'][spawn['cell']]=2
                if state['initial_count']==2: state['status']='ACTIVE'
            else:
                facts.setdefault(episode, []).append((tuple(state['board']), p))
                after,actual,changed=ground.swipe_board_v1(tuple(state['board']), ground.Swipe2048Action(action))
                assert changed and actual==score
                actions.append(action); scores.append(score)
                state['board']=list(after); state['board'][spawn['cell']]=2
                state['step']+=1; state['return_score']+=score; state['post_action_spawns']+=1
                state['status']=ground.state_from_board_v1(tuple(state['board'])).status.value
                state['pending_afterstate']=list(after) if state['status']=='ACTIVE' else None
                state['pending_bank_id']=0 if state['status']=='ACTIVE' else None
            cursor+=1; state['raw_tiles']=cursor; state['random_draw_position']=2*cursor
            event=memory.observe(2)
            if event is not None: memory_events.append(event)
            if state['status']=='LOST':
                completions.append(dict(episode=episode, stream_seed=1, start_raw=state['game_start_raw'],
                    end_raw=cursor, steps=state['step'], score=state['return_score'], status='LOST'))
        work=dict(raw_tile_productions=len(raw), initial_spawns=len(raw)-len(actions),
                  post_action_spawns=len(actions), sampled_transitions=len(actions))
        acquired.update(work)
        rows.append(dict(kind='CARRIER_TRAIN', lifecycle=0, phase=phase,
            module_id_before=module, model_p_four=p, actor_weights_readonly=True,
            leaf_updates_before=0, leaf_updates_after=0, start=before, end=deepcopy(state),
            raw_spawns=raw, actions=actions, scores=scores, completed_games=completions,
            memory_events=memory_events, counts=dict(environment=work, planning={}, learning={})))
        if cursor==(index+1)*block:
            phases[phase]=dict(training=dict(before_stream=start_phase), snapshot=dict(
                stream=deepcopy(state), memory=_memory_state(memory), estimated_p_four=memory.predict()))
            start_phase=deepcopy(state)
    rows.append(dict(kind='VALIDATION_GAME', lifecycle=0, outcome_label=999999))
    expected={0:dict(lifecycle=0, parent=0, warmup=dict(raw_tiles=warm_raw,
        environment_counts={}, direct_counts={}, memory_counts=warm_counts), carrier=dict(phases=phases,
        final_stream=deepcopy(state), training_counts=dict(environment=dict(acquired), planning={}, learning={})))}
    return rows, expected, facts, block


def load(tmp_path, rows, expected):
    path=tmp_path/'carrier.jsonl.gz'
    with gzip.open(path, 'wt') as f:
        for row in rows: f.write(json.dumps(row)+'\n')
    return core.load_parent(path, expected)[0]


def test_pure_whole_game_chronology_excludes_mixed_and_paid_tail(monkeypatch, tmp_path):
    rows, expected, facts, block=fixture(monkeypatch)
    data=load(tmp_path, rows, expected)
    assert [len(data['phases'][p]['fit_games']) for p in core.PHASES]==[4,4,4]
    assert [len(data['phases'][p]['heldout_games']) for p in core.PHASES]==[2,1,1]
    assert len(data['costs']['excluded_games'])==2
    assert all(g['reason']=='MIXED_PHASE' for g in data['costs']['excluded_games'])
    assert data['costs']['excluded_tail']['raw_tiles']==9
    assert data['costs']['reused_carrier_raw_tiles']==3*block
    assert data['costs']['new_environment_raw_tiles']==0
    for phase in data['phases'].values():
        assert phase['fit_games'][-1]['metadata']['end_raw']<=phase['heldout_games'][0]['metadata']['start_raw']
        for game in phase['fit_games']+phase['heldout_games']:
            assert game['afterstates'].dtype==np.int32 and game['rewards'].dtype==np.float64
            assert game['terminal_code']==-1
            assert game['model_p_four'].tolist()==[p for _,p in facts[game['metadata']['episode']]]


def test_anchors_use_first_heldout_game_fixed_positions_and_actual_before_action_context(monkeypatch, tmp_path):
    rows, expected, facts, _=fixture(monkeypatch)
    data=load(tmp_path, rows, expected)
    for phase in data['phases'].values():
        game=phase['heldout_games'][0]; n=len(game['rewards'])
        assert [a['step'] for a in phase['anchors']]==[int((n-1)*q) for q in (.25,.5,.75)]
        for anchor in phase['anchors']:
            assert anchor['episode']==game['metadata']['episode']
            board,p=facts[anchor['episode']][anchor['step']]
            assert anchor['board_before_action']==list(board) and anchor['model_p_four']==p


def test_validation_labels_never_enter_dataset_or_choose_fit(monkeypatch, tmp_path):
    rows, expected, _, _=fixture(monkeypatch)
    baseline=load(tmp_path, rows, expected)
    rows[-1]['outcome_label']=-999999
    changed=load(tmp_path, rows, expected)
    for phase in core.PHASES:
        assert baseline['phases'][phase]['anchors']==changed['phases'][phase]['anchors']
        for a,b in zip(baseline['phases'][phase]['fit_games'], changed['phases'][phase]['fit_games']):
            assert np.array_equal(a['afterstates'], b['afterstates']) and np.array_equal(a['rewards'], b['rewards'])


def test_after_spawn_probability_cannot_replace_recorded_before_action_probability(monkeypatch, tmp_path):
    rows, expected, _, _=fixture(monkeypatch)
    chunk=next(r for r in rows if r['kind']=='CARRIER_TRAIN')
    chunk['model_p_four']+=.01
    with pytest.raises(ValueError, match='preceding observed raw prefix'):
        load(tmp_path, rows, expected)
