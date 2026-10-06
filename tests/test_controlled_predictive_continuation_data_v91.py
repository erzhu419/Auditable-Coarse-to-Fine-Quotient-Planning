"""Terminal accounting, H2 boundary supervision, and root-level censoring."""
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_continuation_data_v91 as module


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_continuation_data_v91.data_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic retained branch trajectories; no environment calls or model fitting.",
        ground_calls=0, main_campaign_calls=0, tree_fits=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def trajectory(n=6, status="LOST", episode=0, query="reward", option="SNAKE_4", replica=0, factor=1):
    boards = [[1, 1, 2, 3, 4, index + 1] + [0] * 10 for index in range(n + 1)]
    steps = [dict(board=boards[index], next_board=boards[index + 1], score=(index + 1) * factor,
        status=status if index == n - 1 and status in module.TERMINAL else "ACTIVE") for index in range(n)]
    return dict(root=dict(board=boards[0], query=query, episode=episode), option=option, replica=replica,
        game=dict(initial_board=boards[0], final_board=boards[-1], steps=steps, status=status,
                  return_score=sum(step["score"] for step in steps), work={"sampled_transitions": n}),
        planning_counts={"model_uniform_draws": 4 * n})


def _write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


@pytest.mark.parametrize("length,status", [(2, "LOST"), (4, "WON")])
def test_terminal_inside_or_exactly_at_boundary_is_counted_only_directly(length, status):
    raw = trajectory(length, status)
    prefix = module.extract_prefix(raw)
    assert prefix["status"] == status
    assert prefix["direct"] == prefix["full_target"]
    assert prefix["direct"][1:] == [float(status == "LOST"), float(status == "WON")]
    assert prefix["boundary_board"] == raw["game"]["final_board"]
    assert module.extract_h2_tail_rows(raw) == []


def test_boundary_reward_and_event_are_not_duplicated_with_tail():
    raw = trajectory(8, "WON", query="risk_goal")
    prefix = module.extract_prefix(raw)
    rows = module.extract_h2_tail_rows(raw)
    assert prefix["status"] == "ACTIVE" and prefix["direct"] == [10 / 2048, 0., 0.]
    assert prefix["boundary_board"] == raw["game"]["steps"][4]["board"]
    assert rows[0]["step"] == 4 and rows[0]["board"] == prefix["boundary_board"]
    assert rows[0]["target"] == [26 / 2048, 0., 1.]
    assert [a + b for a, b in zip(prefix["direct"], rows[0]["target"])] == prefix["full_target"]
    assert all(row["query"] == "risk_goal" for row in rows)


def test_tail_stride_last_active_state_and_trajectory_weight():
    raw = trajectory(38, episode=4)
    rows = module.extract_h2_tail_rows(raw)
    assert [row["step"] for row in rows] == [4, 20, 36, 37]
    assert sum(row["weight"] for row in rows) == pytest.approx(1.)
    assert rows[-1]["target"] == [38 / 2048, 1., 0.]
    assert all(row["episode"] == 4 and row["option"] == "SNAKE_4" and row["replica"] == 0 for row in rows)
    raw = trajectory(37)
    assert [row["step"] for row in module.extract_h2_tail_rows(raw)] == [4, 20, 36]


@pytest.mark.parametrize("length,prefix_status", [(3, "CUTOFF"), (6, "ACTIVE")])
def test_cutoff_keeps_prefix_but_has_no_terminal_target(length, prefix_status):
    raw = trajectory(length, "CUTOFF")
    prefix = module.extract_prefix(raw)
    assert prefix["status"] == prefix_status
    assert prefix["full_target"] is None and prefix["direct"][1:] == [0., 0.]
    assert module.extract_h2_tail_rows(raw) == []


@pytest.fixture
def batch(tmp_path):
    raw, means = [], []
    for episode in (0, 4, 1):
        group = []
        for replica in range(module.REPLICAS):
            for option_index, option in enumerate(module.OPTIONS):
                status = "CUTOFF" if episode == 1 and replica == 7 and option == "SNAKE_4" else "LOST"
                group.append(trajectory(6, status, episode=episode, query="risk_goal", option=option,
                                        replica=replica, factor=option_index + replica + 1))
        raw.extend(group)
        if episode != 1:
            for option_index, option in enumerate(module.OPTIONS[1:], start=1):
                means.append(dict(board=group[0]["root"]["board"], query="risk_goal", episode=episode,
                                  option=option, target=[21 * option_index / 2048, 0., 0.]))
    _write_rows(tmp_path / "branch_games.jsonl.gz", raw)
    _write_rows(tmp_path / "new_rows.jsonl.gz", means)
    return tmp_path


def test_batch_preserves_episode_split_and_excludes_entire_censored_root(batch):
    roots, rows, log = module.load_batch(batch)
    assert len(roots) == 3 and [root["episode"] for root in roots] == [0, 4, 1]
    assert all(len(root["mc_rows"]) == 4 for root in roots[:2])
    assert roots[-1]["censored"] and roots[-1]["mc_rows"] == []
    assert all(len(prefixes) == 8 for prefixes in roots[-1]["prefixes"].values())
    assert {row["episode"] for row in rows} == {0, 4}
    assert len(rows) == 160 and all(row["query"] == "risk_goal" for row in rows)
    assert log["retained_means_match"] and log["largest_mean_difference"] == 0
    counts = log["counts"]
    assert counts["training_eligible_roots"] == counts["heldout_eligible_roots"] == counts["censored_roots"] == 1
    assert counts["trajectories_read"] == 120 and counts["steps_read"] == 720
    assert counts["training_tail_rows"] == counts["heldout_tail_rows"] == 80
    assert counts["new_environment_transitions"] == counts["tree_fits"] == 0
    assert log["inherited_environment_work"]["sampled_transitions"] == 720
    assert log["inherited_planning_work"]["model_uniform_draws"] == 2880


def test_batch_rejects_disagreement_with_retained_mc_means(batch):
    path = batch / "new_rows.jsonl.gz"
    means = list(module._rows(path))
    means[0]["target"][0] += 1
    _write_rows(path, means)
    with pytest.raises(ValueError, match="paired means"):
        module.load_batch(batch)


def test_missing_replica_excludes_root_without_silently_reweighting(batch):
    path = batch / "branch_games.jsonl.gz"
    raw = list(module._rows(path))
    # Remove a terminal record from an otherwise complete root, and its old mean labels.
    raw = [row for row in raw if not (row["root"]["episode"] == 0 and row["replica"] == 7 and row["option"] == "H2")]
    _write_rows(path, raw)
    path = batch / "new_rows.jsonl.gz"
    _write_rows(path, [row for row in module._rows(path) if row["episode"] != 0])
    roots, rows, log = module.load_batch(batch)
    assert roots[0]["censored"] and roots[0]["mc_rows"] == []
    assert {row["episode"] for row in rows} == {4}
    assert log["counts"]["censored_roots"] == 2
    assert log["counts"]["trajectories_read"] == 119


def test_mismatched_total_reward_is_not_silently_used_as_tail_supervision(batch):
    path = batch / "branch_games.jsonl.gz"
    raw = list(module._rows(path))
    raw[0]["game"]["return_score"] += 1
    _write_rows(path, raw)
    with pytest.raises(ValueError, match="recorded transitions"):
        module.load_batch(batch)
