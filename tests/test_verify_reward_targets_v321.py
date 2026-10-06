"""Reject real reward-target, unchanged-risk, physics and inference contract failures."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_reward_targets_v321 as audit


def fixture(kind=1):
    radix = 3; root = ([2,2]+[0]*14) if kind == 2 else ([1,1]+[0]*14)
    cells = np.full((1,4),15,dtype=np.int32); ranks = np.ones((1,4),dtype=np.int32)
    actions = np.ones((1,4),dtype=np.int32); kinds = np.full((1,4),kind,dtype=np.int32)
    teacher = SimpleNamespace(reward=np.full(4*radix**6,.2),terminal=np.zeros(4*radix**6))
    post = root.copy(); post[15] = 1; after,gained = audit.swipe(post,'LEFT'); tail = 6.4 if kind == 1 else 0.
    status = 0 if kind == 1 else 1; endpoint = 2 if kind == 1 else 1
    moves = np.asarray([[0,m,1,1,gained,-1,-1,status,endpoint] for m in range(4)],dtype=np.int32)
    shape = (1,4)
    outcomes = dict(scores=np.full(shape,gained,dtype=np.int64),actions=np.ones(shape,dtype=np.int64),
        new_raw_tiles=np.zeros(shape,dtype=np.int64),status=np.full(shape,status,dtype=np.int32),
        tail_reward=np.full(shape,tail,dtype=np.float64),target_reward=np.full(shape,gained/2048.+tail,dtype=np.float64),
        bootstrap_afterstates=np.asarray([[after if kind == 1 else [0]*16]*4],dtype=np.int32),
        final_boards=np.asarray([[after]*4],dtype=np.int32),last_preboards=np.asarray([[post]*4],dtype=np.int32),
        last_afterstates=np.asarray([[after]*4],dtype=np.int32))
    return dict(moves=moves,roots=np.asarray([root],dtype=np.int32),cells=cells,ranks=ranks,
        selected_action=actions,targetkind=kinds,seeds=np.asarray([[321001+m for m in range(4)]],dtype=np.uint64),
        outcomes=outcomes,teacher=teacher,probability=.1,horizon=1,radix=radix)


def test_live_horizon_reads_frozen_reward_afterstate_before_new_spawn_without_win_truth():
    value = fixture(); target,counts,_ = audit.check_nstep(**value)
    assert np.allclose(target,6.4+4/2048.)
    assert counts['new_raw_tiles'] == 0 and counts['bootstrapped'] == 4 and counts['actions'] == 4
    assert counts['won'] == counts['lost'] == 0


def test_analytic_win_keeps_direct_reward_and_zero_tail_or_unneeded_spawn():
    target,counts,probes = audit.check_nstep(**fixture(2))
    assert np.all(target == 8/2048.) and counts['won'] == 4 and counts['new_raw_tiles'] == 0
    assert all(p['first_h2_decision'] is None for p in probes.values())


def test_saved_initial_lost_has_no_action_and_preserves_actual_paid_board():
    value = fixture(); board = [1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1]; root = board.copy(); root[15] = 0
    value.update(moves=np.empty((0,9),dtype=np.int32),roots=np.asarray([root],dtype=np.int32),
        selected_action=np.full((1,4),-1,dtype=np.int32),targetkind=np.full((1,4),3,dtype=np.int32))
    for field in ('scores','actions','new_raw_tiles'): value['outcomes'][field][:] = 0
    for field in ('tail_reward','target_reward'): value['outcomes'][field][:] = 0.
    value['outcomes']['status'][:] = -1; value['outcomes']['bootstrap_afterstates'][:] = 0
    for field in ('final_boards','last_preboards','last_afterstates'): value['outcomes'][field][:] = board
    target,counts,_ = audit.check_nstep(**value)
    assert not np.any(target) and counts['lost'] == 4 and counts['actions'] == 0


@pytest.mark.parametrize('field', ['tail_reward','target_reward','scores','new_raw_tiles','bootstrap_afterstates'])
def test_changed_target_bootstrap_or_physical_cost_is_rejected(field):
    value = fixture(); value['outcomes'][field].flat[0] += 1
    with pytest.raises(ValueError): audit.check_nstep(**value)


def test_last_spawn_cannot_be_invented_and_saved_direct_cannot_be_reselected():
    value = fixture(); value['moves'][0,5] = 3
    with pytest.raises(ValueError,match='before the final spawn'): audit.check_nstep(**value)
    value = fixture(); value['selected_action'][0,0] = 0
    with pytest.raises(ValueError,match='cannot be reselected'): audit.check_nstep(**value)


def test_missing_or_extra_members_cannot_hide_natural_or_bootstrap_endpoint():
    value = fixture(); value['moves'] = value['moves'][1:]
    with pytest.raises(ValueError,match='full prescribed horizon'): audit.check_nstep(**value)
    value = fixture(2); value['moves'] = np.insert(value['moves'],1,value['moves'][0],axis=0)
    with pytest.raises(ValueError,match='follows a natural'): audit.check_nstep(**value)


def test_actual_native_h4_physics_rng_and_first_reward_tail_match_literal_reader():
    from test_native_reward_targets_v321 import fixture as native_fixture,BUILD,BOARD,run,trace
    from acfqp.science.native_policy_stream_v313 import choose_direct
    first = native_fixture(); post = list(BOARD); post[15] = 2
    selected = audit.ACTIONS.index(choose_direct(first,post,BUILD)['action'])
    roots = np.asarray([BOARD],dtype=np.int32); cells = np.full((1,4),15,dtype=np.int32)
    ranks = np.full((1,4),2,dtype=np.int32); actions = np.full((1,4),selected,dtype=np.int32)
    kinds = np.ones((1,4),dtype=np.int32); seeds = np.arange(321070000,321070004,dtype=np.uint64).reshape(1,4)
    result = run(first,roots,cells,ranks,actions,kinds,seeds,'independent_reader')
    teacher = SimpleNamespace(reward=first.reward_weights.reshape(-1),terminal=first.risk_weights.reshape(-1))
    target,counts,probes = audit.check_nstep(trace(result),roots,cells,ranks,actions,kinds,seeds,result,teacher,.375,radix=first.radix)
    assert np.allclose(target,result['target_reward']) and counts['new_raw_tiles'] == 12
    audit.check_acquisition_work(result,counts,result,{'updates':first.updates},.375,.375)
    assert audit.check_probes(result['boundary_probes'],probes,teacher,.375,first.radix) == 8
    bad_moves = trace(result).copy(); bad_moves[0,6] = 3-bad_moves[0,6]
    with pytest.raises(ValueError,match='exact seeded cell/rank'):
        audit.check_nstep(bad_moves,roots,cells,ranks,actions,kinds,seeds,result,teacher,.375,radix=first.radix)
    corrupt = deepcopy(result); corrupt['environment_counts']['raw_tile_productions'] += 1
    with pytest.raises(ValueError,match='distinct paid costs'): audit.check_acquisition_work(corrupt,counts,result,{'updates':first.updates},.375,.375)


def test_exact_old_control_and_risk_only_comparisons_detect_changed_real_arrays(tmp_path):
    reference = tmp_path/'old.npz'; changed = tmp_path/'new.npz'
    arrays = dict(reward_indices=np.asarray([1,2],dtype=np.int64),reward_values=np.asarray([.1,.2]),
        terminal_indices=np.asarray([3],dtype=np.int64),terminal_values=np.asarray([.3]))
    np.savez(reference,**arrays); np.savez(changed,**arrays)
    assert audit.sparse_equal({'file':str(changed)},{'file':str(reference)}) == 6
    arrays['reward_values'][0] += 1.; np.savez(changed,**arrays)
    assert audit.sparse_equal({'file':str(changed)},{'file':str(reference)},('terminal',)) == 2
    with pytest.raises(ValueError,match='reproduce V319 exactly'): audit.sparse_equal({'file':str(changed)},{'file':str(reference)})
    arrays['terminal_values'][0] += 1.; np.savez(changed,**arrays)
    with pytest.raises(ValueError,match='risk deltas unchanged'): audit.sparse_equal({'file':str(changed)},{'file':str(reference)},('terminal',))


def test_exact_frozen_reader_configuration_agrees_with_producer_before_full_read():
    from acfqp.science.reward_targets_run_v321 import configuration
    source = Path(__file__).resolve().parents[1]/'reports/query_supervision_v319/summary.json'
    assert configuration(source) == audit.expected_configuration(source)


def records(rows):
    return [dict(lifecycle=row['lifecycle'],parent=row['parent'],cells={task:{arm:np.mean([g['utility'] for g in e['game_summaries']])
        for arm,e in arms.items()} for task,arms in row['final_evaluations'].items()}) for row in rows]


def test_independent_paired_effect_reader_preserves_primary_growth_and_task_retention():
    from test_reward_targets_analysis_v321 import cohort
    from acfqp.science.reward_targets_analysis_v321 import summarize
    rows = cohort(); result = summarize(rows); audit.check_analysis(result,records(rows),rows)
    corrupt = deepcopy(result); corrupt['primary']['lifecycle_values']['0'] += 1.
    with pytest.raises(ValueError,match='paired effect vector'): audit.check_analysis(corrupt,records(rows),rows)
    corrupt = deepcopy(result); corrupt['repaired_query_supported'] = False
    with pytest.raises(ValueError,match='separate evidence requirements'): audit.check_analysis(corrupt,records(rows),rows)


def test_natural_cutoff_is_global_hold_and_never_becomes_terminal_benefit():
    from test_reward_targets_analysis_v321 import cohort
    from acfqp.science.reward_targets_analysis_v321 import summarize
    rows = cohort(); rows[3]['final_evaluations']['B']['OLD_FACTUAL']['game_summaries'][2]['status'] = 'CUTOFF'
    result = summarize(rows); audit.check_analysis(result,records(rows),rows)
    corrupt = deepcopy(result); corrupt['task_contrasts']['A']['NSTEP_QUERY_minus_OLD_QUERY'] = {'mean':3.}
    with pytest.raises(ValueError,match='suppresses every'): audit.check_analysis(corrupt,records(rows),rows)
