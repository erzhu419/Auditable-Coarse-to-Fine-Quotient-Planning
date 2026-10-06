import json
from types import SimpleNamespace

import numpy as np

from acfqp.science.closed_loop_versions_v313 import (
    save_version, snapshot_weights, select_prefix)


def test_initial_linear_records_only_actual_changes_from_source_and_neutral(tmp_path):
    leaf = SimpleNamespace(kind='LINEAR_WIN2', updates=2,
        model=SimpleNamespace(weights=np.array([1., 2., 0.])),
        reward_weights=np.array([1., 3., 0.]),
        win_weights=np.array([1./64, .1, 1./64]))
    r = save_version(leaf, dict(parent=0, checkpoint='new_source.npz'),
        0, 1, 'FIRST_LINEAR', 0, tmp_path/'v0.npz')
    with np.load(r['file']) as z:
        assert z['reward_indices'].tolist() == [1]
        assert z['reward_values'].tolist() == [3.]
        assert z['terminal_indices'].tolist() == [1]
        assert z['terminal_values'].tolist() == [.1]
        assert json.loads(str(z['metadata_json']))['default_terminal'] == 1./64
    assert r['copy_parameters'] == 0 and r['scan_parameters'] == 6


def test_native_four_table_shape_uses_flat_addresses_in_incremental_receipts(tmp_path):
    leaf = SimpleNamespace(kind='LOCAL_RISK', updates=1,
        model=SimpleNamespace(weights=np.zeros((4, 3))),
        reward_weights=np.zeros((4, 3)), risk_weights=np.zeros((4, 3)))
    leaf.reward_weights[3, 1] = 2.
    source = dict(parent=0, checkpoint='new_source.npz')
    first = save_version(leaf, source, 0, 0, 'FIRST_LOCAL', 0, tmp_path/'v0.npz')
    old = snapshot_weights(leaf); leaf.risk_weights[2, 2] = -.2
    later = save_version(leaf, source, 0, 0, 'CLOSED_LOCAL', 1,
        tmp_path/'v1.npz', base=first, previous=old)
    with np.load(first['file']) as z:
        assert z['reward_indices'].tolist() == [10]
        assert z['reward_values'].tolist() == [2.]
    with np.load(later['file']) as z:
        assert z['terminal_indices'].tolist() == [8]
        assert z['terminal_values'].tolist() == [-.2]


def test_incremental_history_preserves_zero_reversions_and_previous_identity(tmp_path):
    leaf = SimpleNamespace(kind='LOCAL_RISK', updates=1,
        model=SimpleNamespace(weights=np.zeros(3)),
        reward_weights=np.array([0., 2., 0.]), risk_weights=np.array([0., .3, 0.]))
    source = dict(parent=1, checkpoint='new_source.npz')
    first = save_version(leaf, source, 1, 0, 'FIRST_LOCAL', 0, tmp_path/'v0.npz')
    old = snapshot_weights(leaf)
    leaf.reward_weights[1] = 0.; leaf.risk_weights[2] = -.5; leaf.updates += 2
    second = save_version(leaf, source, 1, 0, 'CLOSED_LOCAL', 1,
        tmp_path/'v1.npz', base=first, previous=old)
    with np.load(second['file']) as z:
        assert z['reward_indices'].tolist() == [1]
        assert z['reward_values'].tolist() == [0.]
        assert z['terminal_indices'].tolist() == [2]
        assert z['terminal_values'].tolist() == [-.5]
    assert second['base_file'] == first['file']
    assert second['copy_parameters'] == 6 and second['changed_parameters'] == 2
    assert old['reward'][1] == 2. and old['terminal'][2] == 0.


def test_quota_masks_only_chronological_fit_states_without_truncating_labels():
    boards = np.zeros((6, 16), dtype=np.int32); boards[1, 0] = 11
    dataset = dict(afterstates=boards, fit_step_end=4,
        rewards=np.array([.1, .2, .3, .4, .5, .6]),
        ends=np.array([4, 6]), terminal_codes=np.array([1, -1]))
    mask, receipt = select_prefix(dataset, 2)
    assert mask.tolist() == [1, 0, 1, 0, 0, 0]
    assert receipt['eligible_samples'] == 3 and receipt['last_selected_step'] == 2
    assert dataset['ends'].tolist() == [4, 6]
    assert dataset['rewards'].tolist() == [.1, .2, .3, .4, .5, .6]
    assert dataset['terminal_codes'].tolist() == [1, -1]
