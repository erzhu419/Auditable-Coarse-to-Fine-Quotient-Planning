"""Block construction must preserve V9 rules and empirical policies."""
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_adaptation_v9 as eager
from acfqp.science import controlled_predictive_adaptation_v11 as block
from acfqp.science.controlled_predictive_encoder_runtime_v8 import RuntimeEncoder
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, TrainingModel
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, plan


GROUP = (1, "ACTIVE", ACTIONS)
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)


def _board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


def _target(kind):
    boards = {0: _board(1), 1: _board(1 if kind == "collision" else 2), 2: _board(1), 3: LOST}
    rows = {(state, action): (Outcome(1, 2 if action == (
        "UP" if state == 0 or kind == "pure" else "DOWN") else 3, 0),)
        for state in (0, 1) for action in ACTIONS}
    layers = {0: 1, 1: 1, 2: 0, 3: 0}
    terminal = {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF", 3: "LOST"}
    if kind == "delayed":
        boards.update({4: _board(1), 5: _board(2)})
        layers.update({4: 2, 5: 2})
        terminal.update({4: "ACTIVE", 5: "ACTIVE"})
        rows.update({(state, action): (Outcome(1, state - 4, 0),)
                     for state in (4, 5) for action in ACTIONS})
    return TrainingModel("target", FiniteModel(layers, terminal, rows, (0, 1)), boards)


def _source(kind):
    tree = ({"feature": 1, "threshold": 3.5,
             "left": {"leaf": 7}, "right": {"leaf": 7}} if kind == "shared"
            else {"feature": 1, "threshold": 2.5,
                  "left": {"leaf": 0}, "right": {"leaf": 1}} if kind == "unused_code"
            else {"leaf": 7})
    return RuntimeEncoder({GROUP: tree, (2, "ACTIVE", ACTIONS): {"leaf": 9},
                           (0, "CUTOFF", ()): {"leaf": 0}, (0, "LOST", ()): {"leaf": 0}})


@pytest.mark.parametrize("kind", ["pure", "mixed", "delayed", "collision", "shared", "unused_code"])
def test_block_build_preserves_eager_tree_model_constraints_and_policies(kind):
    target, source = _target(kind), _source(kind)
    source_before = deepcopy(source.to_payload())
    for build_name in ("build_adapted_target", "build_scratch_target"):
        args = (source, target) if build_name == "build_adapted_target" else (target,)
        old, new = getattr(eager, build_name)(*args), getattr(block, build_name)(*args)
        assert new.encoder.to_payload() == old.encoder.to_payload()
        assert new.compiled == old.compiled
        assert new.code_to_cell == old.code_to_cell
        assert new.diagnostics["groups"] == old.diagnostics["groups"]
        for field in ("unresolved_signature_pairs", "identical_feature_conflicting_pairs",
                      "all_target_predictive_constraints_satisfied", "recursive_empirical_equivalence_supported"):
            assert new.diagnostics[field] == old.diagnostics[field]
        for query in (Query(), Query(1, .37, .2), Query(.5, 5, 1)):
            assert plan(new.compiled, query) == plan(old.compiled, query)
        assert new.diagnostics["work_counts"]["target_validation_action_rows_read"] == len(target.empirical.rows)
        assert new.diagnostics["work_counts"]["pooling_action_rows_read"] == len(target.empirical.rows)
    assert source.to_payload() == source_before


def test_pure_signature_audit_does_not_force_unused_feature_materialization():
    target = _target("pure")
    for built in (block.build_adapted_target(_source("pure"), target), block.build_scratch_target(target)):
        storage = built.diagnostics["feature_storage"]
        assert storage["scalar_feature_values_computed"] == 0
        assert storage["fully_materialized_state_feature_vectors"] == 0
        assert built.diagnostics["work_counts"]["pure_group_full_feature_vectors_not_requested"] == 2
        assert built.diagnostics["work_counts"].get("mixed_group_feature_vector_materializations", 0) == 0


def test_source_path_requests_only_its_feature_block_and_each_build_is_independent():
    source, target = _source("shared"), _target("pure")
    first = block.build_adapted_target(source, target)
    second = block.build_adapted_target(source, target)
    storage = first.diagnostics["feature_storage"]
    assert storage["scalar_feature_values_computed"] == 14
    assert storage["feature_blocks_computed"] == 2
    assert storage["fully_materialized_state_feature_vectors"] == 0
    assert storage == second.diagnostics["feature_storage"]
    assert first.diagnostics["work_counts"] == second.diagnostics["work_counts"]
    assert first.encoder.to_payload() == source.to_payload()


def test_active_contexts_are_per_state_without_cross_horizon_board_sharing():
    target = _target("delayed")
    built = block.build_scratch_target(target)
    storage = built.diagnostics["feature_storage"]
    assert storage["active_feature_contexts_created"] == 4
    assert storage["terminal_feature_contexts_created"] == 0
    assert storage["aggregate_swipe_results_stored"] == 16
    assert storage["fully_materialized_state_feature_vectors"] == 4
    assert storage["scalar_feature_values_computed"] == 124
    assert built.diagnostics["work_counts"]["deterministic_swipe_calls"] == 21
