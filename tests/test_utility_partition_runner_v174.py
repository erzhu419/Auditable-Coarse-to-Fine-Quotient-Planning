"""Pure compact-data checks for the two-generator confirmation experiment."""

from copy import deepcopy

import pytest

from scripts import run_controlled_predictive_utility_partition_v174 as runner
from test_consequence_partition_runner_v172 import compact_row, make_root
from test_confirmed_partition_runner_v173 import discovery_inputs
import test_confirmed_partition_runner_v173 as previous_tests


MODES = (
    "PART_UTILITY_CONFIRMED", "PART_SSE_CONFIRMED",
    "PART_UTILITY_UNPRUNED", "PART_SSE_UNPRUNED", "ONE_LATE", "H2",
)
PRIMARY = "PART_UTILITY_CONFIRMED-PART_SSE_CONFIRMED"


def phase_roots(phase="VALID", uneven=False, three_actions=False):
    roots = []
    for source in runner.source_roster(f"{phase}_SOURCE"):
        for slot in range(8 if uneven and source["replica"] == 0 else 1):
            root = make_root(source["life"], source["replica"], slot, phase, three_actions)
            root["source_id"] = source["source_id"]
            roots.append(root)
    return roots


def rows_for(roots, phase, components_for):
    by_id = {root["root_id"]: root for root in roots}
    rows = []
    for plan in runner.branch_roster(roots, phase):
        root = by_id[plan["root_id"]]
        row = compact_row(plan, components_for(root, plan))
        row["module"] = {
            "mode": "FORCED_H2", "life": root["life"],
            "forced_decisions": 1, "h2_calls": row["steps"] - 1,
        }
        rows.append(row)
    return rows


def choices_for(roots, overrides=None):
    overrides = overrides or {}
    choices = []
    for root in roots:
        actual = {action["canonical_action"]: action["actual_action"] for action in root["actions"]}
        for mode in MODES:
            default = "DOWN" if mode == "PART_UTILITY_CONFIRMED" else root["teacher_action"]
            action = overrides.get(mode, default)
            choices.append({
                "root_id": root["root_id"], "life": root["life"],
                "source_id": root["source_id"], "mode": mode,
                "canonical_action": action, "actual_action": actual[action],
                "fallback": False, "decision": {},
            })
    return choices


def comparison(summary, contrast=PRIMARY):
    return next(row for row in summary["comparisons"] if row["contrast"] == contrast)


def clustered_fixture():
    roots = phase_roots(uneven=True)

    def components_for(root, plan):
        gain = root["life"] + (8 if root["replica"] == 0 else 0)
        return [20.0 + (gain if plan["canonical_action"] == "DOWN" else 0), 1.0, 0.0]

    return roots, rows_for(roots, "VALID", components_for), choices_for(roots)


def test_new_source_and_branch_streams_pair_actions_without_replicating_methods():
    sources = {phase: runner.source_roster(f"{phase}_SOURCE") for phase in ("CONFIRM", "VALID")}
    for phase, plans in sources.items():
        assert len(plans) == 32
        assert {(plan["life"], plan["replica"]) for plan in plans} == {
            (life, replica) for life in range(4) for replica in range(8)
        }
    confirm = {(plan["life"], plan["replica"]): plan for plan in sources["CONFIRM"]}
    valid = {(plan["life"], plan["replica"]): plan for plan in sources["VALID"]}
    for unit in confirm:
        assert valid[unit]["seed"] - confirm[unit]["seed"] == 20_000_000
        assert 17_400_000_000 <= confirm[unit]["seed"] < 17_500_000_000
    seeds = {}
    for phase, offset in (("CONFIRM", 20_000_000), ("VALID", 40_000_000)):
        roots = [phase_roots(phase)[3]]
        roster = runner.branch_roster(roots, phase)
        seeds[phase] = {row["seed"] for row in roster}
        assert len(roster) == 8  # Two actions times four suffixes, independent of six methods.
        assert len({row["branch_id"] for row in roster}) == 8
        root = roots[0]
        for suffix in range(4):
            pair = [row for row in roster if row["suffix"] == suffix]
            expected = (17_400_000_000 + offset + root["life"] * 1_000_000
                        + root["replica"] * 100_000 + root["slot"] * 1_000 + suffix)
            assert {row["seed"] for row in pair} == {expected}
            assert {(row["canonical_action"], row["actual_action"]) for row in pair} == {
                ("DOWN", "RIGHT"), ("RIGHT", "DOWN")
            }
    assert seeds["CONFIRM"].isdisjoint(seeds["VALID"])


def test_source_cluster_units_and_equal_histories_determine_primary_uncertainty():
    roots, rows, choices = clustered_fixture()
    summary = runner.summarize(rows, roots, choices, retained_splits=1)
    assert summary["complete"]
    effect = comparison(summary)
    utility = effect["metrics"]["utility"]
    assert utility["mean"] == pytest.approx(2.5)
    assert utility["mean_variance"] == pytest.approx(0.25)
    assert utility["conditional_source_se"] == pytest.approx(0.5)
    assert utility["conditional_source_ci95"] == pytest.approx([1.52, 3.48])
    for history in effect["per_history"]:
        assert history["source_clusters"] == 8
        assert history["metrics"]["utility"]["n"] == 8
        assert history["metrics"]["utility"]["mean"] == pytest.approx(history["life"] + 1)
        assert history["metrics"]["utility"]["mean_variance"] == pytest.approx(1)
    assert sorted(cluster["roots"] for cluster in effect["clusters"]) == [1] * 28 + [8] * 4
    assert summary["progression"]["status"] == "PASS"


def test_positive_primary_gains_without_utility_retained_structure_fail_science():
    roots, rows, choices = clustered_fixture()
    summary = runner.summarize(rows, roots, choices, retained_splits=0)
    assert summary["complete"]
    for contrast in (PRIMARY, "PART_UTILITY_CONFIRMED-H2"):
        assert comparison(summary, contrast)["metrics"]["utility"]["conditional_source_ci95"][0] > 0
    assert summary["progression"]["passed"] == 2
    assert not summary["progression"]["structure_eligible"]
    assert summary["progression"]["status"] == "FAIL"


def test_both_primary_comparisons_must_pass_not_only_the_sse_comparison():
    roots = phase_roots(three_actions=True)
    choices = choices_for(roots, {"PART_SSE_CONFIRMED": "LEFT"})
    rewards = {"LEFT": 1.0, "DOWN": 2.0, "RIGHT": 3.0}
    rows = rows_for(roots, "VALID", lambda root, plan: [rewards[plan["canonical_action"]], 1.0, 0.0])
    summary = runner.summarize(rows, roots, choices, retained_splits=1)
    assert summary["complete"]
    assert comparison(summary)["metrics"]["utility"]["mean"] == 1.0
    assert comparison(summary, "PART_UTILITY_CONFIRMED-H2")["metrics"]["utility"]["mean"] == -1.0
    assert summary["progression"]["passed"] == 1
    assert summary["progression"]["status"] == "FAIL"


def test_frozen_choices_keep_the_whole_vector_even_when_test_labels_prefer_sse():
    roots = phase_roots()
    choices = choices_for(roots)
    frozen = deepcopy(choices)
    rows = rows_for(
        roots, "VALID", lambda root, plan: [18.0, 0.0, 1.0]
        if plan["canonical_action"] == "DOWN" else [21.0, 1.0, 0.0],
    )
    summary = runner.summarize(list(reversed(rows)), roots, choices, retained_splits=1)
    assert summary["complete"]
    effect = comparison(summary)
    assert effect["metrics"]["reward"]["mean"] == -3.0
    assert effect["metrics"]["failure"]["mean"] == -1.0
    assert effect["metrics"]["success"]["mean"] == 1.0
    assert effect["metrics"]["utility"]["mean"] == -1.0
    assert choices == frozen


def test_missing_planned_source_holds_instead_of_pooling_remaining_sources():
    roots, rows, choices = clustered_fixture()
    missing = {root["root_id"] for root in roots if root["life"] == 0 and root["replica"] == 0}
    rows = [row for row in rows if row["root_id"] not in missing]
    summary = runner.summarize(rows, roots, choices, retained_splits=1)
    assert not summary["complete"]
    assert summary["progression"]["status"] == "HOLD"


def test_discovery_reader_reuses_only_the_two_paid_train_cohorts(discovery_inputs, monkeypatch):
    fixture = discovery_inputs
    monkeypatch.setattr(runner, "read", previous_tests.runner.read)
    monkeypatch.setattr(runner.prior, "assemble_examples", previous_tests.runner.prior.assemble_examples)
    source, discovery = runner.extract_source(directory=fixture["directory"])
    assert discovery["complete"]
    assert set(fixture["reads"]) == set(fixture["contents"])
    assert len(fixture["reads"]) == len(fixture["contents"])
    assert fixture["assemblies"] == [
        (fixture["old_roots"], fixture["old_plans"], fixture["old_rows"]),
        (fixture["new_roots"], fixture["new_plans"], fixture["new_rows"]),
    ]
    assert discovery["roots"] == fixture["old_roots"] + fixture["new_roots"]
    assert {"path": "paidref", "fields": ["costs"]} in source["cost_refs"]
    # The strict reader rejects every path absent from this TRAIN-only registry,
    # including previous CONFIRM and VALID outcomes; cost references are metadata.
    assert not any("CONFIRM" in str(path) or "VALID" in str(path) for path in fixture["reads"])


def test_two_generator_global_k_and_fit_cost_groups_are_accounted_once(monkeypatch):
    examples = [{"root_id": f"DISCOVERY:{life}", "life": life} for life in range(4)]
    calls = []
    saved = []

    def proposal(generator, records, life):
        assert records is examples
        calls.append((generator, life))
        utility = generator == "UTILITY"
        nodes = ([{"kind": "split"}] * 2 + [{"kind": "leaf"}] * 3) if utility else [
            {"kind": "split"}, {"kind": "leaf"}, {"kind": "leaf"},
        ]
        result = {
            "life": life, "mode": "PART_UNPRUNED", "nodes": nodes,
            "fit_counts": {"component_label_reads": 3 if utility else 6},
            "node_fit_counts": {"full_discovery_node_fits": len(nodes)},
        }
        if utility:
            result["utility_search_counts"] = {"action_scores_evaluated": 13}
        return result

    def one(records, life, mode):
        assert records is examples
        assert mode == "ONE_LATE"
        calls.append((mode, life))
        return {"life": life, "mode": mode, "fit_counts": {"component_label_reads": 9}}

    def save(payload, seconds):
        saved.append(deepcopy(payload))
        return {"life": payload["life"], "mode": payload["mode"], "model_ref": "synthetic"}

    monkeypatch.setattr(runner, "propose_utility", lambda records, life: proposal("UTILITY", records, life))
    monkeypatch.setattr(runner, "propose_sse", lambda records, life: proposal("SSE", records, life))
    monkeypatch.setattr(runner, "fit_partition", one)
    result = runner.fit_discovery_models(examples, save)
    assert sorted(calls) == sorted((generator, life)
                                   for generator in ("UTILITY", "SSE", "ONE_LATE") for life in range(4))
    assert len(saved) == 12
    assert set(result["proposals"]) == {"UTILITY", "SSE"}
    assert all(set(models) == set(range(4)) for models in result["proposals"].values())
    assert set(result["controls"]) == {(life, "ONE_LATE") for life in range(4)}
    assert result["total_candidates"] == 12  # Eight utility splits plus four SSE splits.
    assert result["discovery_fit_counts"]["component_label_reads"] == 72
    assert result["discovery_node_fit_counts"]["full_discovery_node_fits"] == 32
    assert result["discovery_utility_search_counts"]["action_scores_evaluated"] == 52
