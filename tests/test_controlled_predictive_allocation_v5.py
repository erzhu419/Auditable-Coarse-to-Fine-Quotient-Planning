from __future__ import annotations

import pytest

from acfqp.science.controlled_predictive_allocation_v5 import (
    _integer_allocation,
    plan_allocations,
    signed_policy_gap_influences,
)
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _downstream_model() -> FiniteModel:
    return FiniteModel(
        {0: 2, 1: 1, 2: 1, 3: 0},
        {0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "CUTOFF"},
        {(0, "RISK"): (Outcome(1, 1, 0),),
         (0, "SAFE"): (Outcome(1, 2, 0),),
         (1, "DRAW"): (Outcome(0.5, 3, 0), Outcome(0.5, 3, 1)),
         (2, "DRAW"): (Outcome(1, 3, 0.45),)}, (0,),
    )


def test_identical_future_occupancies_cancel_before_variance_is_squared() -> None:
    """A noisy future common to both actions must not create gap uncertainty."""
    model = FiniteModel(
        {0: 2, 1: 1, 2: 0}, {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF"},
        {(0, "A"): (Outcome(1, 1, 0),), (0, "B"): (Outcome(1, 1, 0),),
         (1, "DRAW"): (Outcome(0.5, 2, 0), Outcome(0.5, 2, 1))}, (0,),
    )
    influence, work = signed_policy_gap_influences(model, {0: "A", 1: "DRAW"}, 0, "A", "B")
    assert influence == {(0, "A"): -1.0, (0, "B"): 1.0}
    assert work["cancelled_states"] == 1
    result = plan_allocations(model, dict.fromkeys(model.rows, 64), {"reward": Query()})
    pair, = result.pair_diagnostics
    assert pair["standard_error"] == 0
    assert not pair["ambiguous"]
    assert result.diagnostics["uniform_fallback"]
    assert result.diagnostics["query_summaries"]["reward"]["rows_with_zero_observed_target_variance"] == 2


def test_downstream_row_variance_directs_parent_action_gap_measurement() -> None:
    """Root rows can be deterministic while the action ranking is uncertain downstream."""
    model = _downstream_model()
    result = plan_allocations(model, dict.fromkeys(model.rows, 64), {"reward": Query()})
    pair, = result.pair_diagnostics
    assert pair["predicted_gap"] == pytest.approx(0.05)
    assert pair["gap_variance"] == pytest.approx(1 / 252)  # Unbiased Bernoulli variance / 64.
    assert pair["ambiguous"]
    assert result.allocations[256] == {
        (0, "RISK"): 128, (0, "SAFE"): 128, (1, "DRAW"): 640, (2, "DRAW"): 128}
    for budget, allocation in result.allocations.items():
        assert sum(allocation.values()) == budget * len(model.rows)
        assert min(allocation.values()) >= budget // 2
    assert all(result.allocations[1024][row] >= count for row, count in result.allocations[256].items())
    assert result.diagnostics["work_counts"]["nominal_dp_and_variance"]["dp_state_action_rows"] == 4
    assert result.diagnostics["allocation_summaries"][256]["by_layer"][1]["mean_row_count"] == 384


def test_all_covered_states_and_queries_contribute_without_root_reach_weighting() -> None:
    """A pilot-unreachable decision must not disappear from the all-state objective."""
    source = _downstream_model()
    model = FiniteModel(
        {**source.layers, 4: 1}, {**source.terminal, 4: "ACTIVE"},
        {**source.rows, (4, "A"): (Outcome(0.5, 3, 0), Outcome(0.5, 3, 1)),
         (4, "B"): (Outcome(1, 3, 0.49),)}, source.roots)
    result = plan_allocations(model, dict.fromkeys(model.rows, 64),
                              {"reward": Query(), "scaled_reward": Query(2, 0, 0)})
    assert {(pair["query"], pair["state"]) for pair in result.pair_diagnostics} == {
        ("reward", 0), ("reward", 4), ("scaled_reward", 0), ("scaled_reward", 4)}
    assert result.allocations[256][4, "A"] > 128
    assert result.diagnostics["query_names"] == ["reward", "scaled_reward"]


def test_largest_remainders_have_fixed_sorted_ties_and_exact_budgets() -> None:
    """Integer rounding must not overspend or give dictionary order the tie break."""
    scores = {(2, "A"): 9.0, (1, "A"): 1.0, (0, "A"): 1.0}
    result = _integer_allocation(scores, 258)
    assert result == {(0, "A"): 207, (1, "A"): 206, (2, "A"): 361}
    assert result == _integer_allocation(dict(reversed(list(scores.items()))), 258)
    assert sum(result.values()) == 774


def test_zero_observed_variance_falls_back_and_never_claims_no_risk() -> None:
    """A pilot containing one observed outcome per row has no variance evidence."""
    model = FiniteModel(
        {0: 1, 1: 0, 2: 0}, {0: "ACTIVE", 1: "CUTOFF", 2: "LOST"},
        {(0, "A"): (Outcome(1, 1, 0.1),), (0, "B"): (Outcome(1, 1, 0),)}, (0,),
    )
    result = plan_allocations(model, dict.fromkeys(model.rows, 64), {"risk": Query(1, 1, 0)})
    assert result.diagnostics["uniform_fallback_reason"] == "no_positive_observed_score"
    assert result.diagnostics["ambiguous_pairs"] == 0
    assert result.allocations == {256: {(0, "A"): 256, (0, "B"): 256},
                                  1024: {(0, "A"): 1024, (0, "B"): 1024}}
    assert result.diagnostics["uncertainty_interpretation"] == "first_order_fixed_policy_heuristic_not_confidence_bound"


def test_declared_floor_must_preserve_all_pilot_observations() -> None:
    """An allocation cannot retroactively discard already consumed pilot samples."""
    model = _downstream_model()
    with pytest.raises(ValueError, match="floors covering the pilot"):
        plan_allocations(model, dict.fromkeys(model.rows, 129), {"reward": Query()}, (256,))
