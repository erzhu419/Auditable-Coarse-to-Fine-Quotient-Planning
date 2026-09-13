from __future__ import annotations

import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_decision_point_diagnosis_v2 import extract_decision_point_cases


def test_extraction_only_uses_selected_action_reached_conflicts() -> None:
    """An unchosen-action conflict or dropped spawn outcome would misstate mechanism reachability."""
    discovery_path = Path(__file__).resolve().parents[1] / "reports/challenge_generator_discovery_v2.json"
    cases, provenance = extract_decision_point_cases(json.loads(discovery_path.read_text(encoding="utf-8")))
    assert provenance["maximum_recorded_root_q_replay_absolute_error"] < 1e-10
    assert provenance["source_action_uniquely_optimal_for_all_six_queries"]
    assert provenance["parent_reconstruction_costs"]["exact_plan_count"] == 6
    assert provenance["inspected_total_reach_probability"] == pytest.approx(1)
    inspected = provenance["all_inspected_successors"]
    assert all(row["source_root_action"] == "LEFT" for row in inspected)
    assert all(row["parent_state_id"] != 4 for row in inspected)  # State 4 follows DOWN.
    retained = [row for row in inspected if row["retained_for_comparison"]]
    assert len(cases) == len(retained)
    assert {case.name for case in cases} == {row["comparison_case_name"] for row in retained}
    assert all(case.split == "EXPOSED_DECISION_POINT" for case in cases)
    assert len({case.group for case in cases}) == 1
    witness = next(row for row in retained if row["parent_state_id"] == 7)
    assert witness["remaining_horizon"] == 2
    assert witness["one_step_reach_probability_under_source_action"] == pytest.approx(0.3)
    assert witness["board"] == (3, 7, 9, 0, 7, 9, 6, 1, 8, 4, 9, 0, 1, 9, 8, 2)
    assert witness["exact_queries"]["risk_0"]["optimal_actions"] == ("DOWN",)
    for name in ("risk_0_05", "risk_0_2", "risk_1", "risk_5"):
        assert witness["exact_queries"][name]["optimal_actions"] == ("RIGHT",)
