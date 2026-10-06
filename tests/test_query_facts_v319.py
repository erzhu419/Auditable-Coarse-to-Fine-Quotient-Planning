"""Four retained batches and same-game, complete-FIT planner anchors."""
from copy import deepcopy
import gzip
import json

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import query_facts_v319 as facts
from test_retention_facts_v318 import recorded_round


def transpose_board(board):
    return np.asarray(board).reshape(4,4).T.reshape(-1).tolist()


def transposed_round(rows, training, expected):
    rows, training, expected = deepcopy((rows, training, expected))
    actions = dict(LEFT='UP', RIGHT='DOWN', UP='LEFT', DOWN='RIGHT')
    for row in rows:
        for state in (row['start'], row['end']):
            state['board'] = transpose_board(state['board'])
            if state['pending_afterstate'] is not None:
                state['pending_afterstate'] = transpose_board(state['pending_afterstate'])
        for spawn in row['raw_spawns']:
            spawn['cell'] = 4*(spawn['cell']%4)+spawn['cell']//4
        row['actions'] = [actions[action] for action in row['actions']]
    for state in (training['before_stream'], training['after_stream']):
        state['board'] = transpose_board(state['board'])
        if state['pending_afterstate'] is not None:
            state['pending_afterstate'] = transpose_board(state['pending_afterstate'])
    for key in ('afterstates', 'postspawn_boards'):
        expected[key] = expected[key].reshape(-1,4,4).transpose(0,2,1).reshape(-1,16).copy()
    return rows, training, expected


@pytest.fixture
def retained_document(tmp_path):
    a = recorded_round()
    samples = dict(A=a, B=transposed_round(*a))
    lives, receipts, written = [], [], {}
    for parent in range(4):
        rows = []
        for life in range(parent,16,4):
            life_row = dict(lifecycle=life, parent=parent, rounds={'1':{}, '2':{}})
            for task in ('A', 'B'):
                # Initial/SOURCE physics is intentionally absent: it must not be replayed.
                rows.append(dict(kind='TRAIN', lifecycle=life, parent=parent, task=task,
                    arm='SOURCE', phase=task+'0', raw_spawns=[{}, {}]))
            for number in ('1', '2'):
                for task in ('A', 'B'):
                    recorded, training, _ = samples[task]
                    life_row['rounds'][number][task] = dict(collectors=dict(FIXED_FIRST=dict(
                        acquisition=dict(training=training))))
                    rows.extend(dict(deepcopy(row), lifecycle=life, parent=parent, task=task,
                        arm='FIXED_FIRST', phase=f'{task}_R{number}', batch_id=f'{task}_R{number}')
                        for row in recorded)
            lives.append(life_row)
        rows.append(dict(kind='PARENT_END', skipped_tail=True))
        encoded = [json.dumps(row, separators=(',', ':')).encode()+b'\n' for row in rows]
        path = tmp_path/f'parent_{parent}.jsonl.gz'
        with gzip.open(path, 'wb') as stream:
            stream.writelines(encoded)
        receipts.append(dict(parent=parent, trace_file=str(path)))
        written[parent] = dict(rows=rows, parsed_bytes=sum(map(len,encoded)),
            compressed_bytes=path.stat().st_size, selected_bytes=sum(len(line)
                for row,line in zip(rows,encoded) if row.get('phase') in facts.BATCHES))
    return dict(by_lifecycle=lives, parent_receipts=receipts), samples, written


def test_all16_four_batches_use_one_filtered_parent_pass_and_exact_task_facts(retained_document, monkeypatch):
    document, samples, written = retained_document
    consumed, opened, receipts, ids = [], [], [], []
    original_data, original_gzip = facts.FixedPolicyData, facts.gzip.GzipFile
    class CountedData(original_data):
        def consume(self, row):
            consumed.append((row['lifecycle'],row['task'],row['phase']))
            return super().consume(row)
    def counted_open(*args, **kwargs):
        opened.append(kwargs['fileobj'].name)
        return original_gzip(*args, **kwargs)
    monkeypatch.setattr(facts, 'FixedPolicyData', CountedData)
    monkeypatch.setattr(facts.gzip, 'GzipFile', counted_open)
    for parent in range(4):
        iterator = facts.iter_query_lifecycles(document,parent)
        for life in range(parent,16,4):
            life_row, datasets, receipt = next(iterator)
            assert life_row is next(row for row in document['by_lifecycle'] if row['lifecycle']==life)
            assert {value[0] for value in consumed if value[0]%4==parent} == set(range(parent,life+1,4))
            assert set(datasets) == {'1','2'}
            for number,tasks in datasets.items():
                assert set(tasks) == {'A','B'}
                for task,data in tasks.items():
                    expected = samples[task][2]
                    for key in ('afterstates','postspawn_boards','rewards','ends','terminal_codes'):
                        np.testing.assert_array_equal(data[key],expected[key])
                    assert data['games'] == expected['games']
                    assert data['batch_id'] == f'{task}_R{number}'
                    assert data['costs']['excluded_tail_steps'] == 2
                    assert data['costs']['excluded_tail_raw_tiles'] == 4
            assert receipt['reconstructed_raw_tiles'] == sum(data['costs']['full_batch_raw_tiles']
                for tasks in datasets.values() for data in tasks.values())
            assert receipt['new_raw_tiles'] == 0
            assert receipt['cpu_seconds'] >= receipt['reconstruction_cpu_seconds'] >= 0
            ids.append(life); receipts.append(receipt)
        with pytest.raises(StopIteration):
            next(iterator)
    assert sorted(ids) == list(range(16)) and len(opened) == len(set(opened)) == 4
    assert {phase for _,_,phase in consumed} == set(facts.BATCHES)
    assert all(phase.startswith(task+'_R') for _,task,phase in consumed)
    assert sum(row['parsed_records'] for row in receipts) == sum(len(row['rows']) for row in written.values())
    for field in ('parsed_bytes','selected_training_bytes','compressed_bytes_read'):
        key = dict(parsed_bytes='parsed_bytes',selected_training_bytes='selected_bytes',
            compressed_bytes_read='compressed_bytes')[field]
        assert sum(row[field] for row in receipts) == sum(row[key] for row in written.values())
    assert sum(row['parsed_raw_tiles']-row['reconstructed_raw_tiles'] for row in receipts) == 16*4


def test_actual_anchors_recover_first_action_preboard_without_crossing_natural_games(retained_document):
    _, samples, _ = retained_document
    for task in ('A','B'):
        expected = dict(samples[task][2], fit_game_count=2)
        result = facts.prepare_anchors(expected,groups=4)
        starts = {0,int(expected['ends'][0])}
        for index,preboard,root in zip(result['indices'],result['preboards'],result['natural_roots']):
            assert index not in starts and index < expected['fit_step_end']
            np.testing.assert_array_equal(preboard,expected['postspawn_boards'][index-1])
            np.testing.assert_array_equal(root,expected['afterstates'][index])
            board = tuple(map(int,preboard))
            assert any(ground.swipe_board_v1(board,action)[0] == tuple(map(int,root))
                for action in ground.legal_actions_v1(board))
        assert result['counts']['selected_anchors'] == 8
        assert result['counts']['excluded_game_first_nonwinning_states'] == 2


def boundary_dataset():
    afterstates = np.ones((40,16),np.int32)
    afterstates[:,0] = np.arange(40)%10+1
    afterstates[:,1] = np.arange(40)//10+1
    afterstates[[11,23],0] = 11
    postspawn = afterstates.copy(); postspawn[:,15] = 2
    return dict(afterstates=afterstates,postspawn_boards=postspawn,
        ends=np.array([12,24,36],np.int64),fit_game_count=2,fit_step_end=24)


def test_census_positions_exclude_fit_game_starts_wins_heldout_and_tail_before_model_queries():
    data = boundary_dataset()
    result = facts.prepare_anchors(data,groups=5)
    np.testing.assert_array_equal(result['indices'],[1,3,5,7,9,13,15,17,19,22])
    np.testing.assert_array_equal(result['preboards'],data['postspawn_boards'][result['indices']-1])
    np.testing.assert_array_equal(result['natural_roots'],data['afterstates'][result['indices']])
    assert result['indices'].dtype == np.int64
    assert result['preboards'].dtype == result['natural_roots'].dtype == np.int32
    assert all(result[key].flags.c_contiguous for key in ('indices','preboards','natural_roots'))
    assert result['counts']['eligible_anchors'] == 20
    assert result['counts']['excluded_winning_fit_states'] == 2
    assert result['counts']['excluded_game_first_nonwinning_states'] == 2
    assert result['counts']['index_array_bytes'] == 10*8
    assert result['counts']['preboard_array_bytes'] == result['counts']['natural_root_array_bytes'] == 10*16*4
    assert result['cpu_seconds'] >= 0 and result['seconds'] >= 0


def test_insufficient_complete_fit_census_stops_without_repeating_positions_or_using_suffix():
    data = boundary_dataset()
    with pytest.raises(ValueError,match='insufficient eligible complete FIT anchors'):
        facts.prepare_anchors(data,groups=11)


@pytest.mark.parametrize('failure', ['missing_B_R2','misregistered_task'])
def test_missing_or_misregistered_task_round_stops_the_planned_cohort(retained_document,failure):
    document,_,written = retained_document
    rows = deepcopy(written[0]['rows'])
    selected = [i for i,row in enumerate(rows) if row.get('lifecycle')==0 and row.get('phase')=='B_R2']
    if failure == 'missing_B_R2':
        rows = [row for i,row in enumerate(rows) if i not in selected]
        message = 'complete task-round batch'
    else:
        rows[selected[0]]['task'] = 'A'
        message = 'training tags changed'
    with gzip.open(document['parent_receipts'][0]['trace_file'],'wt') as stream:
        for row in rows:
            stream.write(json.dumps(row)+'\n')
    with pytest.raises(ValueError,match=message):
        next(facts.iter_query_lifecycles(document,0))
