"""Real sparse replacement chains, immutable selection and native mixed-head values."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.closed_loop_versions_v313 import save_version, snapshot_weights
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.frozen_components_v315 import restore_head, combine_heads
from acfqp.science.native_policy_stream_v313 import choose_direct
from acfqp.science.native_split_risk_v301 import SplitLeaf, predict_components

BUILD = Path(__file__).resolve().parents[1] / 'reports/component_targets_v315/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


@pytest.fixture
def history():
    BUILD.mkdir(parents=True, exist_ok=True)
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    native = NtupleValue(rule, BUILD)
    native.weights[:] = np.arange(native.weights.size).reshape(native.weights.shape) % 9 * .003
    checkpoint = BUILD / 'source.npz'
    native.save(checkpoint)
    template = QueryTD(QueryParent(native, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    source = dict(parent=0, checkpoint=str(checkpoint))
    first = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    first.reward_weights.reshape(-1)[0] = .4
    first.risk_weights.reshape(-1)[0] = .2
    first.updates = 2
    base = save_version(first, source, 0, 0, 'FIRST_LOCAL', 0, BUILD / 'FIRST_LOCAL_v0.npz')
    finals, actual = {}, {}
    for arm, shift in (('MC_LOCAL', .1), ('TD_LOCAL', .3)):
        head = SplitLeaf(template, 'LOCAL_RISK', BUILD)
        head.reward_weights[:] = first.reward_weights
        head.risk_weights[:] = first.risk_weights
        previous = snapshot_weights(head)
        head.reward_weights.reshape(-1)[0] += shift
        head.risk_weights.reshape(-1)[0] += shift
        head.reward_weights.reshape(-1)[1] = shift
        head.risk_weights.reshape(-1)[1] = -shift
        head.updates = 4
        one = save_version(head, source, 0, 0, arm, 1, BUILD / f'{arm}_v1.npz', base=base, previous=previous)
        previous = snapshot_weights(head)
        # Later files contain replacement values, including a return to SOURCE/zero.
        head.reward_weights.reshape(-1)[0] = native.weights.reshape(-1)[0]
        head.risk_weights.reshape(-1)[0] = 0.
        head.reward_weights.reshape(-1)[2] = shift * 2
        head.risk_weights.reshape(-1)[2] = shift * 3
        head.updates = 6
        finals[arm] = save_version(head, source, 0, 0, arm, 2, BUILD / f'{arm}_v2.npz', base=one, previous=previous)
        head.freeze()
        actual[arm] = head
    return template, finals, actual


def test_sparse_chain_reconstructs_actual_source_and_zero_replacements_exactly(history):
    template, finals, actual = history
    for arm in finals:
        restored, receipt = restore_head(template, finals[arm], BUILD)
        np.testing.assert_array_equal(restored.reward_weights, actual[arm].reward_weights)
        np.testing.assert_array_equal(restored.risk_weights, actual[arm].risk_weights)
        assert restored.updates == 6 and not restored.reward_weights.flags.writeable and not restored.risk_weights.flags.writeable
        assert restored.reward_weights.reshape(-1)[0] == template.parent.source.weights.reshape(-1)[0]
        assert restored.risk_weights.reshape(-1)[0] == 0.
        assert [v['version'] for v in receipt['version_chain']] == [0, 1, 2]
        assert receipt['counts']['version_files_loaded'] == 3
        assert receipt['private_weight_bytes'] == 2 * restored.reward_weights.nbytes
        assert receipt['setup_counts']['allocated_weight_parameters'] == 2 * restored.reward_weights.size
        assert receipt['cpu_seconds'] >= 0. and receipt['wall_seconds'] > 0.
        json.dumps(receipt, allow_nan=False)


def test_four_combinations_use_exact_immutable_arrays_and_actual_native_values(history):
    template, finals, actual = history
    heads = {arm:restore_head(template, receipt, BUILD)[0] for arm,receipt in finals.items()}
    board = (1, 2, 0, 0) + (0,) * 12
    before = {arm:(leaf.reward_weights.copy(), leaf.risk_weights.copy()) for arm,leaf in heads.items()}
    for reward_arm in heads:
        for win_arm in heads:
            mixed = combine_heads(heads[reward_arm], heads[win_arm])
            assert mixed.reward_weights is heads[reward_arm].reward_weights
            assert mixed.risk_weights is heads[win_arm].risk_weights
            assert mixed.setup_counts['allocated_weight_parameters'] == mixed.setup_counts['copied_weight_parameters'] == 0
            assert mixed.component_versions['reward'] == finals[reward_arm]
            assert mixed.component_versions['win'] == finals[win_arm]
            components = predict_components(mixed, board)
            reward = predict_components(heads[reward_arm], board)['reward_prediction']
            probability = predict_components(heads[win_arm], board)['risk_probability']
            assert components['combined_prediction'] == reward + 8. * (probability - .5)
            reference = SplitLeaf(template, 'LOCAL_RISK', BUILD)
            reference.reward_weights[:] = actual[reward_arm].reward_weights
            reference.risk_weights[:] = actual[win_arm].risk_weights
            reference.freeze()
            assert mixed.choose(board, .375) == reference.choose(board, .375)
            assert choose_direct(mixed, board, BUILD) == choose_direct(reference, board, BUILD)
            assert mixed.updates == heads[reward_arm].updates == heads[win_arm].updates == 6
    for arm,leaf in heads.items():
        np.testing.assert_array_equal(leaf.reward_weights, before[arm][0])
        np.testing.assert_array_equal(leaf.risk_weights, before[arm][1])


def test_selected_receipt_and_task_bank_mismatches_are_rejected(history):
    template, finals, _ = history
    wrong = deepcopy(finals['MC_LOCAL'])
    wrong['context_id'] = 1
    with pytest.raises(ValueError, match='receipt differs'):
        restore_head(template, wrong, BUILD)
    mc, _ = restore_head(template, finals['MC_LOCAL'], BUILD)
    td, _ = restore_head(template, finals['TD_LOCAL'], BUILD)
    td.component_identity = dict(td.component_identity, context_id=1)
    with pytest.raises(ValueError, match='same SOURCE, task bank and version'):
        combine_heads(mc, td)


def test_missing_actual_base_file_and_unfrozen_component_cannot_be_selected(history):
    template, finals, _ = history
    source_path = Path(finals['MC_LOCAL']['file'])
    missing_path = BUILD / 'missing_history.npz'
    with np.load(source_path, allow_pickle=False) as saved:
        arrays = {key:saved[key].copy() for key in saved.files if key != 'metadata_json'}
        metadata = json.loads(str(saved['metadata_json']))
    metadata['file'], metadata['base_file'] = str(missing_path), str(BUILD / 'absent_actual_v1.npz')
    np.savez_compressed(missing_path, **arrays, metadata_json=json.dumps(metadata))
    receipt = dict(finals['MC_LOCAL'], **metadata)
    with pytest.raises(FileNotFoundError):
        restore_head(template, receipt, BUILD)
    mc, _ = restore_head(template, finals['MC_LOCAL'], BUILD)
    td, _ = restore_head(template, finals['TD_LOCAL'], BUILD)
    td.risk_weights.flags.writeable = True
    with pytest.raises(ValueError, match='remain frozen'):
        combine_heads(mc, td)
