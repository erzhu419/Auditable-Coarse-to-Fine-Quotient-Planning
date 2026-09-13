"""V8 runtime checks target terminal precedence and executable-model equivalence."""

from collections import Counter
import json
from unittest.mock import patch

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_encoder_io_v7 import freeze_artifact_payload, restore_artifact_payload
from acfqp.science.controlled_predictive_encoder_runtime_v8 import RuntimeEncoder, compile_encoded, profile
from acfqp.science.controlled_predictive_encoder_v7 import (
    ACTIONS, RuleEncoder, TrainingModel, _profile,
    compile_encoded as compile_v7, fit_encoder,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query, plan, sample_model


LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
WON = (11, *LOST[1:])
ACTIVE = (0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.parametrize("board,horizon,status", [
    (ACTIVE, 3, "ACTIVE"),
    ((8, 8, 5, 7, 2, 4, 6, 1, 6, 3, 9, 5, 3, 9, 5, 8), 3, "ACTIVE"),
    (LOST, 0, "LOST"), (LOST, 2, "LOST"),
    (ACTIVE, 0, "CUTOFF"), (WON, 0, "WON"), (WON, 2, "WON"),
])
def test_profile_keeps_active_features_and_terminal_precedence(board, horizon, status):
    """A changed status or ACTIVE feature would alter the frozen encoder codes."""
    work = Counter()
    before_group, before_features = _profile(board, horizon, Counter())
    group, features = profile(board, horizon, work)
    assert group == before_group
    assert group[1] == status
    if status == "ACTIVE":
        assert features == before_features
        assert len(features) == work["feature_values_computed"] == 31
        assert work["deterministic_swipe_calls"] == 4
    else:
        assert features == ()
        assert work["feature_extractions"] == work["feature_values_computed"] == 0
        assert work["terminal_feature_vectors_skipped"] == 1
        assert work["deterministic_swipe_calls"] == (0 if status == "WON" else 1 if status == "CUTOFF" else 4)


def test_codes_and_portable_payload_stay_compatible_without_stochastic_execution():
    """The optimization must execute existing trees and preserve unseen-group fallback."""
    trees = {(3, "ACTIVE", ACTIONS): {"feature": 1, "threshold": 1.5,
                                      "left": {"leaf": 4}, "right": {"leaf": 8}}}
    old = RuleEncoder(trees)
    runtime = RuntimeEncoder.from_payload(json.loads(json.dumps(old.to_payload())))
    assert type(runtime) is RuntimeEncoder
    assert runtime.to_payload() == old.to_payload()
    inputs = [(ACTIVE, 3), (ACTIVE, 2), (ACTIVE, 0), (LOST, 0), (WON, 0),
              (tuple(2 if value == 1 else value for value in ACTIVE), 3)]
    with patch("acfqp.domains.standard_2048.step_v1", side_effect=AssertionError("stochastic step")), \
         patch("acfqp.domains.standard_2048.support_outcomes_v1", side_effect=AssertionError("stochastic support")):
        assert [runtime.encode(*item) for item in inputs] == [old.encode(*item) for item in inputs]


def test_compiler_keeps_partition_rows_and_plans_while_skipping_terminal_features():
    """Optimized pooling must preserve all model dynamics, not just root actions."""
    closure = build_development_closure(
        boards={"small": (1, 1, *([0] * 14)), "large": (2, 2, *([0] * 14)),
                "lost": LOST, "won": WON}, horizon=1, max_nodes=1000)
    empirical = sample_model(closure.model, 16, seed=31)
    fit = fit_encoder([TrainingModel("fixture", empirical, closure.boards)], min_leaf=1)
    old = compile_v7(empirical, closure.boards, fit.encoder)
    runtime = RuntimeEncoder.from_payload(fit.encoder.to_payload())
    fast = compile_encoded(empirical, closure.boards, runtime)
    assert fast.compiled == old.compiled
    assert fast.code_to_cell == old.code_to_cell
    for query in (Query(), Query(1, .3, .2), Query(1, 5, 0)):
        assert plan(fast.compiled, query) == plan(old.compiled, query)
    count = fast.diagnostics["work_counts"]
    active = sum(status == "ACTIVE" for status in empirical.terminal.values())
    assert count["feature_extractions"] == active
    assert count["feature_values_computed"] == 31 * active
    assert count["feature_values_computed"] < old.diagnostics["work_counts"]["feature_values_computed"]
    assert count["pooling_action_rows_read"] == len(empirical.rows)
    assert count["pooling_successor_entries_read"] == sum(map(len, empirical.rows.values()))
    payload = freeze_artifact_payload(runtime, fast.compiled, fast.code_to_cell)
    restored, model, code_map = restore_artifact_payload(payload)
    for root in empirical.roots:
        assert restored.encode(closure.boards[root], empirical.layers[root]) == runtime.encode(closure.boards[root], empirical.layers[root])
    assert model.rows == fast.compiled.rows and code_map == fast.code_to_cell
