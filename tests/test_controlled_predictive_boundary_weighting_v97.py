"""Fixed boundary weighting preserves pair mass and learning splits."""
from collections import defaultdict
from copy import deepcopy
import json
from math import fsum
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_boundary_weighting_v97 import redistribute_weights


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    before = request.session.testsfailed
    yield
    path = ROOT / "reports/controlled_predictive_boundary_weighting_v97.checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, test_failures=request.session.testsfailed - before,
        scope="Synthetic metadata/weight redistribution only; no trajectories, simulation or fitting.",
        ground_calls=0, tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def pair(length, query="reward", episode=0, option="SNAKE_4", replica=0):
    return [dict(query=query, episode=episode, option=option, replica=replica, step=4 + 16 * index,
        weight=1 / 32, candidate_board=[1] * 16, reference_board=[2] * 16,
        target=[index / 2048, 0., 0.], n_target=[1 / 2048, 0., 0.]) for index in range(length)]


def test_different_lengths_keep_each_pairs_original_mass_and_half_at_boundary():
    lengths = [1, 2, 3, 7, 40]
    rows = [row for replica, length in enumerate(lengths) for row in pair(length, replica=replica)]
    rows.reverse()  # Incoming row order does not define the boundary and is preserved.
    before = deepcopy(rows)
    weighted, log = redistribute_weights(rows, 6)
    assert rows == before and weighted is not rows
    groups = defaultdict(list)
    for original, changed in zip(rows, weighted):
        assert original is not changed
        assert {key: value for key, value in original.items() if key != "weight"} == {
            key: value for key, value in changed.items() if key != "weight"}
        groups[changed["replica"]].append(changed)
    for replica, values in groups.items():
        m = lengths[replica]
        assert len(values) == m
        assert fsum(row["weight"] for row in values) == pytest.approx(m / 32, abs=1e-15)
        boundary = next(row for row in values if row["step"] == 4)
        assert boundary["weight"] == (1 / 32 if m == 1 else m / 64)
        if m > 1:
            assert all(row["weight"] == m / (64 * (m - 1)) for row in values if row["step"] != 4)
    total = log["totals"]
    assert total["groups"] == 5 and total["singletons"] == 1 and total["rows"] == 53
    assert total["prior_total_mass"] == pytest.approx(total["new_total_mass"], abs=1e-15)
    assert total["prior_total_mass"] == 53 / 32
    assert total["prior_boundary_share"] == pytest.approx(5 / 53)
    assert total["new_boundary_share"] == pytest.approx(.5 + .5 / 53)
    assert total["singleton_boundary_mass"] == 1 / 32
    assert total["max_pair_mass_error"] < 1e-15
    assert total == log["queries"]["reward"]
    assert log["counts"]["changed_weight_rows"] == 50


def test_query_episode_option_and_replica_groups_and_heldout_future_isolation():
    rows = (pair(3) + pair(5, query="risk_goal") + pair(1, episode=1, option="SPACE_1")
            + pair(2, replica=1) + pair(4, episode=4) + pair(4, episode=6))
    before = deepcopy(rows)
    weighted, log = redistribute_weights(iter(rows), 6)
    assert rows == before
    for old, new in zip(rows, weighted):
        if old["episode"] in (4, 6):
            assert old == new and new["weight"] == 1 / 32
    assert log["eligible_episodes"] == {"reward": [0, 1], "risk_goal": [0]}
    assert log["counts"]["input_rows"] == 19
    assert log["counts"]["training_rows"] == 11
    assert log["counts"]["heldout_rows"] == log["counts"]["future_rows"] == 4
    assert log["queries"]["reward"]["groups"] == 3
    assert log["queries"]["reward"]["prior_total_mass"] == 6 / 32
    assert log["queries"]["risk_goal"]["groups"] == 1
    assert log["queries"]["risk_goal"]["new_boundary_share"] == .5
    assert log["totals"]["groups"] == 4
    assert log["totals"]["new_total_mass"] == 11 / 32
    assert log["counts"]["tree_fits"] == log["counts"]["new_environment_transitions"] == 0


@pytest.mark.parametrize("steps", [[20], [4, 4], [4, 36], [4, 20, 21]])
def test_requires_one_boundary_and_the_complete_fixed_grid(steps):
    rows = pair(len(steps))
    for row, step in zip(rows, steps):
        row["step"] = step
    before = deepcopy(rows)
    with pytest.raises(ValueError, match="exactly one k=4.*grid"):
        redistribute_weights(rows, 6)
    assert rows == before


def test_cannot_redistribute_already_changed_training_weights():
    rows = pair(3)
    rows[0]["weight"] = .5
    with pytest.raises(ValueError, match="original fixed 1/32"):
        redistribute_weights(rows, 6)
