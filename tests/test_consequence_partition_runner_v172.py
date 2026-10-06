"""Pure runner checks: compact labels only, with no environment execution."""

from copy import deepcopy

import pytest

from scripts import run_controlled_predictive_consequence_partition_v172 as runner


MODEL_MODES = ("ONE_LATE", "COARSE_LATE", "PART_EARLY", "PART_LATE")


def make_root(life=0, replica=0, slot=0, phase="TRAIN", three_actions=False):
    # The actual directions deliberately differ from the canonical labels.
    actions = [
        {"canonical_action": "DOWN", "actual_action": "RIGHT"},
        {"canonical_action": "RIGHT", "actual_action": "DOWN"},
    ]
    if three_actions:
        actions.append({"canonical_action": "LEFT", "actual_action": "UP"})
    return {
        "root_id": f"{phase}:{life}:{replica}:{slot}",
        "source_id": f"{phase}_SOURCE:{life}:{replica}",
        "life": life,
        "query": "risk1",
        "replica": replica,
        "slot": slot,
        "canonical_board": ([0, 1, 2, 0] + [0] * 12) if three_actions else [1, 2] + [0] * 14,
        "legal_actions": [action["canonical_action"] for action in actions],
        "immediate_rewards": {action["canonical_action"]: 0.0 for action in actions},
        "teacher_action": "RIGHT",
        "actions": actions,
    }


def compact_row(plan, components):
    reward, failure, success = components
    assert failure + success == 1
    score = int(reward * 2048)
    assert score / 2048 == reward
    return {
        **plan,
        "score": score,
        "steps": 5,
        "status": "LOST" if failure else "WON",
        "components": list(components),
        "utility": reward - failure + success,
        "module": {},
    }


def make_rows(roots, phase, components_for):
    by_id = {root["root_id"]: root for root in roots}
    roster = runner.branch_roster(roots, phase)
    rows = [
        compact_row(plan, components_for(by_id[plan["root_id"]], plan))
        for plan in roster
    ]
    return roster, rows


def frozen_choices(roots, selected_action="DOWN"):
    choices = []
    for root in roots:
        actual = {
            action["canonical_action"]: action["actual_action"]
            for action in root["actions"]
        }
        for mode in (*MODEL_MODES, "H2"):
            action = root["teacher_action"] if mode == "H2" else selected_action
            choices.append({
                "root_id": root["root_id"],
                "life": root["life"],
                "source_id": root["source_id"],
                "mode": mode,
                "canonical_action": action,
                "actual_action": actual[action],
                "fallback": False,
                "decision": {},
            })
    return choices


def comparison(summary, contrast="PART_LATE-H2"):
    return next(row for row in summary["comparisons"] if row["contrast"] == contrast)


@pytest.mark.parametrize("phase,offset", [("TRAIN", 20_000_000), ("VALID", 40_000_000)])
def test_forced_actions_share_suffix_seed_and_keep_root_frame(phase, offset):
    roots = [make_root(1, 2, 3, phase), make_root(3, 7, 6, phase)]
    roster = runner.branch_roster(roots, phase)
    assert len(roster) == 16
    assert len({row["branch_id"] for row in roster}) == 16
    for root in roots:
        for suffix in range(4):
            pair = [row for row in roster
                    if row["root_id"] == root["root_id"] and row["suffix"] == suffix]
            expected_seed = (17_200_000_000 + offset + root["life"] * 1_000_000
                             + root["replica"] * 100_000 + root["slot"] * 1_000 + suffix)
            assert {row["seed"] for row in pair} == {expected_seed}
            assert {(row["canonical_action"], row["actual_action"]) for row in pair} == {
                ("DOWN", "RIGHT"), ("RIGHT", "DOWN")
            }


def test_assembly_preserves_each_paired_whole_component_vector():
    roots = [make_root()]
    vectors = {
        "DOWN": [[3.0, 1.0, 0.0], [7.0, 0.0, 1.0],
                 [2.0, 1.0, 0.0], [9.0, 0.0, 1.0]],
        "RIGHT": [[8.0, 0.0, 1.0], [6.0, 1.0, 0.0],
                  [10.0, 0.0, 1.0], [4.0, 1.0, 0.0]],
    }
    roster, rows = make_rows(
        roots, "TRAIN", lambda root, plan: vectors[plan["canonical_action"]][plan["suffix"]]
    )
    result = runner.assemble_examples(roots, roster, list(reversed(rows)))
    assert result["complete"]
    assert result["issues"] == []
    assert result["counts"]["root_records_read"] == 1
    assert result["counts"]["branch_records_read"] == 8
    assert result["counts"]["paired_root_suffixes"] == 4
    assert result["counts"]["component_label_reads"] == 24
    example, = result["examples"]
    assert example["canonical_board"] == roots[0]["canonical_board"]
    assert example["legal_actions"] == roots[0]["legal_actions"]
    for trial in example["suffix_trials"]:
        suffix = trial["suffix"]
        assert trial["action_components"] == {
            action: vectors[action][suffix] for action in vectors
        }
        assert trial["seed"] == next(
            row["seed"] for row in roster if row["suffix"] == suffix
        )


@pytest.mark.parametrize("failure", ["missing", "duplicate", "cutoff"])
def test_assembly_rejects_incomplete_physical_cohort_without_partial_training(failure):
    roots = [make_root()]
    roster, rows = make_rows(roots, "TRAIN", lambda root, plan: [3.0, 1.0, 0.0])
    if failure == "missing":
        rows.pop()
    elif failure == "duplicate":
        rows.append(deepcopy(rows[0]))
    else:
        rows[0].update(status="CUTOFF", steps=8192, components=[3.0, 0.0, 0.0], utility=None)
    result = runner.assemble_examples(roots, roster, rows)
    assert not result["complete"]
    assert result["examples"] == []
    assert "incomplete_branch_cohort" in result["issues"]
    assert result["counts"]["root_records_read"] == 1
    assert result["counts"]["branch_records_read"] == len(rows)


def clustered_fixture():
    # Eight correlated roots belong to the high-valued SOURCE; one to the low one.
    roots = [make_root(life, replica, slot, "VALID")
             for life in range(4) for replica in range(2)
             for slot in range(8 if replica == 0 else 1)]

    def components_for(root, plan):
        gain = root["life"] + (8 if root["replica"] == 0 else 0)
        reward = 20.0 + (gain if plan["canonical_action"] == "DOWN" else 0)
        return [reward, 1.0, 0.0]

    _, rows = make_rows(roots, "VALID", components_for)
    return roots, rows, frozen_choices(roots)


def test_summary_weights_sources_then_histories_and_uses_source_uncertainty():
    roots, rows, choices = clustered_fixture()
    result = runner.summarize(rows, roots, choices)
    assert result["complete"]
    effect = comparison(result)
    assert effect["complete"]
    utility = effect["metrics"]["utility"]
    # Per history SOURCE gains are [life + 8, life], not nine independent roots.
    assert utility["mean"] == pytest.approx(5.5)
    assert utility["mean_variance"] == pytest.approx(4.0)
    assert utility["conditional_source_se"] == pytest.approx(2.0)
    assert utility["conditional_source_ci95"] == pytest.approx([1.58, 9.42])
    for history in effect["per_history"]:
        moments = history["metrics"]["utility"]
        assert history["source_clusters"] == 2
        assert moments["n"] == 2
        assert moments["mean"] == pytest.approx(history["life"] + 4)
        assert moments["sample_variance"] == pytest.approx(32)
        assert moments["mean_variance"] == pytest.approx(16)
    assert len(effect["clusters"]) == 8
    assert sorted(cluster["roots"] for cluster in effect["clusters"]) == [1] * 4 + [8] * 4
    assert all(cluster["suffixes"] == 4 for cluster in effect["clusters"])
    assert effect["metrics"]["reward"]["mean"] == pytest.approx(5.5)
    assert effect["metrics"]["failure"]["mean"] == 0
    assert effect["metrics"]["success"]["mean"] == 0


def test_summary_scores_frozen_losing_choices_without_validation_argmax():
    roots = [make_root(life, replica, 0, "VALID", three_actions=True)
             for life in range(4) for replica in range(2)]
    choices = frozen_choices(roots, selected_action="DOWN")
    frozen = deepcopy(choices)
    rewards = {"DOWN": 1.0, "RIGHT": 2.0, "LEFT": 100.0}
    _, rows = make_rows(
        roots, "VALID", lambda root, plan: [rewards[plan["canonical_action"]], 1.0, 0.0]
    )
    result = runner.summarize(rows, roots, choices)
    assert result["complete"]
    assert comparison(result)["metrics"]["utility"]["mean"] == pytest.approx(-1.0)
    assert comparison(result)["metrics"]["utility"]["conditional_source_ci95"] == [-1.0, -1.0]
    assert comparison(result, "PART_LATE-ONE_LATE")["metrics"]["utility"]["mean"] == 0
    assert choices == frozen


def test_summary_holds_when_known_validation_source_has_no_retained_outcome():
    roots, rows, choices = clustered_fixture()
    absent_root_ids = {
        root["root_id"] for root in roots if root["life"] == 0 and root["replica"] == 0
    }
    rows = [row for row in rows if row["root_id"] not in absent_root_ids]
    result = runner.summarize(rows, roots, choices)
    assert not result["complete"]
    assert all(not effect["complete"] for effect in result["comparisons"])
