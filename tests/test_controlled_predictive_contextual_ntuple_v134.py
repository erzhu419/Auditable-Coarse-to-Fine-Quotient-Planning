"""Static contextual features and scripted TD integration; no game sampling."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_contextual_ntuple_v134 as core
from acfqp.science import controlled_predictive_online_query_td_v131 as single
from acfqp.science.controlled_predictive_ntuple_td_v120 import ALPHA, NtupleValue, PATTERNS
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_contextual_ntuple_v134_build'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=8., goal_bonus=8.)
SPARSE = [1, 1, 0, 0]+[0]*12
DENSE = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 0, 0, 0, 0]
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
SOURCES, MODELS, STREAMS = [], [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_contextual_ntuple_v134.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        model_work=dict(sum((model.counts for model in MODELS), Counter())),
        source_work=dict(sum((source.counts for source in SOURCES), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in MODELS+SOURCES), Counter())),
        scripted_environment_work=dict(sum((stream.environment_counts for stream in STREAMS), Counter())),
        newly_sampled_environment_transitions=0,
        scope='Static synthetic features and three-transition scripted spawn streams; no natural-game samples.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


def parent():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    source.updates = 42
    SOURCES.append(source)
    return QueryParent(source, SOURCE, TARGET, .4)


def model(representation, source=None):
    result = core.ConditionalQueryTD(parent() if source is None else source, representation, BUILD)
    MODELS.append(result)
    return result


def assert_choices(left, right):
    for field in ('action', 'value', 'status'):
        assert left[field] == right[field]
    assert left['action_values'].keys() == right['action_values'].keys()
    for action, row in left['action_values'].items():
        for field in ('value', 'score', 'afterstate'):
            assert row[field] == right['action_values'][action][field]


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_both_source_copies_preserve_every_legal_value_including_goal_and_d4_ties(representation):
    result = model(representation)
    source = result.parent.source
    assert result.kind == 'PRIOR' and result.representation == representation
    assert result.weights.shape == (2, 4, 4**6)
    for bank in result.weights:
        np.testing.assert_array_equal(bank, source.weights)
    assert not np.shares_memory(result.weights, source.weights)
    assert result.setup_counts['source_parameters_copied'] == 2*source.weights.size
    assert result.setup_counts['allocated_weight_parameters'] == 2*source.weights.size
    for original in (SPARSE, DENSE, [3, 3]+[0]*14, [4]+[0]*15, LOST):
        board = np.asarray(original).reshape(4, 4)
        for reflected in (False, True):
            for rotation in range(4):
                transformed = np.rot90(np.fliplr(board) if reflected else board, rotation).reshape(-1)
                assert_choices(result.choose(transformed), result.parent.choose(transformed))


def test_extra_cells_follow_tuple_symmetries_and_are_outside_every_tuple():
    result = model('CAPACITY')
    assert core.CAPACITY_EXTRA_CELLS == (3, 7, 6, 10)
    for tuple_index, extra in enumerate(core.symmetry_extra_cells()):
        for symmetry_index, cell in enumerate(extra):
            assert int(cell) not in result.model.patterns[tuple_index, symmetry_index]
    np.testing.assert_array_equal(core.symmetry_extra_cells()[:, 0], core.CAPACITY_EXTRA_CELLS)


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_context_switches_an_address_without_changing_its_six_tuple_ranks(representation):
    result = model(representation)
    left = [1]*16
    for cell in (3, 7, 8, 9, 10):
        left[cell] = 0
    right = left.copy()
    right[3] = 1
    assert [left[i] for i in PATTERNS[0]] == [right[i] for i in PATTERNS[0]]
    bank_size = result.parent.source.weights.size
    left_address = int(result.model.feature_indices(left)[0])
    right_address = int(result.model.feature_indices(right)[0])
    assert left_address < bank_size <= right_address
    assert right_address-left_address == bank_size


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_update_uses_one_error_and_exact_context_feature_multiplicity(representation):
    result = model(representation)
    before = result.weights.copy()
    source_before = result.parent.source.weights.copy()
    features = [int(address) for address in result.model.feature_indices(SPARSE)]
    counts = Counter(features)
    expected_prediction = 0.
    for address in features:
        expected_prediction += before.reshape(-1)[address]
    target = 1.3
    expected_error = (target-result.offset)-expected_prediction
    expected = before.copy().reshape(-1)
    for address, multiplicity in counts.items():
        expected[address] += ALPHA*expected_error*multiplicity
    update = result.update(SPARSE, target)
    assert update['error'] == expected_error
    assert update['raw_target'] == target-result.offset
    np.testing.assert_array_equal(result.weights.reshape(-1), expected)
    np.testing.assert_array_equal(result.parent.source.weights, source_before)
    assert result.counts['inner_table_update_occurrences'] == 32
    assert result.counts['inner_table_updates'] == len(counts) < 32
    assert result.counts['inner_update_feature_squared_norm'] == sum(n*n for n in counts.values())
    bank_size = result.parent.source.weights.size
    for bank in (0, 1):
        assert result.counts[f'inner_bank_{bank}_update_occurrences'] == sum(
            n for address, n in counts.items() if address//bank_size == bank)
        assert result.counts[f'inner_bank_{bank}_unique_updates'] == sum(
            address//bank_size == bank for address in counts)
    assert result.counts['inner_context_cell_reads'] == (16 if representation == 'GLOBAL' else 32)
    assert result.counts['inner_context_bank_selections'] == (1 if representation == 'GLOBAL' else 32)
    assert result.counts['inner_context_bank_offset_additions'] == 32


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_an_unselected_bank_is_unchanged_and_goal_bypasses_context(representation):
    result = model(representation)
    unselected = result.weights[1].copy()
    result.update([0]*16, .7)
    np.testing.assert_array_equal(result.weights[1], unselected)
    assert result.counts['inner_bank_0_update_occurrences'] == 32
    assert result.counts['inner_bank_1_update_occurrences'] == 0
    before = result.counts.copy()
    choice = result.choose([4]+[0]*15)
    assert choice['value'] == 8. and choice['status'] == 'WON'
    assert result.counts['inner_context_cell_reads'] == before['inner_context_cell_reads']


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_sparse_checkpoint_preserves_banks_representation_offset_and_freeze(tmp_path, representation):
    result = model(representation)
    result.update(SPARSE, 1.7)
    result.update(DENSE, -3.)
    result.freeze()
    saved = result.save(tmp_path/f'{representation}.npz')
    sidecar = json.loads(Path(saved['sidecar']).read_text())
    assert sidecar['representation'] == representation
    assert sidecar['context_spec'] == dict(global_empty_threshold=4, capacity_extra_cells=[3, 7, 6, 10])
    assert sidecar['schema'] == core.SCHEMA
    assert saved['parameter_count'] == result.weights.size
    assert result.counts['inner_checkpoint_scanned_parameters'] == result.weights.size
    restored = core.ConditionalQueryTD.load(saved['path'], result.parent, BUILD)
    MODELS.append(restored)
    assert restored.representation == representation and not restored.weights.flags.writeable
    assert restored.offset == result.offset and restored.updates == 2
    np.testing.assert_array_equal(restored.weights, result.weights)
    for board in (SPARSE, DENSE, [3, 3]+[0]*14):
        assert_choices(restored.choose(board), result.choose(board))
    with pytest.raises(RuntimeError, match='frozen'):
        restored.update(SPARSE, .1)


@pytest.mark.parametrize('representation', ['GLOBAL', 'CAPACITY'])
def test_original_single_step_stream_resumes_pending_td_with_contextual_weights(monkeypatch, representation):
    def scripted_spawn(board, rng, work, p_four):
        board = list(board)
        cell = board.index(0)
        board[cell] = 1
        work['scripted_spawn_calls'] += 1
        return tuple(board), cell, 1

    def scripted_status(board, work):
        work['scripted_status_calls'] += 1
        return 'WON' if max(board) >= 4 else 'ACTIVE'

    monkeypatch.setattr(single, '_spawn', scripted_spawn)
    monkeypatch.setattr(single, '_status', scripted_status)
    source = parent()
    whole = single.TDStream(model(representation, source), lambda episode: 134000+episode)
    split = single.TDStream(model(representation, source), lambda episode: 134000+episode)
    STREAMS.extend((whole, split))
    expected = whole.advance(3)
    prefix = split.advance(1)
    pending = split.pending
    actual = prefix+split.advance(2)
    assert prefix[0]['pending_after'] == actual[1]['pending_before'] == list(pending)
    for field in ('actions', 'chosen_values', 'scores', 'td_targets', 'raw_td_targets', 'td_errors'):
        assert [value for row in actual for value in row[field]] == [
            value for row in expected for value in row[field]]
    np.testing.assert_array_equal(whole.model.weights, split.model.weights)
    assert whole.model.updates == split.model.updates == 2
    assert whole.environment_counts == split.environment_counts
    assert whole.training_counts == split.training_counts
    assert whole.model.counts['inner_table_update_occurrences'] == 64
