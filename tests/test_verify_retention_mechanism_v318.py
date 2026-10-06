"""Finite V318 exact-board support and two-table H2 localization reader cases."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_retention_mechanism_v318 as audit
from verify_closed_loop_v313 import literal_choose


def heads(radix=3):
    rng = np.random.default_rng(318018)
    size = 4*radix**6
    base = SimpleNamespace(reward=rng.normal(0., .02, size), terminal=rng.normal(0., .05, size))
    updated = SimpleNamespace(reward=rng.normal(0., .05, size), terminal=rng.normal(0., .2, size))
    return updated, base


def all_prediction_boards(board, radix=3):
    result = []
    for action in audit.ACTIONS:
        outer, _ = audit.swipe(board, action)
        if outer == board or max(outer) >= radix:
            continue
        for cell, value in enumerate(outer):
            if value:
                continue
            for rank in (1, 2):
                spawned = list(outer); spawned[cell] = rank
                for inner in audit.ACTIONS:
                    after, _ = audit.swipe(spawned, inner)
                    if after != spawned and max(after) < radix:
                        result.append(after)
    return result


def test_lossless_support_distinguishes_symmetry_equivalent_feature_boards():
    board = np.asarray([1, 2, 0, 1, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0])
    rotated = np.rot90(board.reshape(4, 4)).reshape(-1)
    assert sorted(audit.feature_addresses([board], 3)[0]) == sorted(audit.feature_addresses([rotated], 3)[0])
    assert audit.board_keys([board])[0] != audit.board_keys([rotated])[0]
    assert int(audit.board_keys([board])[0]) == sum(int(rank) << (4*cell) for cell, rank in enumerate(board))
    counts = Counter()
    assert not audit.support_contains(audit.board_keys([board]), rotated, counts)


def test_support_excludes_winning_unused_rows_and_heldout_states():
    a = [1]+[0]*15; winning = [3]+[0]*15; heldout = [2]+[0]*15
    assert np.array_equal(audit.exact_fit_support([a, a, winning, heldout], 3, 3), audit.board_keys([a]))


@pytest.mark.parametrize('on_support', [False, True])
def test_full_or_empty_gate_matches_the_correct_actual_two_table_head(on_support):
    board = [1, 1, 0, 0, 0, 2, 0, 0]+[0]*8
    updated, base = heads()
    keys = np.unique(audit.board_keys(all_prediction_boards(board))) if on_support else np.asarray([], dtype=np.uint64)
    chosen = audit.literal_localized_choose(board, updated, base, keys, .17, 3)
    expected_head = updated if on_support else base
    expected = literal_choose(board, expected_head.reward, expected_head.terminal, 'LOCAL_RISK', .17, radix=3)
    audit.equal_tree({key: chosen[key] for key in expected}, expected, 'correct joint head and full H2 decomposition')
    assert chosen['support_counts']['membership_queries'] > 0
    assert chosen['support_counts'].get('base_head_queries' if on_support else 'updated_head_queries', 0) == 0
    assert chosen['support_counts']['encoded_board_cells'] == 16*chosen['support_counts']['membership_queries']


def test_gate_addresses_second_ply_prediction_not_the_input_board():
    board = [1, 1]+[0]*14; updated, base = heads()
    chosen = audit.literal_localized_choose(board, updated, base, audit.board_keys([board]), .1, 3)
    assert chosen['support_counts'].get('updated_head_queries', 0) == 0
    expected = literal_choose(board, base.reward, base.terminal, 'LOCAL_RISK', .1, radix=3)
    assert chosen['action'] == expected['action']
    assert chosen['value'] == expected['value']


def test_counterfactual_v2_rejects_another_current_head_base():
    head = SimpleNamespace(version=1, file='actual_greedy_v1.npz')
    with pytest.raises(ValueError, match='actual GREEDY v1'):
        audit.apply_counterfactual_version(head, dict(arm='FIRST_BOOTSTRAP_LOCAL', version=2, base_file='FIRST_v0.npz'))


def effect_record(values):
    return dict(mean=float(np.mean(values)), ci95=[.1, .9], ci98_75=[-.2, 1.2],
        lifecycle_deltas={str(life):value for life, value in enumerate(values)},
        parent_mean_deltas={str(parent):float(np.mean(values[parent::4])) for parent in range(4)},
        improved_equal_worse=[sum(value > 0 for value in values), sum(value == 0 for value in values), sum(value < 0 for value in values)],
        status98_75='UNRESOLVED')


def test_family_interval_accepts_unresolved_despite_positive_pointwise_interval():
    values = [float(life//4-1) for life in range(16)]
    audit.check_effect(effect_record(values), values, True, True)


def test_family_support_rejects_pointwise_threshold_and_retains_cutoff_hold():
    values = [float(life//4-1) for life in range(16)]; record = effect_record(values)
    record['status98_75'] = 'SUPPORTED_GAIN'
    with pytest.raises(ValueError, match='family interval'):
        audit.check_effect(record, values, True, True)
    record['status98_75'] = 'HOLD_CUTOFF'
    audit.check_effect(record, values, False, True)


def first_targets_fixture(tmp_path):
    first = SimpleNamespace(reward=np.broadcast_to(np.array([.00375]), (4*11**6,)),
        terminal=np.broadcast_to(np.array([.01]), (4*11**6,)))
    active = [1]+[0]*15; activepost = [1, 1]+[0]*14
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    lostafter = list(lost); lostafter[-1] = 0
    boards = np.asarray([active, lostafter], dtype=np.int32)
    postspawn = np.asarray([activepost, lost], dtype=np.int32)
    games = [dict(steps=2, status='LOST')]
    first_version = dict(arm='FIRST_LOCAL', version=0, file='actual_FIRST_v0.npz')
    current_version = dict(arm='GREEDY_LOCAL', version=1, file='actual_GREEDY_v1.npz')
    reward, win, kind, selected, _ = audit.greedy_targets(boards, postspawn, games, 1, first)
    metadata = dict(audit.greedy_target_metadata(first_version, 1, 2),
        schema='acfqp.frozen_first_greedy_targets.v318', bootstrap_mode='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD',
        current_start_version=current_version)
    path = tmp_path/'first_targets.npz'
    arrays = dict(targetreward=reward, targetwin=win, targetkind=kind, selected_action=selected)

    def save():
        np.savez_compressed(path, **arrays, metadata_json=json.dumps(metadata))
    save()
    work = dict(fitted_games=1, fitted_steps=2, trained_afterstates=2, learning_counts={},
        normalization_counts={}, representation_counts={}, bootstrap_counts={}, bootstrap_planning_counts={})
    def sample(index):
        return dict(step=index, reward_target=float(reward[index]), risk_target=float(win[index]),
            reward_prediction=.3, risk_probability=.6, combined_prediction=.3+8*(.6-.5),
            reward_error=float(reward[index])-.3, risk_error=float(win[index])-.6)
    fit = dict(work, method='FIRST_BOOTSTRAP_LOCAL', alpha=.0025,
        bootstrap_mode=metadata['bootstrap_mode'], bootstrap_version=first_version, current_start_version=current_version,
        frozen_game_start_predictions=True, frozen_batch_start_bootstrap=True,
        target_artifact=dict(file=str(path), saved_bytes=path.stat().st_size, metadata=metadata, save_cpu_seconds=0.),
        target_counts=dict(terminal_game_labels=1, goal_checks=2, skipped_winning_afterstates=0,
            postspawn_board_reads=2, reward_target_assignments=2, win_target_assignments=2,
            bootstrap_greedy_targets=1, analytic_selected_win_targets=0, postspawn_lost_targets=1, target_kind_reads=2),
        first_sample=sample(0), last_sample=sample(1))
    return SimpleNamespace(fit=fit, boards=boards, postspawn=postspawn, games=games, first=first,
        first_version=first_version, current_version=current_version, old_fit=work, arrays=arrays, save=save, path=path)


def read_first(fixture):
    return audit.check_first_targets(fixture.fit, fixture.boards, fixture.postspawn, fixture.games, 1,
        fixture.first, fixture.first_version, fixture.current_version, fixture.old_fit)


def test_literal_first_bootstrap_targets_accept_exact_new_arrays_and_current_head_metadata(tmp_path):
    fixture = first_targets_fixture(tmp_path)
    assert read_first(fixture) == (48, 2)


@pytest.mark.parametrize('corruption', ['reward', 'action', 'own_head_mode'])
def test_first_bootstrap_reader_rejects_target_branch_or_bootstrap_ownership_corruption(tmp_path, corruption):
    fixture = first_targets_fixture(tmp_path)
    if corruption == 'own_head_mode':
        fixture.fit['bootstrap_mode'] = 'BATCH_START_FROZEN_OWN_HEAD'
    else:
        if corruption == 'reward':
            fixture.arrays['targetreward'][0] += .25
        else:
            fixture.arrays['selected_action'][0] = (int(fixture.arrays['selected_action'][0])+1) % 4
        fixture.save(); fixture.fit['target_artifact']['saved_bytes'] = fixture.path.stat().st_size
    with pytest.raises(ValueError):
        read_first(fixture)


def test_independent_configuration_keeps_diagnostic_scope_and_paired_old_evaluation_seeds():
    from acfqp.science.retention_run_v318 import configuration
    prior = Path(__file__).resolve().parents[1]/'reports/greedy_targets_v317/summary.json'
    assert audit.expected_configuration(prior) == configuration(prior)
