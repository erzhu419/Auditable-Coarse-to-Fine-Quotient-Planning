from dataclasses import replace
import math

import pytest

from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel,
    Outcome,
    Query,
    action_outcome_shuffle,
    audit_policy,
    build_quotient,
    compile_full_state,
    conflict_witness,
    evaluate_compiled_policy,
    plan,
    sample_model,
)


def swapped_actions() -> FiniteModel:
    return FiniteModel(
        {0: 1, 1: 1, 2: 0}, {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF"},
        {(0, "a"): (Outcome(1, 2, 1),), (0, "b"): (Outcome(1, 2, 0),),
         (1, "a"): (Outcome(1, 2, 0),), (1, "b"): (Outcome(1, 2, 1),)}, (0, 1),
    )


def two_step() -> FiniteModel:
    return FiniteModel(
        {0: 2, 1: 2, 2: 1, 3: 1, 4: 0, 5: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE", 4: "WON", 5: "LOST"},
        {(0, "a"): (Outcome(1, 2, 0),), (1, "a"): (Outcome(1, 3, 0),),
         (2, "a"): (Outcome(1, 4, 1),), (3, "a"): (Outcome(1, 5, 0),)}, (0, 1),
    )


def test_equal_optimal_value_does_not_merge_action_swapped_states():
    model = swapped_actions()
    quotient = build_quotient(model)
    result = plan(quotient)
    left, right = (quotient.state_to_cell[s] for s in model.roots)
    assert result.values[left] == result.values[right] == 1
    assert left != right
    assert result.policy[left] == "a"
    assert result.policy[right] == "b"


def test_two_step_recursive_conflict_and_exact_policy_audit():
    model = two_step()
    quotient = build_quotient(model)
    assert quotient.state_to_cell[0] != quotient.state_to_cell[1]
    witness = conflict_witness(model, quotient, 0, 1)
    assert witness["reward_difference"] == 0
    assert witness["total_variation"] == 1
    query = Query(reward_weight=2, failure_penalty=3, goal_bonus=5)
    result = plan(quotient, query)
    audit = audit_policy(model, quotient, result, query)
    assert audit.root_metrics[0] == {"reward": 1, "failure": 0, "success": 1, "value": 7}
    assert audit.root_metrics[1] == {"reward": 0, "failure": 1, "success": 0, "value": -3}
    assert all(result.values[quotient.state_to_cell[root]] == audit.root_metrics[root]["value"] for root in model.roots)
    assert audit.counts == {"active_states": 4, "state_action_rows": 4, "outcomes": 4, "visited_states": 6}


def test_complete_link_forbids_tolerance_chaining_and_compiles_mean_row():
    model = FiniteModel(
        {0: 1, 1: 1, 2: 1, 3: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "CUTOFF"},
        {(state, "a"): (Outcome(1, 3, reward),) for state, reward in enumerate((0, 0.09, 0.18))}, (0, 1, 2),
    )
    quotient = build_quotient(model, reward_tolerance=0.1)
    assert quotient.state_to_cell[0] == quotient.state_to_cell[1] != quotient.state_to_cell[2]
    merged = quotient.state_to_cell[0]
    assert quotient.diameters[merged] == {"reward": 0.09, "tv": 0}
    assert plan(quotient).values[merged] == pytest.approx(0.045)


def test_stochastic_kernel_sampling_reuse_and_complete_lifted_policy():
    model = FiniteModel(
        {0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "WON", 4: "LOST"},
        {(0, "a"): (Outcome(0.5, 1, 0), Outcome(0.5, 2, 0)),
         (1, "a"): (Outcome(1, 3, 2),), (2, "a"): (Outcome(1, 4, 0),)}, (0,),
    )
    sampled = sample_model(model, samples_per_row=1, seed=1)
    assert sampled == sample_model(model, samples_per_row=1, seed=1)
    assert len(sampled.rows[0, "a"]) == 1
    quotient = build_quotient(sampled)
    result = plan(quotient, Query(failure_penalty=4))
    audit = audit_policy(model, quotient, result, Query(failure_penalty=4))
    assert audit.root_metrics[0] == {"reward": 1, "failure": 0.5, "success": 0.5, "value": -1}
    assert result.counts["active_states"] == 3  # Includes child omitted by the sample.
    for compiled in (quotient, compile_full_state(sampled)):
        assert all(math.fsum(o.probability for o in row) == pytest.approx(1) for row in compiled.rows.values())


def test_total_variation_complete_link_and_terminal_distinctions():
    model = FiniteModel(
        {0: 1, 1: 1, 2: 1, 3: 0, 4: 0, 5: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "WON", 4: "LOST", 5: "CUTOFF"},
        {(s, "a"): (Outcome(p, 3, 0), Outcome(1 - p, 4, 0)) for s, p in enumerate((0.0, 0.09, 0.18))}, (0, 1, 2),
    )
    quotient = build_quotient(model, tv_tolerance=0.1)
    assert len({quotient.state_to_cell[state] for state in (0, 1, 2)}) == 2
    assert quotient.state_to_cell[0] != quotient.state_to_cell[2]
    assert len({quotient.state_to_cell[state] for state in (3, 4, 5)}) == 3
    assert max(d["tv"] for d in quotient.diameters.values()) == pytest.approx(0.09)


def test_legal_action_coverage_is_preserved_and_shuffle_breaks_control():
    model = swapped_actions()
    shuffled = action_outcome_shuffle(model)
    assert shuffled.rows.keys() == model.rows.keys()
    assert shuffled.rows[0, "a"] == model.rows[0, "b"]
    quotient = build_quotient(shuffled)
    audit = audit_policy(model, quotient, plan(quotient))
    assert audit.aggregate["reward"] == 0
    fewer_actions = replace(model, rows={key: row for key, row in model.rows.items() if key != (1, "a")})
    preserved = build_quotient(fewer_actions, 10, 1)
    assert preserved.state_to_cell[0] != preserved.state_to_cell[1]


def test_opaque_renaming_preserves_partition_and_executable_planning():
    model = two_step()
    renamed_ids = {state: 93 - state * 11 for state in model.layers}
    renamed = FiniteModel(
        {renamed_ids[s]: layer for s, layer in reversed(list(model.layers.items()))},
        {renamed_ids[s]: status for s, status in model.terminal.items()},
        {(renamed_ids[s], a): tuple(Outcome(o.probability, renamed_ids[o.next_state], o.reward) for o in reversed(row))
         for (s, a), row in reversed(list(model.rows.items()))}, tuple(renamed_ids[r] for r in model.roots),
    )
    original_quotient = build_quotient(model, 0.1, 0.2)
    renamed_quotient = build_quotient(renamed, 0.1, 0.2)
    assert all(original_quotient.state_to_cell[s] == renamed_quotient.state_to_cell[renamed_ids[s]] for s in model.layers)
    original_plan = plan(original_quotient)
    # The compiled representation remains executable after the source kernel is unavailable.
    model.rows.clear()
    assert plan(original_quotient) == original_plan
    assert plan(renamed_quotient).values == original_plan.values
    assert original_plan.counts == {"active_states": 4, "state_action_rows": 4, "outcomes": 4, "visited_cells": 6}


def test_kernel_rejects_invalid_probability_and_non_decreasing_horizon():
    model = swapped_actions()
    with pytest.raises(ValueError, match="probability mass"):
        replace(model, rows={**model.rows, (0, "a"): (Outcome(0.7, 2, 1),)})
    with pytest.raises(ValueError, match="remaining horizon"):
        replace(model, rows={**model.rows, (0, "a"): (Outcome(1, 1, 1),)})


def test_compiled_policy_components_match_objective_and_query_changes_action():
    model = FiniteModel(
        {0: 1, 1: 0, 2: 0, 3: 0},
        {0: "ACTIVE", 1: "WON", 2: "LOST", 3: "CUTOFF"},
        {(0, "risky"): (Outcome(0.5, 1, 2), Outcome(0.5, 2, 2)),
         (0, "safe"): (Outcome(1, 3, 1),)}, (0,),
    )
    compiled = build_quotient(model)
    root = compiled.state_to_cell[0]
    reward_plan = plan(compiled)
    assert reward_plan.policy[root] == "risky"
    predicted = evaluate_compiled_policy(compiled, reward_plan)
    assert predicted.root_metrics[root] == {"reward": 2, "failure": 0.5, "success": 0.5, "value": 2}
    assert predicted.root_metrics[root]["value"] == reward_plan.values[root]
    assert predicted.counts == {"active_states": 1, "state_action_rows": 1, "outcomes": 2, "visited_states": 3}
    cautious = Query(reward_weight=2, failure_penalty=6, goal_bonus=1)
    cautious_plan = plan(compiled, cautious)
    assert cautious_plan.policy[root] == "safe"
    predicted = evaluate_compiled_policy(compiled, cautious_plan, cautious)
    audited = audit_policy(model, compiled, cautious_plan, cautious)
    assert predicted.root_metrics[root] == audited.root_metrics[0]
    assert predicted.root_metrics[root]["value"] == cautious_plan.values[root] == 2
