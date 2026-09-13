from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp.science import controlled_predictive_characterization_v6 as characterization
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_challenges_v6 import V6Case
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query


def _closure(*, off_policy_only: bool = False) -> DevelopmentClosure:
    rows = {
        (0, "CONTINUE"): (Outcome(1, 1, -100 if off_policy_only else 0),),
        (1, "REWARD"): (Outcome(0.5, 3, 0.25), Outcome(0.5, 4, 0.25)),
        (1, "SAFE"): (Outcome(1, 4, 0),),
        (2, "REWARD"): (Outcome(0.5, 3, 0.25), Outcome(0.5, 4, 0.25)),
        (2, "SAFE"): (Outcome(1, 4, 0),),
    }
    if off_policy_only:
        rows[0, "EXIT"] = (Outcome(1, 5, 0),)
    model = FiniteModel(
        layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0, 5: 1},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF", 5: "WON"},
        rows=rows, roots=(0,),
    )
    return DevelopmentClosure(model, {state: (state,) * 16 for state in model.layers}, ("fixture",),
        {"states": 6, "active_states": 3, "exact_transition_row_calls": len(rows),
         "exact_outcomes_enumerated": sum(map(len, rows.values()))}, 0.25)


def _queries() -> dict[str, Query]:
    return {"reward": Query(), "risk": Query(1, 1, 0)}


def test_root_action_does_not_hide_reached_descendant_risk_conflict() -> None:
    """Root action equality must not erase a reached, consequential query switch."""
    report = characterization.characterize_closure(_closure(), fit_queries=_queries(), probe_queries={})
    assert report["classification"] == "CANONICAL_POLICY_REACHED_DOWNSTREAM_ONLY_QUERY_CONFLICT"
    assert report["exact_root_required_switches"]["ALL"]["states_with_required_switch"] == 0
    assert report["exact_all_state_required_switches"]["ALL"]["states_with_required_switch"] == 2
    assert report["canonical_policy_reach"]["reached_conflict_states"] == 1
    assert report["canonical_policy_reach"]["off_policy_only_conflict_states"] == 1
    witness = report["conflict_witnesses"][0]
    assert witness["state"] == 1
    assert witness["canonical_root_policy_reach_probability_by_query"] == {"reward": 1, "risk": 1}
    reward, risk = witness["queries"]["reward"], witness["queries"]["risk"]
    assert reward["optimal_policy_metrics"]["failure"] == pytest.approx(0.5)
    assert risk["optimal_policy_metrics"]["failure"] == 0
    assert reward["first_action_then_frozen_query_policy"]["REWARD"]["value"] == pytest.approx(0.25)
    assert risk["first_action_then_frozen_query_policy"]["REWARD"]["value"] == pytest.approx(-0.25)
    root = report["root_characterization"][0]
    assert root["queries"]["reward"]["first_action_then_frozen_query_policy"]["CONTINUE"]["continuation_reward"] == 0.25
    assert root["queries"]["risk"]["first_action_then_frozen_query_policy"]["CONTINUE"]["failure"] == 0
    assert report["characterization_cost"]["canonical_policy_reach_counts"]["state_action_rows"] == 4


def test_off_policy_only_conflicts_are_separate_from_root_policy_coverage() -> None:
    """An avoided branch is a counterfactual conflict, not exercised behavior."""
    report = characterization.characterize_closure(_closure(off_policy_only=True), fit_queries=_queries(), probe_queries={})
    assert report["classification"] == "OFF_POLICY_ONLY_QUERY_CONFLICT"
    assert report["canonical_policy_reach"]["reached_conflict_states"] == 0
    assert report["canonical_policy_reach"]["off_policy_only_conflict_states"] == 2


def test_overlapping_optimal_ties_do_not_count_as_required_switches() -> None:
    """Different canonical actions can share an optimal action and require no switch."""
    references = {
        "left": {"optimal_actions": {0: ("A", "B")}},
        "middle": {"optimal_actions": {0: ("B", "C")}},
        "right": {"optimal_actions": {0: ("D",)}},
    }
    assert characterization.strict_query_pairs(references, 0, tuple(references)) == [("left", "right"), ("middle", "right")]


def test_zero_tolerance_quotient_compresses_without_losing_policy_value() -> None:
    """Two equivalent decision states should merge and retain both risk behaviors."""
    report = characterization.characterize_closure(_closure(), fit_queries=_queries(), probe_queries={})
    exact = report["references"]["full_state_exact"]["inventory"]
    quotient = report["references"]["zero_tolerance_exact_quotient"]
    assert quotient["inventory"]["active_cells"] == exact["active_cells"] - 1
    assert report["exact_quotient_comparison"]["all_state_optimal_full_policy_count"] == 6
    assert report["exact_quotient_comparison"]["maximum_all_state_objective_regret"] == pytest.approx(0)
    assert quotient["all_state_required_switches"]["ALL"]["all_required_switches_preserved"]


def test_budget_failures_stay_in_declared_case_denominators(monkeypatch: pytest.MonkeyPatch) -> None:
    """A closure limit must retain the case and must not emit a truncated success."""
    case = V6Case("fixture", "source", "test", "v", (1,) * 16, 3, "TEST", "test")
    def too_large(**kwargs):
        raise ValueError("complete closure exceeds max_nodes=1; no truncated model produced")
    monkeypatch.setattr(characterization, "build_development_closure", too_large)
    report = characterization.run_characterization_v6(cases=(case, replace(case, name="second")), max_nodes=1,
        fit_queries=_queries(), probe_queries={})
    assert report["summary"]["declared_case_count"] == 2
    assert report["summary"]["completed_case_count"] == 0
    assert report["summary"]["closure_budget_exceeded_count"] == 2
    assert report["summary"]["source_group_count"] == 1
    assert all(row["exact_transition_generation_calls"] is None for row in report["cases"])
    assert report["within_cohort_closure_overlap"]["completed_closure_count"] == 0
