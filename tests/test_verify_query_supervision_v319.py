"""Finite V319 group provenance, exact paid reset samples and joint teacher reader."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_query_supervision_v319 as audit
from verify_closed_loop_v313 import swipe


def literal_pool(board, radix=3):
    paths = []; roots = []
    for a, action in enumerate(audit.ACTIONS):
        outer, _ = swipe(board, action)
        if outer == board or max(outer) >= radix:
            continue
        for cell, value in enumerate(outer):
            if value:
                continue
            for rank in (1, 2):
                spawned = list(outer); spawned[cell] = rank
                for b, inner_action in enumerate(audit.ACTIONS):
                    after, _ = swipe(spawned, inner_action)
                    if after != spawned and max(after) < radix:
                        paths.append([a, cell, rank, b]); roots.append(after)
    return paths, roots


def test_every_actual_h2_query_path_preserves_order_and_duplicate_call_multiplicity():
    board = [1, 1]+[0]*14
    paths, roots = literal_pool(board)
    assert len(roots) > len({tuple(root) for root in roots})
    repeated = np.asarray([board]*len(roots), dtype=np.int32)
    counts, actual_roots, actual_paths = audit.query_paths(repeated, np.arange(len(roots)), 3)
    assert np.all(counts == len(roots))
    assert np.array_equal(actual_roots, roots)
    assert np.array_equal(actual_paths, paths)


def test_selector_consumes_one_fresh_draw_even_for_empty_call_pool():
    active = [1, 1]+[0]*14
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    boards = np.asarray([active, lost, active], dtype=np.int32)
    pool, _ = literal_pool(active)
    counts = np.asarray([len(pool), 0, len(pool)], dtype=np.int64)
    rng = audit.TileRandom(319071)
    u = [rng.random() for _ in range(3)]
    ordinals = np.asarray([int(u[0]*counts[0]), -1, int(u[2]*counts[2])], dtype=np.int64)
    audit.check_selector(boards, ordinals, counts, np.asarray([1, 0, 1], dtype=np.int32), 319071, 3)
    corrupt = ordinals.copy(); corrupt[2] = int(u[1]*counts[2])
    assert corrupt[2] != ordinals[2]
    with pytest.raises(ValueError, match='one independent seeded uniform'):
        audit.check_selector(boards, corrupt, counts, np.asarray([1, 0, 1], dtype=np.int32), 319071, 3)


def test_anchor_census_excludes_game_starts_win_and_heldout_without_label_selection():
    boards = np.zeros((10, 16), dtype=np.int32); boards[:, 0] = 1; boards[4, 0] = 11
    games = [dict(steps=5), dict(steps=3), dict(steps=2)]
    indices = audit.anchor_census(boards, games, 2, groups=2)
    assert indices.tolist() == [1, 2, 3, 7]
    with pytest.raises(ValueError, match='without replacements'):
        audit.anchor_census(boards, games, 1, groups=2)


def test_common_root_positions_are_evenly_spaced_valid_census_not_replacements():
    assert audit.selected_positions(np.asarray([1, 0, 1, 1, 0, 1], dtype=np.int32), groups=3).tolist() == [0, 2, 5]
    with pytest.raises(ValueError, match='whole-cohort HOLD'):
        audit.selected_positions(np.asarray([1, 0, 0], dtype=np.int32), groups=2)


def spawn_fixture():
    roots = np.asarray([[1]+[0]*15, [0, 1]+[0]*14], dtype=np.int32)
    uniforms = audit.ground_uniforms(319091, 2)
    cells = np.empty((2, 4), dtype=np.int32)
    for group, board in enumerate(roots):
        empty = np.flatnonzero(board == 0); cells[group] = empty[(uniforms[group, :, 0]*len(empty)).astype(np.int64)]
    ranks = np.where(uniforms[:, :, 1] < .9, 1, 2).astype(np.int32)
    return roots, uniforms, cells, ranks


def test_each_physical_member_resets_the_root_and_paid_raw_budget_is_exact():
    roots, uniforms, cells, ranks = spawn_fixture()
    after = audit.ground_postspawn(roots, uniforms, .1, cells, ranks)
    assert after.shape == (2, 4, 16)
    assert np.all(np.count_nonzero(after, axis=2) == 2)
    assert np.count_nonzero(after != roots[:, None, :]) == 8


@pytest.mark.parametrize('field', ['cells', 'ranks'])
def test_new_physical_spawn_mismatch_is_rejected(field):
    roots, uniforms, cells, ranks = spawn_fixture()
    if field == 'cells':
        cells[0, 0] = (int(cells[0, 0])+1) % 16
    else:
        ranks[0, 0] = 3-int(ranks[0, 0])
    with pytest.raises(ValueError, match='exact continuous'):
        audit.ground_postspawn(roots, uniforms, .1, cells, ranks)


def test_one_step_targets_share_the_selected_branch_with_analytic_win_and_lost():
    teacher = SimpleNamespace(reward=np.zeros(4*3**6), terminal=np.zeros(4*3**6))
    win = [2, 2]+[0]*14
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    post = np.asarray([[win, lost]], dtype=np.int32)
    reward, probability, action, kind, _ = audit.teacher_targets(post, teacher, 3)
    assert reward[0, 0] == 8./2048 and probability[0, 0] == 1.
    assert action[0, 0] == 1 and kind[0, 0] == 2
    assert reward[0, 1] == probability[0, 1] == 0.
    assert action[0, 1] == -1 and kind[0, 1] == 3


def group_fixture():
    roots, uniforms, cells, ranks = spawn_fixture()
    teacher = SimpleNamespace(reward=np.zeros(4*3**6), terminal=np.zeros(4*3**6))
    post = audit.ground_postspawn(roots, uniforms, .1, cells, ranks)
    reward, win, actions, kinds, stats = audit.teacher_targets(post, teacher, 3)
    mean_reward, mean_win = audit.group_means(reward, win)
    arrays = dict(roots=roots, targetreward=reward, targetwin=win, selected_action=actions,
        targetkind=kinds, spawn_cells=cells, spawn_ranks=ranks, mean_reward=mean_reward, mean_win=mean_win)
    return arrays, roots, uniforms, teacher, stats


def test_actual_four_member_teacher_targets_and_group_means_are_accepted():
    arrays, roots, uniforms, teacher, _ = group_fixture()
    audit.check_group_arrays(arrays, roots, uniforms, .1, teacher, 3)


@pytest.mark.parametrize('field', ['targetreward', 'mean_win'])
def test_fake_teacher_component_or_fake_group_update_mean_is_rejected(field):
    arrays, roots, uniforms, teacher, _ = group_fixture()
    arrays[field].flat[0] += .125
    with pytest.raises(ValueError, match='frozen FIRST branch|arithmetic means'):
        audit.check_group_arrays(arrays, roots, uniforms, .1, teacher, 3)


def test_artifact_owner_cannot_substitute_current_head_or_stale_draw_seed(tmp_path):
    metadata = dict(teacher_version={'file':'actual_FIRST_v0.npz','version':0}, draw_seed=319500100000)
    path = tmp_path/'members.npz'
    values = np.asarray([.1,.2], dtype=np.float64)
    np.savez_compressed(path, targets=values, metadata_json=__import__('json').dumps(metadata))
    receipt = dict(file=str(path), saved_bytes=path.stat().st_size, array_bytes=values.nbytes,
        metadata=metadata, save_cpu_seconds=0.,save_wall_seconds=0.)
    assert np.array_equal(audit.artifact_arrays(receipt, ['targets'], metadata)['targets'], values)
    altered = dict(metadata, teacher_version={'file':'updated_private_v1.npz','version':1})
    with pytest.raises(ValueError, match='ownership teacher stream'):
        audit.artifact_arrays(receipt, ['targets'], altered)


def test_exact_v319_configuration_matches_new_driver_without_running_it():
    from acfqp.science.query_supervision_run_v319 import configuration
    source = Path(__file__).resolve().parents[1]/'reports/greedy_targets_v317/summary.json'
    assert audit.expected_configuration(source) == json.loads(json.dumps(configuration(source)))
    assert audit.selection_seed(15,'B',2) == 319251200000
    assert audit.draw_seed(15,'B',2) == 319651200000
    assert audit.evaluation_seed(15,'B',31) == 319915100031
