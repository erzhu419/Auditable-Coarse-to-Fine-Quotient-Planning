"""Filtered factual replay and outcome-independent complete-state probes."""
from copy import deepcopy
import gzip
import json
import random

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import retention_facts_v318 as facts


def recorded_round():
    """Record real standard swipes/spawns, natural terminals and a paid tail."""
    rng = random.Random(31801)
    state = dict(board=[0]*16, pending_afterstate=None, pending_bank_id=None,
        episode=-1, step=0, return_score=0, status='NOT_STARTED', initial_count=0,
        raw_tiles=0, post_action_spawns=0, game_start_raw=0,
        stream_seed=317500000000, random_draw_position=0)
    events, boards, postboards, scores, ends, games = [], [], [], [], [], []
    before_stream = deepcopy(state)

    def spawn(kind, board, action=None, score=None):
        before = deepcopy(state)
        if kind == 'INITIAL' and state['status'] != 'INITIALIZING':
            state.update(episode=state['episode']+1, step=0, return_score=0,
                status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'],
                pending_afterstate=None, pending_bank_id=None)
        cell = rng.choice([i for i, rank in enumerate(board) if rank == 0])
        rank = 1 if rng.random() < .9 else 2
        raw = dict(kind=kind, episode=state['episode'], cell=cell, rank=rank)
        observed = list(board); observed[cell] = rank
        if kind == 'INITIAL':
            state['initial_count'] += 1
            if state['initial_count'] == 2:
                state['status'] = ground.state_from_board_v1(tuple(observed)).status.value
        else:
            boards.append(board); postboards.append(tuple(observed)); scores.append(score)
            state['step'] += 1; state['return_score'] += score; state['post_action_spawns'] += 1
            state['pending_afterstate'] = list(board) if max(board) < 11 else None
            state['pending_bank_id'] = 0 if max(board) < 11 else None
            state['status'] = ground.state_from_board_v1(tuple(observed)).status.value
        state['board'] = observed
        state['raw_tiles'] += 1; state['random_draw_position'] += 2
        complete = None
        if state['status'] in ('WON', 'LOST'):
            state['pending_afterstate'] = state['pending_bank_id'] = None
            complete = dict(episode=state['episode'], stream_seed=state['stream_seed'],
                start_raw=state['game_start_raw'], end_raw=state['raw_tiles'],
                steps=state['step'], score=state['return_score'], status=state['status'])
            games.append(complete); ends.append(len(boards))
        events.append(dict(raw=raw, before=before, after=deepcopy(state),
            action=action, score=score, complete=complete))
        return tuple(observed)

    for game in range(4):
        board = spawn('INITIAL', (0,)*16)
        board = spawn('INITIAL', board)
        while state['status'] == 'ACTIVE':
            action = ground.legal_actions_v1(board)[0]
            after, score, _ = ground.swipe_board_v1(board, action)
            board = spawn('POST_ACTION', after, action.value, score)
            if game == 3 and state['step'] == 2:
                break
    rows = []
    for start in range(0, len(events), 64):
        chunk = events[start:start+64]
        rows.append(dict(kind='TRAIN', start=chunk[0]['before'], end=chunk[-1]['after'],
            raw_spawns=[event['raw'] for event in chunk],
            actions=[event['action'] for event in chunk if event['action'] is not None],
            scores=[event['score'] for event in chunk if event['score'] is not None],
            completed_games=[event['complete'] for event in chunk if event['complete'] is not None],
            bank_update_counts={}, td_examples=[], counts=dict(learning={})))
    training = dict(before_stream=before_stream, after_stream=deepcopy(state),
        raw_tiles=len(events), chunks=len(rows), counts=dict(environment={'raw_tiles':len(events)},
            planning={}, learning={}))
    complete = ends[-1]
    expected = dict(afterstates=np.asarray(boards[:complete], np.int32),
        postspawn_boards=np.asarray(postboards[:complete], np.int32),
        rewards=np.asarray(scores[:complete], np.float64)/2048., ends=np.asarray(ends),
        terminal_codes=np.asarray([1 if game['status']=='WON' else -1 for game in games]),
        games=[dict(game, split='FIT' if i < 2 else 'HELDOUT') for i,game in enumerate(games)],
        fit_step_end=ends[1], tail_steps=len(boards)-complete,
        tail_raw=len(events)-games[-1]['end_raw'])
    return rows, training, expected


@pytest.fixture
def retained_document(tmp_path):
    original, training, expected = recorded_round()
    lives, receipts, written = [], [], {}
    for parent in range(4):
        rows = []
        for life in range(parent, 16, 4):
            life_row = dict(lifecycle=life, parent=parent, rounds={})
            # These deliberately have no valid physics payload. They must only be parsed.
            rows.append(dict(kind='TRAIN', lifecycle=life, parent=parent, phase='A0',
                task='A', arm='SOURCE', raw_spawns=[{}, {}]))
            for number in ('1', '2'):
                life_row['rounds'][number] = dict(A=dict(collectors=dict(FIXED_FIRST=dict(
                    acquisition=dict(training=training)))))
                rows.extend(dict(deepcopy(row), lifecycle=life, parent=parent, task='A',
                    arm='FIXED_FIRST', phase=f'A_R{number}', batch_id=f'A_R{number}') for row in original)
                rows.append(dict(kind='TRAIN', lifecycle=life, parent=parent,
                    task='B', arm='FIXED_FIRST', phase=f'B_R{number}',
                    batch_id=f'B_R{number}', raw_spawns=[{}, {}]))
            lives.append(life_row)
        rows.append(dict(kind='PARENT_END', paid_tail='parse and charge this last row'))
        path = tmp_path/f'parent_{parent}.jsonl.gz'
        encoded = [json.dumps(row, separators=(',', ':')).encode()+b'\n' for row in rows]
        with gzip.open(path, 'wb') as stream:
            stream.writelines(encoded)
        receipts.append(dict(parent=parent, trace_file=str(path)))
        written[parent] = dict(rows=rows, bytes=sum(map(len, encoded)),
            compressed_bytes=path.stat().st_size,
            selected_bytes=sum(len(line) for row,line in zip(rows,encoded)
                if row.get('phase') in ('A_R1', 'A_R2')))
    return dict(by_lifecycle=lives, parent_receipts=receipts), expected, written


def test_one_parent_reconstructs_exact_complete_facts_and_does_not_preload_next_life(retained_document, monkeypatch):
    document, expected, written = retained_document
    consumed, finished = [], []
    original = facts.FixedPolicyData
    class CountedData(original):
        def consume(self, row):
            consumed.append((row['lifecycle'], row['task'], row['phase']))
            return super().consume(row)
        def finish(self, training):
            finished.append(training)
            return super().finish(training)
    monkeypatch.setattr(facts, 'FixedPolicyData', CountedData)
    iterator = facts.iter_a_lifecycles(document, 0)
    receipts = []
    for life in (0, 4, 8, 12):
        life_row, datasets, receipt = next(iterator)
        assert life_row is next(row for row in document['by_lifecycle'] if row['lifecycle']==life)
        assert set(datasets) == {'1', '2'}
        assert {row[0] for row in consumed} == set(range(0, life+1, 4))
        for number,data in datasets.items():
            for key in ('afterstates', 'postspawn_boards', 'rewards', 'ends', 'terminal_codes'):
                np.testing.assert_array_equal(data[key], expected[key])
            assert data['games'] == expected['games']
            assert data['fit_step_end'] == expected['fit_step_end']
            assert data['costs']['excluded_tail_steps'] == expected['tail_steps'] == 2
            assert data['costs']['excluded_tail_raw_tiles'] == expected['tail_raw'] == 4
            assert data['costs']['fit_raw_tiles']+data['costs']['heldout_raw_tiles']+expected['tail_raw'] == data['costs']['full_batch_raw_tiles']
            assert data['batch_id'] == f'A_R{number}'
            assert 'full_A_raw_tiles' not in data['costs']
        receipts.append(receipt)
    with pytest.raises(StopIteration):
        next(iterator)
    assert len(finished) == 8
    assert all(task=='A' and phase in ('A_R1', 'A_R2') for _,task,phase in consumed)
    assert sum(row['parsed_records'] for row in receipts) == len(written[0]['rows'])
    assert sum(row['parsed_bytes'] for row in receipts) == written[0]['bytes']
    assert sum(row['selected_training_bytes'] for row in receipts) == written[0]['selected_bytes']
    assert sum(row['compressed_bytes_read'] for row in receipts) == written[0]['compressed_bytes']
    assert sum(row.get('trace_files_read', 0) for row in receipts) == 1
    assert all(row['cpu_seconds'] >= row['reconstruction_cpu_seconds'] >= 0 for row in receipts)


def test_all16_are_streamed_with_one_read_per_parent_and_old_raw_is_not_new_acquisition(retained_document, monkeypatch):
    document, _, written = retained_document
    opened = []
    original = facts.gzip.GzipFile
    def counted_open(*args, **kwargs):
        opened.append(kwargs['fileobj'].name)
        return original(*args, **kwargs)
    monkeypatch.setattr(facts.gzip, 'GzipFile', counted_open)
    ids, receipts = [], []
    for life_row, datasets, receipt in facts.extract_a_rounds(document):
        ids.append(life_row['lifecycle']); receipts.append(receipt)
        assert receipt['reconstructed_raw_tiles'] == sum(data['costs']['full_batch_raw_tiles'] for data in datasets.values())
        assert receipt['new_raw_tiles'] == 0
    assert sorted(ids) == list(range(16)) and len(opened) == len(set(opened)) == 4
    assert sum(row['parsed_records'] for row in receipts) == sum(len(row['rows']) for row in written.values())
    assert sum(row['parsed_raw_tiles']-row['reconstructed_raw_tiles'] for row in receipts) == 16*6


def test_reader_cost_excludes_caller_cpu_between_lifecycle_yields(retained_document, monkeypatch):
    document, _, _ = retained_document
    ticks = iter((0., 2., 100., 103., 200., 204., 300., 305.))
    monkeypatch.setattr(facts, 'process_time', lambda: next(ticks))
    receipts = [receipt for _,_,receipt in facts.iter_a_lifecycles(document, 0)]
    assert [row['cpu_seconds'] for row in receipts] == [2., 3., 4., 5.]


@pytest.mark.parametrize('missing', ['lifecycle', 'round', 'first_chunk'])
def test_missing_planned_facts_stop_instead_of_silently_reducing_the_cohort(retained_document, missing):
    document, _, written = retained_document
    if missing == 'lifecycle':
        document['by_lifecycle'] = [row for row in document['by_lifecycle'] if row['lifecycle'] != 12]
        message = 'all four retained lifecycles'
    else:
        rows = written[0]['rows']
        selected = [i for i,row in enumerate(rows) if row.get('lifecycle')==0 and row.get('phase')=='A_R2']
        assert len(selected) > 1
        removed = set(selected if missing=='round' else selected[:1])
        path = document['parent_receipts'][0]['trace_file']
        with gzip.open(path, 'wt') as stream:
            for i,row in enumerate(rows):
                if i not in removed:
                    stream.write(json.dumps(row)+'\n')
        message = 'complete round' if missing=='round' else 'initial chunk'
    with pytest.raises(ValueError, match=message):
        next(facts.iter_a_lifecycles(document, 0))


def test_positions_are_spaced_over_nonwinning_complete_fit_and_heldout_only():
    boards = np.ones((215, 16), np.int32)
    winning = [0, 50, 99, 100, 150, 199]
    boards[winning, 0] = 11
    data = dict(afterstates=boards, ends=np.array([100, 200]), fit_step_end=100,
        rewards=np.arange(215), terminal_codes=np.array([-1, 1]))
    fit, heldout = facts.sample_indices(data, 'FIT'), facts.sample_indices(data, 'HELDOUT')
    assert len(fit) == len(heldout) == 64
    assert (fit[0],fit[-1],heldout[0],heldout[-1]) == (1,98,101,198)
    for sample,start,stop in ((fit,0,100), (heldout,100,200)):
        assert sample == sorted(set(sample))
        assert all(start <= i < stop and max(boards[i]) < 11 for i in sample)
        eligible = [i for i in range(start,stop) if i not in winning]
        positions = [eligible.index(i) for i in sample]
        assert set(np.diff(positions)) == {1, 2}
    data['rewards'] = -data['rewards']; data['terminal_codes'] *= -1
    assert facts.sample_indices(data, 'FIT') == fit
    assert facts.sample_indices(data, 'HELDOUT') == heldout
    assert all(type(index) is int for index in fit+heldout)


def test_small_eligible_split_returns_each_position_once_and_empty_support_stays_empty():
    boards = np.ones((8,16), np.int32); boards[[1,4,6],0] = 11
    data = dict(afterstates=boards, ends=np.array([4,7]), fit_step_end=4)
    assert facts.sample_indices(data, 'FIT') == [0,2,3]
    assert facts.sample_indices(data, 'HELDOUT') == [5]
    boards[5,0] = 11
    assert facts.sample_indices(data, 'HELDOUT') == []
