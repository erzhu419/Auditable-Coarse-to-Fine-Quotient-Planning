"""Bellman segment/terminal accounting and retained-root compatibility."""
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_bellman_data_v94 as module
from acfqp.science.controlled_predictive_continuation_data_v91 import load_batch as load_v91


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_bellman_data_v94.data_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic branch records and V91 cohort compatibility; no simulation or model fitting.",
        ground_calls=0, main_campaign_calls=0, tree_fits=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def trajectory(option="SNAKE_4", n=40, status="WON", episode=0, replica=0, query="risk_goal", factor=1):
    boards = [[1, 1, 2, 3, 4, index + 1] + [0] * 10 for index in range(n + 1)]
    steps = [dict(board=boards[i], next_board=boards[i + 1], score=(i + 1) * factor,
        status=status if i == n - 1 and status in module.TERMINAL else "ACTIVE") for i in range(n)]
    seed = 101340000000 + episode * 100 + replica
    duration = 0 if option == "H2" else int(option.split("_")[1])
    return dict(root=dict(query=query, episode=episode, board=boards[0]), option=option, replica=replica,
        env_seed=seed, model_seed=seed + 1000000000000,
        game=dict(seed=seed, initial_board=boards[0], initial_spawns=[], final_board=boards[-1], steps=steps,
            return_score=sum(step["score"] for step in steps), status=status,
            work=dict(sampled_transitions=n, environment_random_draws=2 * n)),
        controller=dict(selected_option=option, initiation_step=0, fragment_actions=min(duration, n)),
        planning_counts=dict(model_uniform_draws=4 * n))


def write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_fixed_grid_terminal_anchors_and_no_reward_or_event_double_count():
    raw = trajectory()
    rows = module.extract_bellman_rows(raw)
    assert [row["step"] for row in rows] == [4, 20, 36]
    assert [row["steps"] for row in rows] == [16, 16, 4]
    assert [row["next_active"] for row in rows] == [True, True, False]
    assert [row["n_target"][0] for row in rows] == [200 / 2048, 456 / 2048, 154 / 2048]
    assert [row["n_target"][1:] for row in rows] == [[0., 0.], [0., 0.], [0., 1.]]
    assert rows[0]["target"] == [810 / 2048, 0., 1.]
    assert rows[-1]["n_target"] == rows[-1]["target"]
    assert rows[0]["next_board"] == rows[1]["board"]
    assert rows[-1]["next_board"] == raw["game"]["final_board"]
    assert [sum(row["n_target"][j] for row in rows) for j in range(3)] == rows[0]["target"]
    assert all(row["weight"] == 1 and row["query"] == "risk_goal" for row in rows)


@pytest.mark.parametrize("n,expected", [(4, []), (5, [4]), (20, [4]), (21, [4, 20])])
def test_terminal_at_fragment_or_segment_boundary_is_handled_once(n, expected):
    rows = module.extract_bellman_rows(trajectory(n=n, status="LOST"))
    assert [row["step"] for row in rows] == expected
    if rows:
        assert not rows[-1]["next_active"] and rows[-1]["n_target"][1:] == [1., 0.]
        assert sum(row["n_target"][1] for row in rows) == 1


def test_cutoff_has_no_bellman_or_full_return_supervision():
    assert module.extract_bellman_rows(trajectory(status="CUTOFF")) == []


@pytest.fixture
def batch(tmp_path):
    raw, means = [], []
    for episode in (0, 4, 1):
        for replica in range(8):
            for index, option in enumerate(module.OPTIONS):
                status = "CUTOFF" if episode == 1 and replica == 7 and option == "SNAKE_4" else "LOST"
                raw.append(trajectory(option, n=22, status=status, episode=episode, replica=replica,
                                      factor=index + replica + 1))
        if episode != 1:
            means.extend(dict(board=raw[-1]["root"]["board"], query="risk_goal", episode=episode,
                option=option, target=[253 * index / 2048, 0., 0.])
                for index, option in enumerate(module.OPTIONS[1:], start=1))
    write_rows(tmp_path / "branch_games.jsonl.gz", raw)
    write_rows(tmp_path / "new_rows.jsonl.gz", means)
    return tmp_path


def test_roots_exactly_match_v91_and_censored_root_costs_are_retained(batch):
    roots, rows, log = module.load_batch(batch)
    previous, _, previous_log = load_v91(batch)
    assert roots == previous
    assert len(roots) == 3 and len(rows) == 160
    assert roots[-1]["censored"] and roots[-1]["mc_rows"] == []
    assert {row["episode"] for row in rows} == {0, 4}
    assert all(row["query"] == "risk_goal" for row in rows)
    assert log["counts"]["terminal_anchor_rows"] == log["counts"]["bootstrap_rows"] == 80
    assert log["counts"]["training_bellman_rows"] == log["counts"]["heldout_bellman_rows"] == 80
    assert log["counts"]["censored_root_trajectories"] == 40
    assert log["counts"]["new_environment_transitions"] == log["counts"]["tree_fits"] == 0
    assert log["inherited_environment_work"] == previous_log["inherited_environment_work"]
    assert log["inherited_environment_work"]["sampled_transitions"] == 120 * 22
    assert log["inherited_planning_work"]["model_uniform_draws"] == 120 * 22 * 4
    assert log["retained_means_match"] and log["complete_root_execution_contract_matches"]


@pytest.mark.parametrize("field", ["fragment_actions", "initiation_step", "model_uniform_draws", "environment_random_draws"])
def test_invalid_execution_contract_cannot_supply_h2_targets(batch, field):
    path = batch / "branch_games.jsonl.gz"
    raw = list(module._rows(path))
    record = next(row for row in raw if row["option"] == "SNAKE_4")
    if field in ("fragment_actions", "initiation_step"):
        record["controller"][field] += 1
    elif field == "model_uniform_draws":
        record["planning_counts"][field] += 1
    else:
        record["game"]["work"][field] += 1
    write_rows(path, raw)
    with pytest.raises(ValueError, match="execution contract"):
        module.load_batch(batch)


def test_changed_original_mc_target_is_detected(batch):
    path = batch / "new_rows.jsonl.gz"
    means = list(module._rows(path))
    means[0]["target"][0] += 1
    write_rows(path, means)
    with pytest.raises(ValueError, match="MC means"):
        module.load_batch(batch)
