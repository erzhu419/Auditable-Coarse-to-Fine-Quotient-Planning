"""Block execution preserves features and rules without a cross-state cache."""

from collections import Counter
import json
import weakref

import pytest

from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, FEATURE_NAMES, RuleEncoder
from acfqp.science import controlled_predictive_encoder_runtime_v8 as eager
from acfqp.science import controlled_predictive_encoder_runtime_v11 as blocks
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, plan


SINGLE = (0,) * 5 + (1,) + (0,) * 10
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
WON = (11,) + (0,) * 15


@pytest.mark.parametrize("board", [*PUBLIC_DEVELOPMENT_BOARDS.values(), SINGLE, (1,) + (0,) * 15])
def test_full_materialization_equals_v8_features_and_batches_missing_blocks(board, monkeypatch):
    work = Counter()
    group, features = blocks.profile(board, 3, work)
    expected_group, expected = eager.profile(board, 3, Counter())
    assert group == expected_group and len(features) == len(FEATURE_NAMES) == 31
    assert features[1] == expected[1]
    assert features[6] == expected[6]
    assert work["feature_blocks_computed"] == 1
    assert work["feature_values_computed"] == 7
    assert work["feature_block_cache_hits"] == 1

    def scalar_dispatch_forbidden(*args):
        raise AssertionError("materialize must not iterate through scalar __getitem__")

    monkeypatch.setattr(blocks.BlockFeatures, "__getitem__", scalar_dispatch_forbidden)
    materialized = features.materialize()
    assert materialized == expected
    assert features.materialize() is materialized
    assert work["feature_value_requests"] == 2
    assert work["feature_values_computed"] == 31
    assert work["feature_blocks_computed"] == 5
    assert work["global_feature_blocks_computed"] == 1
    assert work["action_feature_blocks_computed"] == 4
    assert work["feature_materialization_calls"] == 2
    assert work["feature_materialization_cache_hits"] == 1
    assert work["fully_materialized_state_feature_vectors"] == 1
    assert work["adjacent_pair_tests"] == 120
    assert work["post_swipe_empty_adjacency_feature_calls"] == 8
    assert work["deterministic_swipe_calls"] == 4
    assert work["profile_board_validations"] == 1
    assert work["swipe_internal_board_validations"] == 4
    assert work["board_validations"] == 5


@pytest.mark.parametrize("board,horizon,status,swipes", [
    (WON, 0, "WON", 0), (WON, 3, "WON", 0),
    (LOST, 0, "LOST", 4), (LOST, 3, "LOST", 4), (SINGLE, 0, "CUTOFF", 1),
])
def test_terminals_preserve_short_circuit_and_never_create_feature_context(board, horizon, status, swipes, monkeypatch):
    def no_terminal_context(*args):
        raise AssertionError("terminal states must not create BlockFeatures")

    monkeypatch.setattr(blocks, "BlockFeatures", no_terminal_context)
    work = Counter()
    assert blocks.profile(board, horizon, work) == ((horizon, status, ()), ())
    assert work["deterministic_swipe_calls"] == swipes
    assert work["feature_values_computed"] == 0
    summary = blocks.feature_work_summary(work)
    assert summary["active_feature_contexts_created"] == 0
    assert summary["terminal_feature_contexts_created"] == 0
    assert summary["aggregate_swipe_results_stored"] == 0


def test_action_path_computes_one_six_feature_block_and_constant_rule_needs_none():
    work = Counter()
    group, features = blocks.profile(SINGLE, 3, work)
    constant = blocks.RuntimeEncoder({group: {"leaf": 5}})
    assert constant._encode_profile(group, features, work)[-1] == 5
    assert work["feature_value_requests"] == work["feature_values_computed"] == 0
    assert features[7] == 0
    assert features[12] == eager.profile(SINGLE, 3, Counter())[1][12]
    assert work["feature_blocks_computed"] == 1
    assert work["feature_values_computed"] == 6
    assert work["feature_block_cache_hits"] == 1
    assert work["deterministic_swipe_calls"] == 4
    assert work["global_feature_blocks_computed"] == 0


def test_repeated_board_gets_independent_contexts_across_states_and_horizons():
    work = Counter()
    assert blocks.profile(SINGLE, 0, work)[0] == (0, "CUTOFF", ())
    _, first = blocks.profile(SINGLE, 1, work)
    _, second = blocks.profile(SINGLE, 2, work)
    assert first is not second
    assert first._blocks is not second._blocks
    assert first[1] == second[1] == 1
    assert work["states_profiled"] == 3
    assert work["deterministic_swipe_calls"] == 9
    assert work["profile_board_validations"] == 3
    assert work["feature_values_computed"] == 14
    assert blocks.feature_work_summary(work)["aggregate_swipe_results_stored"] == 8
    reference = weakref.ref(first)
    del first
    assert reference() is None


def _model():
    model = FiniteModel({0: 2, 1: 1, 2: 0}, {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF"},
        {(state, action): (Outcome(1, state + 1, 0),) for state in (0, 1) for action in ACTIONS}, (0,))
    trees = {(2, "ACTIVE", ACTIONS): {"leaf": 0},
             (1, "ACTIVE", ACTIONS): {"feature": 1, "threshold": 1.5,
                "left": {"leaf": 2}, "right": {"leaf": 3}}}
    return model, {state: SINGLE for state in model.layers}, blocks.RuntimeEncoder(trees)


def test_compilation_and_portable_rule_execution_equal_eager_with_no_cross_state_reuse():
    model, boards, encoder = _model()
    payload = json.loads(json.dumps(encoder.to_payload()))
    restored = blocks.RuntimeEncoder.from_payload(payload)
    old = RuleEncoder.from_payload(payload)
    assert isinstance(restored, blocks.RuntimeEncoder)
    for board in (SINGLE, (2,) + (0,) * 15):
        for horizon in (0, 1, 2, 3):
            assert restored.encode(board, horizon) == old.encode(board, horizon)
    built = blocks.compile_encoded(model, boards, restored)
    expected = eager.compile_encoded(model, boards, old)
    assert built.compiled == expected.compiled
    assert built.code_to_cell == expected.code_to_cell
    assert plan(built.compiled, Query(1, .3, .2)) == plan(expected.compiled, Query(1, .3, .2))
    work = built.diagnostics["work_counts"]
    assert work["states_profiled"] == 3
    assert work["deterministic_swipe_calls"] == 9
    assert work["feature_values_computed"] == 7
    assert work["pooling_action_rows_read"] == len(model.rows)
    assert built.diagnostics["feature_work_summary"]["active_feature_contexts_created"] == 2
    assert set(payload) == {"schema", "feature_names", "trees", "unseen_active_group_leaf"}
