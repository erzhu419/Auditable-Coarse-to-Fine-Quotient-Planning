"""Target rule repair tests exercise reachable partition and recursion errors."""
from copy import deepcopy
import json

import pytest

from acfqp.science.controlled_predictive_adaptation_v9 import build_adapted_target, build_scratch_target
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, TrainingModel
from acfqp.science.controlled_predictive_encoder_v8 import fit_constraint_encoder
from acfqp.science.controlled_predictive_encoder_runtime_v8 import RuntimeEncoder, compile_encoded
from acfqp.science.controlled_predictive_encoder_io_v7 import freeze_artifact_payload, restore_artifact_payload
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, compile_full_state, plan


def _board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
GROUP = (1, "ACTIVE", ACTIONS)


def _target(second_rank=2, *, delayed=False, same_outcomes=False):
    boards = {0: _board(1), 1: _board(second_rank), 2: _board(1), 3: LOST}
    rows = {}
    for state in (0, 1):
        for action in ACTIONS:
            safe_action = "UP" if state == 0 or same_outcomes else "DOWN"
            rows[state, action] = (Outcome(1, 2 if action == safe_action else 3, 0),)
    layers = {0: 1, 1: 1, 2: 0, 3: 0}
    terminal = {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF", 3: "LOST"}
    roots = (0, 1)
    if delayed:
        boards |= {4: _board(1), 5: _board(2)}
        layers |= {4: 2, 5: 2}
        terminal |= {4: "ACTIVE", 5: "ACTIVE"}
        rows |= {(state, action): (Outcome(1, state - 4, 0),)
                 for state in (4, 5) for action in ACTIONS}
        roots = (4, 5)
    return TrainingModel("current_target", FiniteModel(layers, terminal, rows, roots), boards)


def _source(tree=None, *, delayed=False):
    trees = {GROUP: {"leaf": 7} if tree is None else tree,
             (0, "CUTOFF", ()): {"leaf": 0}, (0, "LOST", ()): {"leaf": 0}}
    if delayed:
        trees[2, "ACTIVE", ACTIONS] = {"leaf": 9}
    return RuntimeEncoder(trees)


@pytest.mark.parametrize("second_rank,threshold,unvisited_patched", [(4, 2.5, 0), (2, 3.5, 1)])
def test_shared_output_code_patches_union_and_every_original_occurrence(second_rank, threshold, unvisited_patched):
    source = _source({"feature": 1, "threshold": threshold,
                      "left": {"leaf": 7}, "right": {"leaf": 7}})
    before = deepcopy(source.to_payload())
    target = _target(second_rank)
    built = build_adapted_target(source, target)
    assert source.to_payload() == before
    adapted_tree = built.encoder.trees[GROUP]
    assert adapted_tree["left"] == adapted_tree["right"]
    assert "feature" in adapted_tree["left"]
    assert built.encoder.encode(_board(1), 1) != built.encoder.encode(_board(second_rank), 1)
    assert built.diagnostics["repaired_source_code_groups"] == 1
    assert built.diagnostics["work_counts"]["rule_patch_occurrences_installed"] == 2
    assert built.diagnostics["unvisited_source_leaf_occurrences_patched_via_shared_code"] == unvisited_patched
    assert built.diagnostics["all_target_predictive_constraints_satisfied"]


def test_fresh_codes_cannot_collide_with_unvisited_original_output_code():
    source = _source({"feature": 1, "threshold": 2.5,
                      "left": {"leaf": 0}, "right": {"leaf": 1}})
    built = build_adapted_target(source, _target())
    assert built.encoder.encode(_board(3), 1)[-1] == 1
    assert {built.encoder.encode(_board(rank), 1)[-1] for rank in (1, 2)} == {2, 3}
    assert built.diagnostics["source_output_codes_without_target_records_retained"] == 1
    assert built.encoder.trees[GROUP]["right"] == source.trees[GROUP]["right"]


def test_pure_target_preserves_existing_rules_and_reads_rows_once_for_each_required_pass():
    source = _source()
    target = _target(same_outcomes=True)
    built = build_adapted_target(source, target)
    assert built.encoder.to_payload() == source.to_payload()
    assert built.diagnostics["repaired_source_code_groups"] == 0
    assert built.diagnostics["added_tree_nodes_including_new_groups"] == 0
    assert built.diagnostics["initial_active_cells"] == built.diagnostics["final_active_cells"] == 1
    work = built.diagnostics["work_counts"]
    assert work["states_profiled"] == len(target.empirical.layers)
    assert work["target_validation_action_rows_read"] == len(target.empirical.rows)
    assert work["pooling_action_rows_read"] == len(target.empirical.rows)
    assert work.get("tree_split_nodes_fitted", 0) == 0


def test_lower_code_change_triggers_upper_repair_before_single_final_pool():
    target = _target(delayed=True)
    built = build_adapted_target(_source(delayed=True), target)
    assert built.diagnostics["impure_base_code_groups_when_visited_by_layer"] == {1: 1, 2: 1}
    assert built.diagnostics["repaired_source_code_groups"] == 2
    assert built.encoder.encode(_board(1), 2) != built.encoder.encode(_board(2), 2)
    assert built.diagnostics["recursive_empirical_equivalence_supported"]
    reference = compile_full_state(target.empirical)
    for query in (Query(), Query(failure_penalty=.37), Query(.5, 2, 1)):
        full, candidate = plan(reference, query), plan(built.compiled, query)
        for state in target.empirical.layers:
            assert candidate.values[built.compiled.state_to_cell[state]] == pytest.approx(full.values[state])
    runtime_build = compile_encoded(target.empirical, target.boards, built.encoder)
    assert runtime_build.compiled.state_to_cell == built.compiled.state_to_cell
    assert runtime_build.compiled.rows == built.compiled.rows


def test_identical_feature_contradiction_retains_code_and_blocks_global_equivalence():
    target = _target(second_rank=1, delayed=True)
    source = _source(delayed=True)
    built = build_adapted_target(source, target)
    assert built.encoder.trees[GROUP] == {"leaf": 7}
    assert built.diagnostics["unresolved_signature_pairs"] == 1
    assert built.diagnostics["identical_feature_conflicting_pairs"] == 1
    assert not built.diagnostics["all_target_predictive_constraints_satisfied"]
    assert not built.diagnostics["recursive_empirical_equivalence_supported"]
    upper = next(group for group in built.diagnostics["groups"] if group["horizon"] == 2)
    assert upper["local_predictive_constraints_satisfied"]
    assert upper["unresolved_lower_horizon_group_present"]
    lower = next(group for group in built.diagnostics["groups"] if group["horizon"] == 1)
    record = lower["original_output_codes"][0]
    assert record["mixed_leaves"][0]["output_code"] == 7
    assert record["identical_feature_collision_witness"]["left"]["source_model"] == target.name


def test_shared_engine_scratch_matches_v8_constraint_partition_and_portable_reload():
    target = _target(delayed=True)
    built = build_scratch_target(target)
    previous_fit = fit_constraint_encoder([target])
    previous = compile_encoded(target.empirical, target.boards, previous_fit.encoder).compiled
    partition = lambda compiled: {frozenset(cell.members) for cell in compiled.cells.values()}
    assert partition(built.compiled) == partition(previous)
    assert built.diagnostics["source_unseen_active_group_states"] == 4
    assert built.diagnostics["work_counts"]["states_profiled"] == len(target.empirical.layers)
    root = target.empirical.roots[0]
    payload = freeze_artifact_payload(built.encoder, built.compiled, built.code_to_cell,
        example_board=target.boards[root], example_horizon=target.empirical.layers[root])
    restored_encoder, restored_model, restored_codes = restore_artifact_payload(json.loads(json.dumps(payload)))
    query = Query(1, .37, .2)
    code = restored_encoder.encode(target.boards[root], target.empirical.layers[root])
    restored = plan(restored_model, query)
    original = plan(built.compiled, query)
    assert restored.values[restored_codes[code]] == original.values[built.compiled.state_to_cell[root]]
    assert not restored_model.state_to_cell
    assert all(not cell.members for cell in restored_model.cells.values())


def test_partially_split_feature_collision_is_not_counted_as_fully_repaired():
    target = _target(second_rank=1)
    model = target.empirical
    rows = dict(model.rows) | {(4, action): model.rows[0, action] for action in ACTIONS}
    extended = TrainingModel(target.name, FiniteModel(model.layers | {4: 1},
        model.terminal | {4: "ACTIVE"}, rows, (0, 1, 4)), target.boards | {4: _board(2)})
    built = build_adapted_target(_source(), extended)
    assert built.diagnostics["refined_source_code_groups"] == 1
    assert built.diagnostics["repaired_source_code_groups"] == 0
    assert built.diagnostics["partially_repaired_source_code_groups"] == 1
    assert built.diagnostics["unresolved_signature_pairs"] == 1
    assert not built.diagnostics["all_target_predictive_constraints_satisfied"]
