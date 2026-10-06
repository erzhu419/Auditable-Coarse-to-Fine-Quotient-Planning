"""Actual V324 snapshot wiring with finite mocked terminal endpoints, no suffix pilots."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from acfqp.science import win_terminal_run_v325 as driver
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from verify_closed_loop_v313 import HeadVersions, read_source_weights
from verify_greedy_targets_v317 import predict_components as literal_components


def retained_life():
    previous = json.loads((ROOT/'reports/win_learning_v324/summary.json').read_text())
    return previous['source_provenance']['parents'][0], previous['by_lifecycle'][0]


def test_actual_cell_wiring_uses_three_saved_snapshots_and_paired_suffix_seeds(monkeypatch):
    # Swapped heads, duplicated alias prediction work or reused suffix seeds would invalidate the diagnostic.
    source, old = retained_life()
    out = ROOT/'reports/win_terminal_v325/test_logs/driver_fixture'
    runtime = out/'runtime'; runtime.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(driver, 'GROUPS', 2)
    indices = np.asarray([0, 16383], dtype=np.int64)
    template, _ = load_leaf(source, runtime)
    snapshots, continuations = [], []
    actual_predict = driver.predict_win

    def observed_predict(leaf, roots):
        snapshots.append((leaf.updates, roots.copy()))
        return actual_predict(leaf, roots)

    def finite_terminal(first, roots, spawn_cells, spawn_ranks, selected_action, targetkind,
            seeds, build, trace, **kwargs):
        task = trace.parent.name
        arm, stage = trace.stem.split('_R')
        number = int(stage.removesuffix('_trace'))
        initial = old['initial'][task]
        with np.load(old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']['file'],
                allow_pickle=False) as retained:
            for actual, name in ((roots, 'roots'), (spawn_cells, 'spawn_cells'),
                    (spawn_ranks, 'spawn_ranks'), (selected_action, 'selected_action'), (targetkind, 'targetkind')):
                np.testing.assert_array_equal(actual, retained[name][indices])
        assert first.updates == initial['head_version']['updates']
        assert not first.reward_weights.flags.writeable and not first.risk_weights.flags.writeable
        assert kwargs == dict(p_model=initial['planning_belief']['estimated_p_four'],
            p_true=.1 if task == 'A' else .5, max_steps=8192)
        expected_seeds = [[325500000000+driver.TASKS.index(task)*1000000+number*100000+int(group)*4+member
            for member in range(4)] for group in indices]
        np.testing.assert_array_equal(seeds, expected_seeds)
        continuations.append((task, arm, number, seeds.copy()))
        trace.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(trace, moves=np.empty((0, 8), dtype=np.int32))
        shape = (2, 4)
        status = np.asarray([[1, -1, 0, -1], [-1, 1, -1, 1]], dtype=np.int32)
        actions = np.asarray([[2, 3, 8192, 0], [1, 2, 4, 3]], dtype=np.int64)
        reward = np.where(status == 0, np.nan, .5)
        win = np.where(status == 0, np.nan, status == 1).astype(np.float64)
        return dict(scores=np.ones(shape, dtype=np.int64)*1024, actions=actions,
            status=status, new_raw_tiles=actions.copy(), final_boards=np.tile(roots[:, None, :], (1, 4, 1)),
            reward_return=reward, win=win, utility=reward+8.*(win-.5),
            environment_counts=dict(raw_tile_productions=int(actions.sum())),
            planning_counts=dict(choose_calls=9), representation_counts=dict(risk_sigmoid_evaluations=9),
            counts=dict(rollouts_started=8, reused_start_spawns=8, terminal_wins=3,
                terminal_losses=4, action_cutoffs=1),
            trace_artifact=dict(file=str(trace), compressed_bytes=trace.stat().st_size), cpu_seconds=.25)

    monkeypatch.setattr(driver, 'predict_win', observed_predict)
    monkeypatch.setattr(driver, 'continue_targets', finite_terminal)
    row = driver._run_life(template, source, old, runtime, out)
    assert len(snapshots) == 24 and len(continuations) == 8
    for task in driver.TASKS:
        for number in (1, 2):
            factual = next(seeds for t, a, n, seeds in continuations if (t, a, n) == (task, 'FACTUAL_WIN', number))
            query = next(seeds for t, a, n, seeds in continuations if (t, a, n) == (task, 'QUERY_WIN', number))
            np.testing.assert_array_equal(factual, query)
        initial = old['initial'][task]
        for arm in driver.ARMS:
            reference = HeadVersions(read_source_weights(source['checkpoint']), source['checkpoint'],
                dict(lifecycle=0, parent=0, context_id=initial['context_id'], arm=arm), 'LOCAL_RISK')
            expected = {1: [], 2: []}
            for number in (0, 1, 2):
                version = initial['head_version'] if number == 0 else old['rounds'][str(number)][task]['arms'][arm]['head_version']
                reference.apply(version)
                for stage in (1, 2):
                    receipt = old['rounds'][str(stage)][task]['arms'][arm]['supervision']['group_artifact']
                    with np.load(receipt['file'], allow_pickle=False) as retained:
                        _, probability = literal_components(retained['roots'][indices], reference)
                    expected[stage].append(probability)
            for number in (1, 2):
                cell = row['stages'][str(number)][task]['arms'][arm]
                assert set(cell['prediction_receipts']) == {'FIRST', 'v1', 'v2'}
                assert cell['source_group_artifact'] == old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']
                versions = cell['prediction_versions']
                assert versions == dict(FIRST=initial['head_version'],
                    before=initial['head_version'] if number == 1 else old['rounds']['1'][task]['arms'][arm]['head_version'],
                    after=old['rounds'][str(number)][task]['arms'][arm]['head_version'],
                    FINAL=old['rounds']['2'][task]['arms'][arm]['head_version'])
                with np.load(cell['outcome_artifact']['file'], allow_pickle=False) as saved:
                    np.testing.assert_array_equal(saved['prediction_probabilities'], expected[number])
                    np.testing.assert_array_equal(saved['original_group_indices'], indices)
                    assert json.loads(str(saved['metadata_json'])) == cell['outcome_artifact']['metadata']
                    assert saved['prediction_logits'].shape == (3, 2)
                    assert np.isnan(saved['win'][0, 2]) and np.isnan(saved['reward_return'][0, 2])
                for group_index, group in enumerate(cell['groups']):
                    assert group['index'] == indices[group_index]
                    values = expected[number]
                    assert group['predictions'] == dict(FIRST=values[0][group_index],
                        before=values[0 if number == 1 else 1][group_index],
                        after=values[number][group_index], FINAL=values[2][group_index])
                assert cell['groups'][0]['replicas'][2]['actual_win'] is None
                assert cell['groups'][0]['replicas'][2]['actual_reward'] is None
                assert cell['groups'][0]['replicas'][2]['status'] == 'CUTOFF'
    account = driver.accounting([row], [dict(cpu_seconds=1., compiler_cpu_seconds=2.)], 3., 4., 5.)
    assert account['rollouts'] == account['reused_first_spawns'] == 64
    assert account['fit_updates'] == account['new_head_files'] == account['new_evaluation_games'] == 0
    assert account['new_raw_tiles'] == 8*8207
    assert account['new_calibration_component_cpu_seconds'] == 6.
    assert account['economic_source_v324_and_calibration_component_cpu_seconds'] == 11.
    for arm in driver.ARMS:
        value = account['per_arm'][arm]
        assert value['unique_snapshot_cells'] == 12 and value['prediction_counts']['win_predictions'] == 24
        assert value['prediction_counts']['reward_table_lookups'] == 24*32
        assert value['rollouts'] == 32 and value['new_raw_tiles'] == 4*8207
        assert value['terminal_counts'] == dict(WON=12, LOST=16, CUTOFF=4)


def test_saved_group_metadata_mismatch_blocks_read():
    # A group receipt pointing to different ownership data must stop before any fresh suffix acquisition.
    _, old = retained_life()
    receipt = deepcopy(old['rounds']['1']['A']['arms']['QUERY_WIN']['supervision']['group_artifact'])
    receipt['metadata']['arm'] = 'FACTUAL_WIN'
    with pytest.raises(ValueError, match='metadata differs'):
        driver._read_groups(receipt, np.asarray([0, 16383]))
