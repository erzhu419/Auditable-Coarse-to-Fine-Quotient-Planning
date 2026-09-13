from dataclasses import replace

import pytest

from acfqp.science import controlled_predictive_comparison_v4 as comparison
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import CompiledModel, FiniteModel, Outcome, Query


def _closure() -> DevelopmentClosure:
    model = FiniteModel(
        layers={0: 2, 1: 1, 2: 1, 3: 0, 4: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "LOST", 4: "CUTOFF"},
        rows={(0, "CONTINUE"): (Outcome(1, 1, 0),),
              (1, "REWARD"): (Outcome(0.5, 3, 0.01), Outcome(0.5, 4, 0.01)),
              (1, "SAFE"): (Outcome(1, 4, 0),),
              (2, "REWARD"): (Outcome(1, 4, 0.01),),
              (2, "SAFE"): (Outcome(1, 4, 0),)}, roots=(0,),
    )
    return DevelopmentClosure(model, {state: (state,) for state in model.layers}, ("fixture",),
        {"states": 5, "active_states": 3, "exact_transition_row_calls": 5,
         "exact_outcomes_enumerated": 6}, 0.25)


def _case() -> comparison.RefinementCase:
    return comparison.RefinementCase("fixture", "fixture", "TEST", (1,) * 16, "test", 1, 2)


def test_shared_empirical_exact_baseline_and_probe_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exact-environment baseline or fitted probes would invalidate matching."""
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    sample_fn, exact_fn = comparison.sample_model, comparison.build_quotient
    fitted_fn, incremental_fn = comparison.build_refined_quotient, comparison.build_refined_quotient_v4
    sampled, exact_inputs, fit_inputs = [], [], []

    def sample(*args, **kwargs):
        model = sample_fn(*args, **kwargs)
        sampled.append(model)
        return model

    def exact(model, **kwargs):
        exact_inputs.append((model, kwargs))
        return exact_fn(model, **kwargs)

    def fit(model, queries, **kwargs):
        fit_inputs.append((model, dict(queries)))
        return fitted_fn(model, queries, **kwargs)

    def incremental(model, queries, **kwargs):
        fit_inputs.append((model, dict(queries)))
        return incremental_fn(model, queries, **kwargs)

    monkeypatch.setattr(comparison, "sample_model", sample)
    monkeypatch.setattr(comparison, "build_quotient", exact)
    monkeypatch.setattr(comparison, "build_refined_quotient", fit)
    monkeypatch.setattr(comparison, "build_refined_quotient_v4", incremental)
    bank = {"reward": Query(1, 0, 0), "risk": Query(1, 1, 0)}
    report = comparison.run_comparison_v4(cases=(_case(),), fit_queries=bank,
        probe_queries={"probe": Query(1, 0.5, 0)}, sample_seeds=(123,), samples_per_row=32)
    assert len(sampled) == 1
    assert len(exact_inputs) == 1 and exact_inputs[0] == (sampled[0], {})
    assert len(fit_inputs) == 2 and all(model is sampled[0] and queries == bank for model, queries in fit_inputs)
    record = report["cases"][0]
    assert record["exact_all_state_required_switches"]["ALL"]["states_with_required_switch"] == 1
    run = record["sampled_runs"][0]
    assert run["v4_v3_compiled_equivalence"]["equivalent"]
    assert set(run["arms"]) == set(comparison.ARM_NAMES)
    for name in comparison.ARM_NAMES[1:]:
        for query in ("reward", "risk", "probe"):
            assert run["matched_comparisons"][name][query]["maximum_all_state_extra_regret_over_full_state"] == pytest.approx(0)
    arm = run["arms"][comparison.ARM_NAMES[3]]
    assert arm["all_state_required_switches"]["ALL"]["all_required_switches_preserved"]
    assert arm["model_build_count"] == 1 and arm["query_count_using_same_compiled_model"] == 3
    cost = arm["measured_cumulative_workloads"][-1]
    assert cost["including_shared_closure_sample_build_plan_forecast_audit_seconds"] == pytest.approx(
        0.25 + run["sampling_seconds"] + cost["construction_plus_planning_seconds"]
        + cost["cumulative_forecast_seconds"] + cost["cumulative_ground_audit_seconds"])
    assert all("members_before" not in row for row in arm["refinement_diagnostics"]["iterations"])


def test_equivalence_ignores_cell_ids_but_detects_transition_reward_changes() -> None:
    """Equal cell counts alone must not hide an incremental recompilation error."""
    left = comparison.compile_full_state(_closure().model)
    mapping = {key: key + 20 for key in left.cells}
    right = CompiledModel(
        {mapping[key]: cell for key, cell in left.cells.items()},
        {(mapping[key], action): tuple(replace(outcome, next_state=mapping[outcome.next_state]) for outcome in row)
         for (key, action), row in left.rows.items()},
        tuple(mapping[root] for root in left.roots),
        {state: mapping[key] for state, key in left.state_to_cell.items()}, {},
    )
    assert comparison.compiled_equivalence(left, right)["equivalent"]
    changed = dict(right.rows)
    key = next(iter(changed))
    changed[key] = tuple(replace(outcome, reward=outcome.reward + 0.1) for outcome in changed[key])
    comparison_row = comparison.compiled_equivalence(left, replace(right, rows=changed))
    assert comparison_row["same_member_partition"] and not comparison_row["equivalent"]
    assert comparison_row["maximum_probability_weighted_reward_difference"] == pytest.approx(0.1)


def test_rotation_and_declared_budget_exclusions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every arm must receive each timing position; closure failure remains declared."""
    excluded = comparison.run_comparison_v4(cases=(_case(),), max_nodes=1,
        fit_queries={"reward": Query()}, probe_queries={}, sample_seeds=(123,))
    assert excluded["case_count"] == 1 and excluded["cases"][0]["status"] == "CLOSURE_BUDGET_EXCEEDED"
    assert excluded["summary_by_source_group"]["fixture"]["declared_cases"] == 1
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    cases = tuple(replace(_case(), name=str(index), group=str(index)) for index in range(4))
    report = comparison.run_comparison_v4(cases=cases, fit_queries={"reward": Query()},
        probe_queries={}, sample_seeds=(123,), samples_per_row=8)
    orders = [record["sampled_runs"][0]["measured_arm_order"] for record in report["cases"]]
    for index in range(4):
        assert {order[index] for order in orders} == set(comparison.ARM_NAMES)


def test_fixed_cohort_marks_all_old_v3_boards_exposed_and_retains_fresh_seeds() -> None:
    cases = comparison.comparison_cases_v4()
    assert len(cases) == 25 and len({case.group for case in cases}) == 25
    assert {case.split for case in cases[:13]} == {"EXPOSED_V3_DEVELOPMENT"}
    assert {case.split for case in cases[13:]} == {"NEW_DEVELOPMENT_V4"}
    assert {case.seed for case in cases[13:]} == {seed + index for seed in comparison.DEVELOPMENT_SEEDS_V4 for index in range(3)}
    assert cases[0].horizon == 2 and all(case.horizon == 3 for case in cases[1:])


def test_repeated_roots_are_reported_without_replacing_declared_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Different generator seeds must not disguise reuse of an exposed root."""
    monkeypatch.setattr(comparison, "build_development_closure", lambda **kwargs: _closure())
    exposed = replace(_case(), name="old", group="old", split="EXPOSED_V3_DEVELOPMENT")
    new = replace(exposed, name="new", group="new", split="NEW_DEVELOPMENT_V4", seed=2)
    report = comparison.run_comparison_v4(cases=(exposed, new), fit_queries={"reward": Query()},
        probe_queries={}, sample_seeds=(123,), samples_per_row=8)
    overlap = report["root_board_identity_overlap"]
    assert report["case_count"] == 2 and [row["case"]["name"] for row in report["cases"]] == ["old", "new"]
    assert all(row["status"] == "COMPLETE" for row in report["cases"])
    assert overlap["declared_case_count"] == 2 and overlap["unique_root_board_count"] == 1
    assert overlap["duplicate_root_group_count"] == 1
    assert overlap["duplicate_root_groups"][0]["case_names"] == ["old", "new"]
    assert overlap["new_cases_reusing_exposed_root_count"] == 1
    assert overlap["new_cases_reusing_exposed_roots"][0]["exposed_case_names"] == ["old"]
    assert overlap["unique_new_roots_not_among_declared_exposed_roots"] == 0
    assert overlap["all_declared_cases_retained"]
