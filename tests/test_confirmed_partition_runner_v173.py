"""Compact synthetic checks; no environment or policy execution."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import run_controlled_predictive_confirmed_partition_v173 as runner
from test_consequence_partition_runner_v172 import compact_row, make_root


MODES = ("PART_CONFIRMED", "PART_UNPRUNED", "ONE_LATE", "COARSE_LATE", "H2")


def board_code(index):
    return [10, 9, 8, 7, 6, 5, 4, 3, 2, 1] + [(index >> bit) & 1 for bit in range(5)] + [0]


def phase_roots(phase="VALID", uneven=False):
    roots = []
    for source in runner.source_roster(f"{phase}_SOURCE"):
        count = 8 if uneven and source["replica"] == 0 else 1
        for slot in range(count):
            root = make_root(source["life"], source["replica"], slot, phase)
            root["source_id"] = source["source_id"]
            root["canonical_board"] = board_code(source["life"] * 8 + source["replica"])
            roots.append(root)
    return roots


def rows_for(roots, phase, components_for):
    by_id = {root["root_id"]: root for root in roots}
    rows = []
    for plan in runner.branch_roster(roots, phase):
        root = by_id[plan["root_id"]]
        row = compact_row(plan, components_for(root, plan))
        row["module"] = {
            "mode": "FORCED_H2",
            "life": root["life"],
            "forced_decisions": 1,
            "h2_calls": row["steps"] - 1,
        }
        rows.append(row)
    return rows


def choices_for(roots, confirmed="DOWN"):
    choices = []
    for root in roots:
        actual = {action["canonical_action"]: action["actual_action"] for action in root["actions"]}
        for mode in MODES:
            action = confirmed if mode == "PART_CONFIRMED" else root["teacher_action"]
            choices.append({
                "root_id": root["root_id"], "life": root["life"],
                "source_id": root["source_id"], "mode": mode,
                "canonical_action": action, "actual_action": actual[action],
                "fallback": False, "decision": {},
            })
    return choices


def comparison(summary, contrast="PART_CONFIRMED-PART_UNPRUNED"):
    return next(row for row in summary["comparisons"] if row["contrast"] == contrast)


def clustered_fixture():
    roots = phase_roots(uneven=True)

    def components_for(root, plan):
        gain = root["life"] + (8 if root["replica"] == 0 else 0)
        reward = 20.0 + (gain if plan["canonical_action"] == "DOWN" else 0)
        return [reward, 1.0, 0.0]

    return roots, rows_for(roots, "VALID", components_for), choices_for(roots)


def test_source_and_action_seed_streams_are_phase_separate_and_method_independent():
    confirm = runner.source_roster("CONFIRM_SOURCE")
    valid = runner.source_roster("VALID_SOURCE")
    assert len(confirm) == len(valid) == 32
    assert {(row["life"], row["replica"]) for row in confirm} == {
        (life, replica) for life in range(4) for replica in range(8)
    }
    valid_by_unit = {(row["life"], row["replica"]): row for row in valid}
    for row in confirm:
        assert valid_by_unit[row["life"], row["replica"]]["seed"] - row["seed"] == 20_000_000
    assert {row["seed"] for row in confirm}.isdisjoint(row["seed"] for row in valid)
    physical = {}
    for phase, offset in (("CONFIRM", 20_000_000), ("VALID", 40_000_000)):
        roots = [phase_roots(phase)[3]]
        roster = runner.branch_roster(roots, phase)
        physical[phase] = {row["seed"] for row in roster}
        assert len(roster) == 8  # Four suffixes and two actions, not five fitted methods.
        assert len({row["branch_id"] for row in roster}) == 8
        for suffix in range(4):
            pair = [row for row in roster if row["suffix"] == suffix]
            root = roots[0]
            seed = (17_300_000_000 + offset + root["life"] * 1_000_000
                    + root["replica"] * 100_000 + root["slot"] * 1_000 + suffix)
            assert {row["seed"] for row in pair} == {seed}
            assert {(row["canonical_action"], row["actual_action"]) for row in pair} == {
                ("DOWN", "RIGHT"), ("RIGHT", "DOWN")
            }
    assert physical["CONFIRM"].isdisjoint(physical["VALID"])


@pytest.mark.parametrize("phase", ["CONFIRM", "VALID"])
def test_fresh_filter_keeps_fixed_slots_without_replacement(phase):
    candidates = phase_roots(phase)
    collision = deepcopy(candidates[0])
    second = deepcopy(candidates[0])
    second.update(root_id=f"{phase}:0:0:7", slot=7, canonical_board=[9] + [0] * 15)
    candidates.append(second)
    seen = [{**collision, "root_id": "old_training_root", "source_id": "old_training_source"}]
    frozen = deepcopy(candidates)
    result = runner.fresh_roots(candidates, seen, phase=phase)
    assert result["complete"]
    assert len(result["excluded"]) == 1
    assert {root["root_id"] for root in result["roots"]} == {
        root["root_id"] for root in candidates if root["root_id"] != collision["root_id"]
    }
    retained, = [root for root in result["roots"] if root["source_id"] == second["source_id"]]
    assert retained["slot"] == 7
    assert candidates == frozen


def test_fresh_filter_holds_when_a_planned_source_has_no_fresh_root():
    candidates = phase_roots("VALID")
    seen = [{**candidates[0], "root_id": "old_training_root"}]
    result = runner.fresh_roots(candidates, seen, phase="VALID")
    assert not result["complete"]
    assert len(result["roots"]) == 31
    assert len(result["excluded"]) == 1
    assert candidates[0]["source_id"] not in {root["source_id"] for root in result["roots"]}


def test_summary_preserves_offsetting_reward_failure_success_components():
    roots = phase_roots()
    rows = rows_for(
        roots, "VALID",
        lambda root, plan: [18.0, 0.0, 1.0] if plan["canonical_action"] == "DOWN"
        else [20.0, 1.0, 0.0],
    )
    result = runner.summarize(list(reversed(rows)), roots, choices_for(roots), retained_splits=1)
    assert result["complete"]
    effect = comparison(result)
    assert effect["metrics"]["reward"]["mean"] == -2.0
    assert effect["metrics"]["failure"]["mean"] == -1.0
    assert effect["metrics"]["success"]["mean"] == 1.0
    assert effect["metrics"]["utility"]["mean"] == 0.0


def test_summary_uses_source_units_and_equal_history_weights():
    roots, rows, choices = clustered_fixture()
    result = runner.summarize(rows, roots, choices, retained_splits=1)
    assert result["complete"]
    effect = comparison(result)
    utility = effect["metrics"]["utility"]
    # Each history has eight SOURCE gains: [life + 8, life, ..., life].
    assert utility["mean"] == pytest.approx(2.5)
    assert utility["mean_variance"] == pytest.approx(0.25)
    assert utility["conditional_source_se"] == pytest.approx(0.5)
    assert utility["conditional_source_ci95"] == pytest.approx([1.52, 3.48])
    for history in effect["per_history"]:
        moments = history["metrics"]["utility"]
        assert history["source_clusters"] == 8
        assert moments["n"] == 8
        assert moments["mean"] == pytest.approx(history["life"] + 1)
        assert moments["sample_variance"] == pytest.approx(8)
        assert moments["mean_variance"] == pytest.approx(1)
    assert len(effect["clusters"]) == 32
    assert sorted(cluster["roots"] for cluster in effect["clusters"]) == [1] * 28 + [8] * 4
    assert result["progression"]["passed"]
    assert result["progression"]["status"] == "PASS"


def test_positive_action_gains_without_confirmed_split_are_not_representation_success():
    roots, rows, choices = clustered_fixture()
    result = runner.summarize(rows, roots, choices, retained_splits=0)
    assert result["complete"]
    for contrast in ("PART_CONFIRMED-PART_UNPRUNED", "PART_CONFIRMED-H2"):
        assert comparison(result, contrast)["metrics"]["utility"]["conditional_source_ci95"][0] > 0
    assert result["progression"]["retained_splits"] == 0
    assert not result["progression"]["structure_eligible"]
    assert result["progression"]["passed"] == 2
    assert result["progression"]["status"] == "FAIL"
    assert result["progression"]["status"] != "PASS"


def test_summary_scores_frozen_losing_choices_without_validation_argmax():
    roots = phase_roots()
    choices = choices_for(roots)
    frozen = deepcopy(choices)
    rows = rows_for(
        roots, "VALID",
        lambda root, plan: [1.0 if plan["canonical_action"] == "DOWN" else 2.0, 1.0, 0.0],
    )
    result = runner.summarize(rows, roots, choices, retained_splits=1)
    assert result["complete"]
    assert comparison(result)["metrics"]["utility"]["mean"] == -1.0
    assert comparison(result, "PART_CONFIRMED-H2")["metrics"]["utility"]["mean"] == -1.0
    assert choices == frozen
    assert not result["progression"]["passed"]


def test_missing_known_validation_source_holds_scientific_progression():
    roots, rows, choices = clustered_fixture()
    missing_ids = {root["root_id"] for root in roots if root["life"] == 0 and root["replica"] == 0}
    rows = [row for row in rows if row["root_id"] not in missing_ids]
    result = runner.summarize(rows, roots, choices, retained_splits=1)
    assert not result["complete"]
    assert not result["progression"]["passed"]
    assert result["progression"]["status"] == "HOLD"


@pytest.fixture
def discovery_inputs(tmp_path, monkeypatch):
    directory = tmp_path / "v172"
    inherited_ref = tmp_path / "v171" / "frozen_inputs.json"
    old_roots = [make_root(life, 0, 0, "V171_TRAIN") for life in range(4)]
    new_roots = [make_root(life, 0, 0, "V172_TRAIN") for life in range(4)]
    old_plans = runner.prior.branch_roster(old_roots, "TRAIN")
    new_plans = runner.prior.branch_roster(new_roots, "TRAIN")
    old_rows = [compact_row(plan, [2.0 + plan["life"], 1.0, 0.0]) for plan in old_plans]
    new_rows = [compact_row(plan, [12.0 + plan["life"], 1.0, 0.0]) for plan in new_plans]
    old_refs = [{"life": life, "path": str(tmp_path / "v171" / "TRAIN" / f"life{life}.json")}
                for life in range(4)]
    new_refs = [{"life": life, "outcomes_ref": str(directory / "TRAIN" / f"life{life}.json")}
                for life in range(4)]
    capsule = {
        "inherited_frozen_inputs_ref": str(inherited_ref),
        "train_outcomes": old_refs,
        "cost_refs": [{"path": "paidref", "fields": ["costs"]}],
        "snapshots": [{"life": life} for life in range(4)],
    }
    contents = {
        directory / "run.json": {"status": "complete", "phases": {"TRAIN": {"lifecycles": new_refs}}},
        directory / "source_capsule.json": capsule,
        directory / "frozen_inputs.json": {"inherited_roots": old_roots},
        directory / "analysis.json": {"training_complete": True, "costs": {"new_environment_samples": 91}},
        directory / "equivalence_analysis.json": {
            "observed_equivalence": True, "original_zero_sum_contract_failed": True,
        },
        inherited_ref: {"train_roster": old_plans},
        directory / "training_roots.json": new_roots,
        directory / "training_roster.json": new_plans,
    }
    for ref in old_refs:
        contents[Path(ref["path"])] = [row for row in old_rows if row["life"] == ref["life"]]
    for ref in new_refs:
        contents[Path(ref["outcomes_ref"])] = [row for row in new_rows if row["life"] == ref["life"]]
    reads = []
    assemblies = []

    def read(path):
        path = Path(path)
        assert path in contents, f"Unexpected discovery read, including any old VALID labels: {path}"
        reads.append(path)
        return deepcopy(contents[path])

    def assemble(roots, roster, outcomes):
        assemblies.append(deepcopy((roots, roster, outcomes)))
        return {
            "examples": [{
                "root_id": root["root_id"], "life": root["life"],
                "source_id": root["source_id"], "canonical_board": root["canonical_board"],
                "legal_actions": root["legal_actions"], "immediate_rewards": root["immediate_rewards"],
                "suffix_trials": [],
            } for root in roots],
            "counts": {"root_records_read": len(roots), "branch_records_read": len(outcomes)},
            "complete": True,
        }

    monkeypatch.setattr(runner, "read", read)
    monkeypatch.setattr(runner.prior, "assemble_examples", assemble)
    return {
        "directory": directory, "inherited_ref": inherited_ref, "contents": contents,
        "reads": reads, "assemblies": assemblies,
        "old_roots": old_roots, "new_roots": new_roots,
        "old_plans": old_plans, "new_plans": new_plans,
        "old_rows": old_rows, "new_rows": new_rows,
    }


def test_discovery_inherits_both_train_cohorts_without_reading_old_validation(discovery_inputs):
    fixture = discovery_inputs
    _, discovery = runner.extract_source(directory=fixture["directory"])
    assert discovery["complete"]
    assert fixture["assemblies"] == [
        (fixture["old_roots"], fixture["old_plans"], fixture["old_rows"]),
        (fixture["new_roots"], fixture["new_plans"], fixture["new_rows"]),
    ]
    assert set(fixture["reads"]) == set(fixture["contents"])
    assert len(fixture["reads"]) == len(fixture["contents"])
    assert discovery["roots"] == fixture["old_roots"] + fixture["new_roots"]
    assert {example["root_id"] for example in discovery["examples"]} == {
        root["root_id"] for root in discovery["roots"]
    }


def test_discovery_manifest_preserves_paid_cost_and_current_test_references(discovery_inputs):
    fixture = discovery_inputs
    source, discovery = runner.extract_source(directory=fixture["directory"])
    manifest = discovery["manifest"]
    assert source["inherited_v172_environment_samples"] == 91
    assert source["original_zero_sum_contract_failed"] is True
    assert {"path": "paidref", "fields": ["costs"]} in source["cost_refs"]
    referenced_paths = {ref["path"] for ref in source["cost_refs"]}
    assert str(fixture["directory"] / "analysis.json") in referenced_paths
    assert str(fixture["directory"] / "equivalence_analysis.json") in referenced_paths
    test_refs = json.dumps(source["this_stage_test_refs"])
    for name in ("core_checks.json", "runner_checks.json", "analyzer_checks.json"):
        assert name in test_refs
    assert manifest["inherited_frozen_inputs_ref"] == str(fixture["inherited_ref"])
    assert manifest["inherited_roots_ref"] == str(fixture["directory"] / "frozen_inputs.json")
    assert manifest["v172_training_roots_ref"] == str(fixture["directory"] / "training_roots.json")
    assert manifest["v172_training_roster_ref"] == str(fixture["directory"] / "training_roster.json")
    assert manifest["old_roots"] == manifest["new_roots"] == 4
    assert manifest["old_outcomes"] == manifest["new_outcomes"] == 32
