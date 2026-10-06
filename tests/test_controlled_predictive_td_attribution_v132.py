"""Finite retained-transition fixtures; no RNG or environment sampling."""
from collections import Counter
import copy
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_td_attribution_v132 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_td_attribution_v132_build'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=8., goal_bonus=8.)
BOARD = [1, 1, 0, 0]+[0]*12
MODELS, REPLAYS, RESULTS = [], [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_td_attribution_v132.core_checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    replay_work = Counter()
    for replay in REPLAYS:
        if replay._handle:
            native, _, _ = replay._native_counts()
            replay_work.update(dict(zip(core.COUNT_NAMES, map(int, native))))
            replay_work.update(replay.counts)
        else:
            replay_work.update(replay.completed_counts)
    data['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        reference_work=dict(sum((m.counts for m in MODELS), Counter())),
        replay_work=dict(replay_work),
        setup_counts=dict(sum((r.setup_counts for r in REPLAYS), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Hand specified boards, deterministic recorded empty-cell insertions and TD arithmetic. No random draws.'))
    path.write_text(json.dumps(data, indent=2)+'\n')


@pytest.fixture(autouse=True)
def small_goal(monkeypatch):
    def status(board, work):
        work['synthetic_status_checks'] += 1
        if max(board) >= 4:
            return 'WON'
        return ground.state_from_board_v1(board).status.value
    monkeypatch.setattr(core, '_status', status)


def model():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    parent = QueryParent(source, SOURCE, TARGET, .4)
    result = QueryTD(parent, build_dir=BUILD)
    MODELS.append(result)
    return result


def clone(original):
    result = QueryTD(original.parent, build_dir=BUILD)
    result.model.weights[:] = original.weights
    result.model.updates = original.updates
    MODELS.append(result)
    return result


def retained(model, board, pending=None, step=0, episode=0, spawn_cell=None, spawn_rank=1):
    """Record exactly one manually supplied transition, using the original TD code."""
    start_updates = model.updates
    chosen = model.choose(board)
    update = model.update(pending, chosen['value']) if pending is not None else None
    after = chosen['afterstate']
    cell = after.index(0) if spawn_cell is None else spawn_cell
    assert after[cell] == 0
    end = list(after)
    end[cell] = spawn_rank
    status = core._status(tuple(end), Counter())
    next_pending = None if max(after) >= model.radix else list(after)
    terminal = None
    if status == 'LOST' and next_pending is not None:
        terminal = dict(model.update(next_pending, -TARGET['failure_penalty']), afterstate=next_pending)
        next_pending = None
    return dict(episode=episode, start_step=step, end_step=step+1, start_board=list(board), end_board=end,
        actions=[chosen['action']], scores=[chosen['score']], spawned_cells=[cell], spawned_ranks=[spawn_rank],
        chosen_values=[chosen['value']], chosen_raw_values=[chosen['raw_value']],
        td_targets=[None if update is None else update['target']],
        raw_td_targets=[None if update is None else update['raw_target']],
        td_errors=[None if update is None else update['error']], terminal_update=terminal,
        pending_before=pending, pending_after=next_pending, updates_before=start_updates,
        updates_after=model.updates, status=status, censored_last_update=False)


def replay(mid, probes):
    result = core.TDAttributionReplay(mid, probes, BUILD)
    REPLAYS.append(result)
    return result


def finish(replay, final):
    result = replay.finish(final)
    RESULTS.append(result)
    return result


def test_pending_checkpoint_boundary_replays_all_arithmetic_and_preserves_sources():
    mid = model()
    final = clone(mid)
    source_before = mid.parent.source.weights.copy()
    mid_before = mid.weights.copy()
    first = retained(final, BOARD)
    second = retained(final, first['end_board'], first['pending_after'], step=1)
    engine = replay(mid, [dict(probe_id='pair', old_afterstate=BOARD,
        new_afterstate=first['pending_after'])])
    assert engine.segment(first)['updates'] == 0
    assert engine.segment(second)['category_counts'] == dict(LOSS=0, WIN_BOUNDARY=0, BOOTSTRAP=1)
    result = finish(engine, final)
    assert result['checks']['exact_final_weights']
    assert result['counts']['greedy_action_checks'] == 2
    assert result['counts']['td_error_checks'] == 1
    np.testing.assert_array_equal(mid.weights, mid_before)
    np.testing.assert_array_equal(mid.parent.source.weights, source_before)
    assert not np.shares_memory(engine.weights, mid.weights)


def test_win_boundary_targets_previous_pending_and_never_goal_features():
    mid = model()
    final = clone(mid)
    pending = list(BOARD)
    row = retained(final, [3, 3]+[0]*14, pending, step=20)
    assert row['status'] == 'WON' and row['terminal_update'] is None
    engine = replay(mid, [dict(probe_id='goal', old_afterstate=pending, new_afterstate=[4]+[0]*15)])
    engine.segment(row)
    result = finish(engine, final)
    assert result['category_counts'] == dict(LOSS=0, WIN_BOUNDARY=1, BOOTSTRAP=0)
    assert result['probes'][0]['categories']['LOSS'] == 0.
    assert result['counts']['update_feature_occurrences'] == 32


def test_loss_terminal_is_an_explicit_separate_update():
    mid = model()
    # DOWN creates the checkerboard with its top-left cell missing.
    board = [2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0, 1, 2, 1]
    choices = mid.choose(board)['action_values']
    desired = choices['DOWN']['afterstate']
    mid.weights[:] = 0.
    for address in mid.model.feature_indices(desired):
        mid.weights.reshape(-1)[address] += 10.
    assert mid.choose(board)['action'] == 'DOWN'
    final = clone(mid)
    row = retained(final, board, spawn_cell=0, spawn_rank=1)
    assert row['status'] == 'LOST'
    engine = replay(mid, [dict(probe_id='loss', old_afterstate=BOARD, new_afterstate=desired)])
    engine.segment(row)
    result = finish(engine, final)
    assert result['category_counts'] == dict(LOSS=1, WIN_BOUNDARY=0, BOOTSTRAP=0)
    assert result['probes'][0]['signed_overlap_update_counts']['LOSS'] == 1


def test_repeated_addresses_attribution_matches_hand_computed_update():
    mid = model()
    mid.weights[:] = 0.
    final = clone(mid)
    old = [0]*16
    new = list(BOARD)
    row = retained(final, BOARD, pending=new, step=5)
    feature_count = Counter(map(int, mid.model.feature_indices(new)))
    before = sum(float(mid.weights.reshape(-1)[a]) for a in mid.model.feature_indices(new))
    error = row['raw_td_targets'][0]-before
    difference = Counter(map(int, mid.model.feature_indices(new)))
    difference.subtract(map(int, mid.model.feature_indices(old)))
    expected = math.fsum(coefficient*(.0025*error*feature_count[address])
        for address, coefficient in difference.items())
    engine = replay(mid, [dict(probe_id='shared', old_afterstate=old, new_afterstate=new)])
    engine.segment(row)
    result = finish(engine, final)
    assert len(feature_count) < 32
    assert result['probes'][0]['linear_gap_change'] == expected
    assert result['probes'][0]['categories']['BOOTSTRAP'] == pytest.approx(expected, abs=1e-14)
    assert result['probes'][0]['exact_board_categories']['BOOTSTRAP'] == pytest.approx(expected, abs=1e-14)


def test_rotated_same_features_cancel_without_false_overlap():
    mid = model()
    final = clone(mid)
    rotated = np.rot90(np.asarray(BOARD).reshape(4, 4)).reshape(-1).tolist()
    assert core.signed_features(mid.model, BOARD, rotated) == {}
    row = retained(final, BOARD, pending=BOARD, step=1)
    engine = replay(mid, [dict(probe_id='symmetric', old_afterstate=BOARD, new_afterstate=rotated)])
    engine.segment(row)
    result = finish(engine, final)['probes'][0]
    assert result['nonzero_signed_addresses'] == 0
    assert result['categories'] == dict.fromkeys(core.CATEGORIES, 0.)
    assert result['signed_overlap_update_counts'] == dict.fromkeys(core.CATEGORIES, 0)
    assert result['linear_gap_change'] == 0.


def test_different_board_shared_features_are_separate_from_exact_board_updates():
    mid = model()
    final = clone(mid)
    rotated = np.rot90(np.asarray(BOARD).reshape(4, 4)).reshape(-1).tolist()
    row = retained(final, BOARD, pending=rotated, step=1)
    engine = replay(mid, [dict(probe_id='shared_only', old_afterstate=[0]*16, new_afterstate=BOARD)])
    engine.segment(row)
    result = finish(engine, final)['probes'][0]
    assert result['categories']['BOOTSTRAP'] != 0.
    assert result['exact_board_categories']['BOOTSTRAP'] == 0.
    assert result['shared_feature_categories'] == result['categories']


def test_stored_error_mismatch_fails_before_its_weight_update():
    mid = model()
    final = clone(mid)
    row = retained(final, BOARD, pending=BOARD, step=1)
    row['td_errors'][0] = np.nextafter(row['td_errors'][0], math.inf)
    engine = replay(mid, [])
    with pytest.raises(ValueError, match='TD error mismatch'):
        engine.segment(row)
    np.testing.assert_array_equal(engine.weights, mid.weights)


def test_source_predictions_and_pending_continuity_are_checked():
    mid = model()
    final = clone(mid)
    first = retained(final, BOARD)
    second = retained(final, first['end_board'], first['pending_after'], step=1)
    engine = replay(mid, [])
    engine.segment(first)
    bad = copy.deepcopy(second)
    bad['pending_before'][0] += 1
    with pytest.raises(ValueError, match='pending or board continuity'):
        engine.segment(bad)
    engine2 = replay(mid, [])
    bad = copy.deepcopy(first)
    bad['chosen_values'][0] = np.nextafter(bad['chosen_values'][0], math.inf)
    with pytest.raises(ValueError, match='chosen value mismatch'):
        engine2.segment(bad)


def test_exact_final_checkpoint_comparison_detects_unreplayed_change():
    mid = model()
    final = clone(mid)
    row = retained(final, BOARD)
    engine = replay(mid, [])
    engine.segment(row)
    final.weights[0, 0] = np.nextafter(final.weights[0, 0], math.inf)
    with pytest.raises(ValueError, match='final checkpoint'):
        engine.finish(final)
