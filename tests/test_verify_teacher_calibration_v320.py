"""Finite terminal-label and paid continuation provenance failures for V320."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_teacher_calibration_v320 as audit


def fixture(kind=2, max_steps=1):
    root = ([2, 2]+[0]*14) if kind == 2 else ([1]+[0]*15)
    cells = np.full((1, 4), 15, dtype=np.int32); ranks = np.ones((1, 4), dtype=np.int32)
    actions = np.ones((1, 4), dtype=np.int32); kinds = np.full((1, 4), kind, dtype=np.int32)
    seeds = np.asarray([[320031+i for i in range(4)]], dtype=np.uint64)
    rows = []; final = []; scores = []
    for member in range(4):
        board = list(root); board[15] = 1
        after, score = audit.swipe(board, 'LEFT'); rng = audit.TileRandom(int(seeds[0, member]))
        empty = [i for i, x in enumerate(after) if not x]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        after[cell] = rank; status = audit._status_code(after, 3)
        rows.append([0, member, 1, 1, score, cell, rank, status]); final.append(after); scores.append(score)
    outcomes = dict(scores=np.asarray([scores], dtype=np.int64), actions=np.ones((1, 4), dtype=np.int64),
        new_raw_tiles=np.ones((1, 4), dtype=np.int64), status=np.full((1, 4), 1 if kind == 2 else 0, dtype=np.int32),
        final_boards=np.asarray([final], dtype=np.int32))
    return dict(moves=np.asarray(rows, dtype=np.int32), roots=np.asarray([root], dtype=np.int32),
        cells=cells, ranks=ranks, selected_action=actions, targetkind=kinds, seeds=seeds,
        outcomes=outcomes, probability=.1, max_steps=max_steps, radix=3)


def test_frozen_indices_span_entire_original_batch_and_pair_exact_member_seeds():
    selected = audit.selected_groups()
    assert len(selected) == 64 and selected[0] == 0 and selected[-1] == 16383
    assert np.all(np.diff(selected) > 0)
    assert audit.continuation_seed(15, 'B', 2, 16383, 3) == 320651265535


def test_prescribed_direct_win_still_produces_paid_spawn_and_excludes_root_action_reward():
    reward, win, counts, probes = audit.check_continuations(**fixture())
    assert np.all(reward == 8./2048.) and np.all(win == 1.)
    assert counts['new_raw_tiles'] == 4 and counts['new_random_draws'] == 8
    assert counts['prescribed_direct_actions'] == 4 and counts['followup_h2_actions'] == 0
    assert all(value['first_h2_decision'] is None for value in probes.values())


def test_initial_saved_postspawn_lost_has_no_new_action_or_free_relabelled_spawn():
    value = fixture()
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    root = lost.copy(); root[15] = 0
    value.update(moves=np.empty((0, 8), dtype=np.int32), roots=np.asarray([root], dtype=np.int32),
        selected_action=np.full((1, 4), -1, dtype=np.int32), targetkind=np.full((1, 4), 3, dtype=np.int32),
        outcomes=dict(scores=np.zeros((1, 4), dtype=np.int64), actions=np.zeros((1, 4), dtype=np.int64),
            new_raw_tiles=np.zeros((1, 4), dtype=np.int64), status=np.full((1, 4), -1, dtype=np.int32),
            final_boards=np.asarray([[lost]*4], dtype=np.int32)))
    reward, win, counts, _ = audit.check_continuations(**value)
    assert not np.any(reward) and not np.any(win) and counts['lost'] == 4 and counts['new_raw_tiles'] == 0


def test_active_full_horizon_retains_cutoff_status_instead_of_terminal_win_label():
    _, win, counts, _ = audit.check_continuations(**fixture(kind=1))
    assert counts['cutoffs'] == 4 and np.all(np.isnan(win))
    value = fixture(kind=1); value['outcomes']['status'][0, 0] = -1
    with pytest.raises(ValueError, match='natural status'):
        audit.check_continuations(**value)


@pytest.mark.parametrize('field,column,match', [
    ('trace', 4, 'exact ground merge score'), ('trace', 5, 'exact seeded cell/rank'),
    ('trace', 7, 'post-spawn status'), ('trace', 2, '1-based action numbering'),
    ('outcome', 'new_raw_tiles', 'complete replayed score'), ('outcome', 'scores', 'complete replayed score')])
def test_fabricated_physics_or_cost_member_is_rejected(field, column, match):
    value = fixture()
    if field == 'trace': value['moves'][0, column] += 1
    else: value['outcomes'][column][0, 0] += 1
    with pytest.raises(ValueError, match=match): audit.check_continuations(**value)


def test_saved_target_branch_cannot_be_replaced_by_fresh_teacher_choice():
    value = fixture(); value['selected_action'][0, 0] = 2
    with pytest.raises(ValueError, match='actual saved target branch'): audit.check_continuations(**value)


def test_chronological_trace_cannot_omit_a_member_or_move_after_terminal():
    value = fixture(); value['moves'] = value['moves'][1:]
    with pytest.raises(ValueError, match='omitted tail'): audit.check_continuations(**value)
    value = fixture(); value['moves'] = np.insert(value['moves'], 1, value['moves'][0], axis=0)
    with pytest.raises(ValueError, match='after natural termination'): audit.check_continuations(**value)


def test_direct_only_boundary_probe_must_be_null_and_all_members_retained():
    _, _, _, expected = audit.check_continuations(**fixture())
    probes = [dict(root_local_index=g, member=m, **row) for (g, m), row in expected.items()]
    teacher = SimpleNamespace(reward=np.zeros(4*3**6), terminal=np.zeros(4*3**6))
    assert audit.check_probes(probes, expected, teacher, .1, 3) == 0
    corrupt = deepcopy(probes); corrupt[0]['first_h2_decision'] = {'step': 2}
    with pytest.raises(ValueError, match='invented followup'): audit.check_probes(corrupt, expected, teacher, .1, 3)
    with pytest.raises(ValueError, match='boundary probes'): audit.check_probes(probes[:-1], expected, teacher, .1, 3)


def test_new_native_terminal_tape_counts_and_actual_teacher_probes_match_independent_reader():
    from test_native_teacher_calibration_v320 import fixture as native_fixture, BUILD, BOARD
    from acfqp.science.native_policy_stream_v313 import choose_direct
    from acfqp.science.native_teacher_calibration_v320 import continue_targets
    first = native_fixture(); roots = np.asarray([BOARD], dtype=np.int32)
    cells = np.full((1, 4), 15, dtype=np.int32); ranks = np.full((1, 4), 2, dtype=np.int32)
    post = list(BOARD); post[15] = 2
    action = audit.ACTIONS.index(choose_direct(first,post,BUILD)['action'])
    actions = np.full((1, 4), action, dtype=np.int32); kinds = np.ones((1, 4), dtype=np.int32)
    seeds = np.asarray([[320720010+i for i in range(4)]], dtype=np.uint64)
    result = continue_targets(first,roots,cells,ranks,actions,kinds,seeds,BUILD,BUILD/'independent_reader.npz',p_model=.375,p_true=.375)
    with np.load(result['trace_artifact']['file'],allow_pickle=False) as saved: moves = saved['moves']
    reward, win, counts, expected = audit.check_continuations(moves,roots,cells,ranks,actions,kinds,seeds,result,.375,radix=first.radix)
    assert not counts['cutoffs'] and np.allclose(result['reward_return'],reward) and np.array_equal(result['win'],win)
    audit.check_continuation_work(result,counts,result,{'updates':first.updates},.375,.375)
    teacher = SimpleNamespace(reward=first.reward_weights.reshape(-1),terminal=first.risk_weights.reshape(-1))
    assert audit.check_probes(result['boundary_probes'],expected,teacher,.375,first.radix) > 0


def analysis_fixture():
    rows = []
    for life in range(16):
        teacher = {'file':f'FIRST_{life}.npz'}; stages = {}; initial = {task:{'teacher_version':teacher} for task in audit.TASKS}
        for number in ('1','2'):
            stages[number] = {}
            for task in audit.TASKS:
                arms = {}
                for arm in audit.ARMS:
                    groups = []
                    for index in audit.selected_groups():
                        replicas = [dict(teacher_reward=1.25+(.25 if arm=='QUERY_LOCAL' else 0.),teacher_win=.5,
                            actual_reward=1.,actual_win=0,status='LOST',score=2048,actions=2,new_raw_tiles=2,
                            seed=audit.continuation_seed(life,task,int(number),int(index),member)) for member in range(4)]
                        groups.append(dict(index=int(index),replicas=replicas))
                    arms[arm] = dict(groups=groups)
                stages[number][task] = dict(teacher_version=teacher,teacher_unchanged=True,groups=64,replicas=4,
                    selected_group_indices=audit.selected_groups().tolist(),arms=arms)
        rows.append(dict(lifecycle=life,parent=life%4,initial=initial,stages=stages))
    return rows


def test_frozen_reader_configuration_agrees_with_driver_before_acquisition():
    from acfqp.science.teacher_calibration_run_v320 import configuration
    source = Path(__file__).resolve().parents[1]/'reports/query_supervision_v319/summary.json'
    assert configuration(source) == audit.expected_configuration(source)


def test_full_production_analysis_and_independent_moments_and_signed_primary_agree():
    from acfqp.science.teacher_calibration_analysis_v320 import summarize
    rows = analysis_fixture(); result = summarize(rows)
    audit.check_analysis(result,rows)
    assert result['primary_status'] == 'SUPPORTED_MORE_OPTIMISTIC' and result['primary']['mean'] == .25
    corrupt = deepcopy(result); corrupt['primary_status'] = 'SUPPORTED_GAIN'
    with pytest.raises(ValueError,match='diagnostic as learning'): audit.check_analysis(corrupt,rows)
    corrupt = deepcopy(result); corrupt['by_lifecycle'][0]['cells']['R1_A']['QUERY_LOCAL']['signed_error']['combined'] += .1
    with pytest.raises(ValueError,match='actual terminal data'): audit.check_analysis(corrupt,rows)


def test_global_cutoff_hold_analysis_matches_independent_no_imputed_truth():
    from acfqp.science.teacher_calibration_analysis_v320 import summarize
    rows = analysis_fixture(); x = rows[3]['stages']['2']['B']['arms']['QUERY_LOCAL']['groups'][1]['replicas'][2]
    x.update(status='CUTOFF',actual_reward=None,actual_win=None,actions=8192,new_raw_tiles=8192)
    result = summarize(rows); audit.check_analysis(result,rows)
    corrupt = deepcopy(result); corrupt['overall'] = {}
    with pytest.raises(ValueError,match='suppresses all terminal-bias'): audit.check_analysis(corrupt,rows)
