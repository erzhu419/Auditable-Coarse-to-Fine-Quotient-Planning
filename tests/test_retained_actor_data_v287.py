"""Deterministic legal swipe fixtures, without sampling an environment."""
from collections import Counter
from copy import deepcopy
from functools import lru_cache
import gzip
import json

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import retained_actor_data_v287 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory


@lru_cache(maxsize=1)
def game_events():
    board = (2,)+(0,)*14+(2,)
    events = [(dict(kind='INITIAL', cell=0, rank=2), None, None),
              (dict(kind='INITIAL', cell=15, rank=2), None, None)]
    for _ in range(512):
        choices = [(score, action.value, after) for action in ground.ACTION_ORDER
            for after, score, changed in [ground.swipe_board_v1(board, action)] if changed]
        if not choices:
            break
        score, action, after = min(choices)
        cell = next(i for i, rank in enumerate(after) if rank == 0)
        events.append((dict(kind='POST_ACTION', cell=cell, rank=2), action, score))
        board = list(after)
        board[cell] = 2
        board = tuple(board)
        if ground.state_from_board_v1(board).status.value != 'ACTIVE':
            break
    assert ground.state_from_board_v1(board).status.value == 'LOST'
    return events, board


def fixture():
    events, final = game_events()
    rows, memory, acquired = [], SpawnMemory('LIBRARY'), Counter()
    while memory.observations_seen < 256:
        raw = [dict(spawn) for spawn, _, _ in events]
        actions = [action for _, action, _ in events if action is not None]
        scores = [score for _, action, score in events if action is not None]
        for spawn in raw:
            memory.observe(spawn['rank'])
        rows.append(dict(kind='WARMUP', lifecycle=0, raw_spawns=raw, actions=actions,
            scores=scores, summary=dict(seed=len(rows), steps=len(actions), score=sum(scores),
                status='LOST'), final_board=list(final)))
    warm_raw, warm_memory = memory.observations_seen, memory.to_payload()
    state = dict(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
        episode=-1, step=0, return_score=0, status='NOT_STARTED', initial_count=0,
        raw_tiles=0, post_action_spawns=0, game_start_raw=0,
        stream_seed=286200000000, random_draw_position=0)
    before = deepcopy(state)
    sequence = [(episode, event) for episode in range(8) for event in events]
    sequence.extend((8, event) for event in events[:5])
    cursor = 0
    while cursor < len(sequence):
        start, module, p = deepcopy(state), memory.module_id, memory.predict()
        chunk = sequence[cursor:cursor+64-memory.pending_n]
        cursor += len(chunk)
        raw, actions, scores, completions, memory_events = [], [], [], [], []
        for episode, (spawn, action, score) in chunk:
            spawn = dict(spawn, episode=episode)
            raw.append(spawn)
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    state.update(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
                        episode=episode, step=0, return_score=0, status='INITIALIZING',
                        initial_count=0, game_start_raw=state['raw_tiles'])
                state['initial_count'] += 1
                state['board'][spawn['cell']] = spawn['rank']
                if state['initial_count'] == 2:
                    state['status'] = 'ACTIVE'
            else:
                after, actual, changed = ground.swipe_board_v1(tuple(state['board']),
                    ground.Swipe2048Action(action))
                assert changed and score == actual
                actions.append(action)
                scores.append(score)
                state['board'] = list(after)
                state['board'][spawn['cell']] = spawn['rank']
                state['step'] += 1
                state['return_score'] += score
                state['post_action_spawns'] += 1
                state['status'] = ground.state_from_board_v1(tuple(state['board'])).status.value
                state['pending_afterstate'] = list(after) if state['status'] == 'ACTIVE' else None
                state['pending_bank_id'] = 0 if state['status'] == 'ACTIVE' else None
            state['raw_tiles'] += 1
            state['random_draw_position'] += 2
            event = memory.observe(spawn['rank'])
            if event is not None:
                memory_events.append(event)
            if state['status'] == 'LOST':
                completions.append(dict(episode=episode, stream_seed=state['stream_seed'],
                    start_raw=state['game_start_raw'], end_raw=state['raw_tiles'],
                    steps=state['step'], score=state['return_score'], status='LOST'))
        counts = dict(raw_tile_productions=len(raw), environment_random_draws=2*len(raw),
            initial_spawns=sum(spawn['kind'] == 'INITIAL' for spawn in raw),
            post_action_spawns=len(actions), sampled_transitions=len(actions))
        acquired.update(counts)
        rows.append(dict(kind='TRAIN', lifecycle=0, arm='FROZEN', phase='A',
            active_bank_id=0, module_id_before=module, model_p_four=p,
            start=start, end=deepcopy(state), raw_spawns=raw, actions=actions, scores=scores,
            completed_games=completions, memory_events=memory_events,
            counts=dict(environment=counts, planning={}, learning={})))
    snapshot = dict(stream=deepcopy(state), memory=core._memory_state(memory),
        estimated_p_four=memory.predict(), active_bank_id=0)
    rows.append(dict(kind='EVALUATION', lifecycle=0, arm='FROZEN', phase='A', snapshot=snapshot))
    # A future completion must never supply a label for the excluded last A game.
    rows.append(dict(kind='TRAIN', lifecycle=0, arm='FROZEN', phase='B',
        raw_spawns=[dict(rank=2, cell=0)], actions=['LEFT'], scores=[999999],
        completed_games=[dict(episode=8, status='WON', score=999999)]))
    expected = dict(lifecycle=0, parent=0, warmup=dict(raw_tiles=warm_raw,
        environment_counts=dict(initial_spawns=4, sampled_transitions=warm_raw-4),
        direct_counts={}, memory_counts=warm_memory['counts']), arms=dict(FROZEN=dict(phases=dict(A=dict(
        training=dict(before_stream=before, after_stream=deepcopy(state), raw_tiles=state['raw_tiles'],
            counts=dict(environment=dict(acquired), planning={}, learning={})), snapshot=snapshot)))))
    return rows, {0: expected}, events, warm_memory


def write_trace(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row)+'\n')


def load(tmp_path, rows, expected):
    path = tmp_path/'trace.jsonl.gz'
    write_trace(path, rows)
    return core.load_retained_parent(path, [0], expected)[0]


def test_complete_A_only_chronological_split_and_fit_memory_excludes_holdout(tmp_path):
    rows, expected, events, warm_memory = fixture()
    data = load(tmp_path, rows, expected)
    steps = len(events)-2
    assert data['afterstates'].shape == (8*steps, 16)
    assert data['afterstates'].dtype == np.int32 and data['rewards'].dtype == np.float64
    assert data['ends'].dtype == np.int64 and data['terminal_codes'].dtype == np.int32
    assert data['ends'].tolist() == [steps*k for k in range(1, 9)]
    assert data['terminal_codes'].tolist() == [-1]*8
    assert data['fit_game_count'] == 6 and data['fit_step_end'] == 6*steps
    assert [game['split'] for game in data['games']] == ['FIT']*6+['HELDOUT']*2
    assert data['fit_end_raw'] == 6*len(events)
    direct_prefix = SpawnMemory.from_payload(warm_memory)
    for _ in range(6):
        for spawn, _, _ in events:
            direct_prefix.observe(spawn['rank'])
    assert core._memory_state(SpawnMemory.from_payload(data['fit_memory'])) == core._memory_state(direct_prefix)
    assert data['fit_memory']['observations_seen'] < data['actor_memory_A_end']['observations_seen']
    assert data['costs']['excluded_tail_games'] == 1
    assert data['costs']['excluded_tail_steps'] == 3 and data['costs']['excluded_tail_raw_tiles'] == 5
    assert data['costs']['full_A_raw_tiles'] == 8*len(events)+5
    assert data['costs']['warmup_raw_tiles'] == warm_memory['observations_seen']


def test_future_B_rewards_and_holdout_outcomes_do_not_choose_fit_boundary(tmp_path):
    rows, expected, _, _ = fixture()
    data = load(tmp_path, rows, expected)
    rows[-1]['completed_games'][0]['score'] = -999999999
    rows[-1]['completed_games'][0]['status'] = 'LOST'
    rows[-1]['raw_spawns'] = []
    future_changed = load(tmp_path, rows, expected)
    assert data['fit_end_raw'] == future_changed['fit_end_raw']
    assert data['fit_memory'] == future_changed['fit_memory']
    assert np.array_equal(data['afterstates'], future_changed['afterstates'])
    assert np.array_equal(data['rewards'], future_changed['rewards'])


@pytest.mark.parametrize('corruption', ['chunk_start', 'score', 'initial_missing', 'completed_status'])
def test_reconstruction_detects_reachable_receipt_errors(tmp_path, corruption):
    rows, expected, _, _ = fixture()
    chunks = [row for row in rows if row['kind'] == 'TRAIN' and row['phase'] == 'A']
    if corruption == 'chunk_start':
        chunks[1]['start']['board'][0] += 1
    elif corruption == 'score':
        chunks[0]['scores'][0] += 4
    elif corruption == 'initial_missing':
        chunks[0]['raw_spawns'].pop(0)
    else:
        next(row for row in chunks if row['completed_games'])['completed_games'][0]['status'] = 'WON'
    with pytest.raises(ValueError):
        load(tmp_path, rows, expected)


def test_winning_action_afterstate_is_retained_with_its_current_reward():
    board = [10, 10]+[0]*14
    state = dict(board=board, pending_afterstate=None, pending_bank_id=None, episode=0,
        step=600, return_score=1000, status='ACTIVE', initial_count=2, raw_tiles=602,
        post_action_spawns=600, game_start_raw=0, stream_seed=7, random_draw_position=1204)
    after, score, changed = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action.LEFT)
    assert changed and score == 2048
    child = list(after)
    child[1] = 1
    end = dict(state, board=child, step=601, return_score=3048, status='WON',
        raw_tiles=603, post_action_spawns=601, random_draw_position=1206)
    replay = core._Replay(dict(arms=dict(FROZEN=dict(phases=dict(A=dict(training=dict(before_stream=state)))))))
    row = dict(start=state, end=end, module_id_before=0, model_p_four=.5, active_bank_id=0,
        actions=['LEFT'], scores=[score], raw_spawns=[dict(episode=0, kind='POST_ACTION', cell=1, rank=1)],
        completed_games=[dict(episode=0, stream_seed=7, start_raw=0, end_raw=603,
            steps=601, score=3048, status='WON')], memory_events=[],
        counts=dict(environment={}, planning={}, learning={}))
    replay.train(row)
    assert replay.afterstates == [after] and replay.scores == [2048] and replay.codes == [1]
