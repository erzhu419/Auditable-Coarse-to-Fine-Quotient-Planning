"""Lazy execution preserves existing semantics and charges actual work."""
from collections import Counter
import json
import weakref

import pytest

from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, FEATURE_NAMES, RuleEncoder
from acfqp.science import controlled_predictive_encoder_runtime_v8 as eager
from acfqp.science.controlled_predictive_encoder_runtime_v10 import FeatureCache, RuntimeEncoder, compile_encoded
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, plan


SINGLE = (0,) * 5 + (1,) + (0,) * 10
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
WON = (11,) + (0,) * 15


@pytest.mark.parametrize("board", [*PUBLIC_DEVELOPMENT_BOARDS.values(), SINGLE, (1,) + (0,) * 15])
def test_all_31_requested_features_and_groups_exactly_equal_eager(board):
    work = Counter()
    cache = FeatureCache(work)
    group, lazy = cache.profile(board, 3)
    expected_group, expected_features = eager.profile(board, 3, Counter())
    assert group == expected_group
    assert tuple(lazy) == expected_features
    assert len(lazy) == len(FEATURE_NAMES) == 31
    assert work["feature_values_computed"] == 31
    assert work["fully_materialized_board_feature_vectors"] == 1
    assert work["deterministic_swipe_calls"] == 4
    assert work["board_cache_entry_validations"] == 1
    assert work["swipe_internal_board_validations"] == 4
    assert work["board_validations"] == 5
    assert tuple(lazy) == expected_features
    assert work["feature_values_computed"] == 31
    assert work["feature_value_cache_hits"] == 31


def test_horizon_zero_then_active_reuses_existing_swipe_and_board_validation():
    work = Counter()
    cache = FeatureCache(work)
    group, features = cache.profile(SINGLE, 0)
    assert group == (0, "CUTOFF", ()) and features == ()
    assert work["deterministic_swipe_calls"] == 1
    group, lazy = cache.profile(SINGLE, 2)
    assert group == (2, "ACTIVE", ACTIONS)
    assert work["deterministic_swipe_calls"] == 4
    assert work["swipe_cache_hits"] == 1
    assert work["board_cache_entry_validations"] == work["board_maximum_scans"] == 1
    assert work["feature_values_computed"] == 0
    assert lazy[1] == 1
    assert work["feature_values_computed"] == 1
    cache.profile(SINGLE, 0)
    assert work["deterministic_swipe_calls"] == 4
    assert cache.diagnostics()["board_entries"] == 1
    assert work["board_cache_hits"] == 2


@pytest.mark.parametrize("board,status,swipes", [(WON, "WON", 0), (LOST, "LOST", 4)])
def test_terminal_precedence_is_stable_across_horizons_without_features(board, status, swipes):
    work = Counter()
    cache = FeatureCache(work)
    for horizon in (0, 3, 0):
        assert cache.profile(board, horizon) == ((horizon, status, ()), ())
    assert work["deterministic_swipe_calls"] == swipes
    assert work["feature_values_computed"] == 0
    assert cache.diagnostics()["scalar_feature_values_cached"] == 0
    assert work["board_cache_entry_validations"] == 1


def test_constant_rule_requests_zero_features_and_path_only_computes_needed_scalar():
    work = Counter()
    cache = FeatureCache(work)
    constant = RuntimeEncoder({(3, "ACTIVE", ACTIONS): {"leaf": 5}})
    assert cache.encode(constant, SINGLE, 3)[-1] == 5
    assert work["feature_value_requests"] == work["feature_values_computed"] == 0
    path = RuntimeEncoder({(3, "ACTIVE", ACTIONS): {
        "feature": 1, "threshold": 1.5, "left": {"leaf": 7}, "right": {"leaf": 9}}})
    assert cache.encode(path, SINGLE, 3)[-1] == 7
    assert work["feature_value_requests"] == work["feature_values_computed"] == 1
    assert work["fully_materialized_board_feature_vectors"] == 0


def _model():
    model = FiniteModel({0: 2, 1: 1, 2: 0}, {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF"},
        {(state, action): (Outcome(1, state + 1, 0),) for state in (0, 1) for action in ACTIONS}, (0,))
    trees = {(2, "ACTIVE", ACTIONS): {"leaf": 0},
             (1, "ACTIVE", ACTIONS): {"feature": 1, "threshold": 1.5,
                "left": {"leaf": 2}, "right": {"leaf": 3}}}
    return model, {state: SINGLE for state in model.layers}, RuntimeEncoder(trees)


def test_compile_cache_reuses_same_board_across_horizons_and_is_fresh_per_build():
    model, boards, encoder = _model()
    built = compile_encoded(model, boards, encoder)
    again = compile_encoded(model, boards, encoder)
    old = eager.compile_encoded(model, boards, encoder)
    assert built.compiled == old.compiled
    assert built.code_to_cell == old.code_to_cell
    assert built.diagnostics["work_counts"] == again.diagnostics["work_counts"]
    work = built.diagnostics["work_counts"]
    assert work["states_profiled"] == 3
    assert work["board_cache_entries"] == work["board_cache_misses"] == 1
    assert work["board_cache_hits"] == 2
    assert work["deterministic_swipe_calls"] == 4
    assert work["feature_values_computed"] == 1
    assert work["pooling_action_rows_read"] == len(model.rows)
    assert built.diagnostics["cache"]["scalar_feature_values_cached"] == 1


def test_v7_payload_reloads_into_lazy_runtime_and_preserves_code_and_planning():
    model, boards, encoder = _model()
    payload = json.loads(json.dumps(encoder.to_payload()))
    restored = RuntimeEncoder.from_payload(payload)
    eager_encoder = RuleEncoder.from_payload(payload)
    assert isinstance(restored, RuntimeEncoder)
    for horizon in (0, 1, 2, 3):
        assert restored.encode(SINGLE, horizon) == eager_encoder.encode(SINGLE, horizon)
    compiled = compile_encoded(model, boards, restored).compiled
    expected = eager.compile_encoded(model, boards, eager_encoder).compiled
    assert plan(compiled, Query(1, .3, .2)) == plan(expected, Query(1, .3, .2))
    assert set(payload) == {"schema", "feature_names", "trees", "unseen_active_group_leaf"}


def test_board_entry_is_released_without_waiting_for_cyclic_gc_after_build_scope():
    cache = FeatureCache(Counter())
    _, features = cache.profile(SINGLE, 2)
    entry = weakref.ref(features._entry)
    features[1]
    del features
    del cache
    assert entry() is None
