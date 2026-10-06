"""Paired suffix accounting, observed-time sampling, and exact stream provenance."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_paired_continuation_data_v92 as module


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_paired_continuation_data_v92.data_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired retained trajectories, no simulation or fitting.",
        ground_calls=0, main_campaign_calls=0, tree_fits=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def trajectory(option="SNAKE_4", n=22, status="LOST", factor=1, episode=0, replica=0, query="reward"):
    boards = [[1, 1, 2, 3, 4, index + 1] + [0] * 10 for index in range(n + 1)]
    steps = [dict(board=boards[i], next_board=boards[i + 1], score=(i + 1) * factor,
        status=status if i == n - 1 and status in module.TERMINAL else "ACTIVE") for i in range(n)]
    env_seed = 8310000000 + episode * 100 + replica
    duration = 0 if option == "H2" else int(option.split("_")[1])
    return dict(root=dict(board=boards[0], query=query, episode=episode), option=option, replica=replica,
        env_seed=env_seed, model_seed=env_seed + 1000000000000,
        game=dict(seed=env_seed, initial_board=boards[0], initial_spawns=[], final_board=boards[-1],
            steps=steps, status=status, return_score=sum(step["score"] for step in steps),
            work=dict(sampled_transitions=n, environment_random_draws=2 * n)),
        planning_counts=dict(model_uniform_draws=4 * n),
        controller=dict(selected_option=option, initiation_step=0, fragment_actions=min(duration, n)))


def write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_fixed_grid_differences_exclude_past_reward_and_do_not_append_terminal_neighbor():
    candidate = trajectory(factor=2)
    reference = trajectory("H2", status="WON")
    rows = module.extract_paired_tail_rows(candidate, reference)
    assert [row["step"] for row in rows] == [4, 20]
    assert rows[0]["target"] == [(253 - 10) / 2048, 1., -1.]
    assert rows[1]["target"] == [43 / 2048, 1., -1.]
    assert all(row["candidate_active"] and row["reference_active"] for row in rows)
    assert all(row["weight"] == 1 / 32 for row in rows)
    short = module.extract_paired_tail_rows(trajectory(n=7), trajectory("H2", n=7))
    assert [row["step"] for row in short] == [4]
    assert short[0]["weight"] == rows[0]["weight"]


def test_absorbed_side_has_zero_future_reward_and_zero_future_terminal_events():
    candidate = trajectory(n=2, status="LOST", episode=4, query="risk_goal")
    reference = trajectory("H2", status="WON", episode=4, query="risk_goal")
    rows = module.extract_paired_tail_rows(candidate, reference)
    assert rows[0]["target"] == [-243 / 2048, 0., -1.]
    assert all(not row["candidate_active"] and row["reference_active"] for row in rows)
    assert all(row["candidate_board"] == candidate["game"]["final_board"] for row in rows)
    assert all(row["query"] == "risk_goal" and row["episode"] == 4 for row in rows)
    assert module.extract_paired_tail_rows(trajectory(n=2), trajectory("H2", n=4)) == []


def test_coalesced_states_and_shared_suffixes_have_exact_zero_difference():
    reference = trajectory("H2")
    candidate = trajectory()
    for step in candidate["game"]["steps"][:4]:
        step["score"] += 100
    candidate["game"]["return_score"] += 400
    rows = module.extract_paired_tail_rows(candidate, reference)
    assert all(row["candidate_board"] == row["reference_board"] for row in rows)
    assert all(row["target"] == [0., 0., 0.] for row in rows)


@pytest.mark.parametrize("change", ["seed", "environment_draws", "model_draws", "query"])
def test_pair_requires_same_query_and_aligned_environment_and_model_streams(change):
    candidate, reference = trajectory(), trajectory("H2")
    if change == "seed":
        candidate["env_seed"] += 1
    elif change == "query":
        candidate["root"]["query"] = "risk_goal"
    elif change == "environment_draws":
        candidate["game"]["work"]["environment_random_draws"] += 1
    else:
        candidate["planning_counts"]["model_uniform_draws"] -= 1
    with pytest.raises(ValueError, match="streams|contract"):
        module.extract_paired_tail_rows(candidate, reference)


@pytest.fixture
def batch(tmp_path):
    raw, means = [], []
    for episode in (0, 4, 1):
        for replica in range(8):
            for index, option in enumerate(module.OPTIONS):
                status = "CUTOFF" if episode == 1 and replica == 7 and option == "SNAKE_4" else "LOST"
                raw.append(trajectory(option, factor=index + replica + 1, status=status, episode=episode, replica=replica))
        if episode != 1:
            for index, option in enumerate(module.OPTIONS[1:], start=1):
                means.append(dict(board=raw[-1]["root"]["board"], query="reward", episode=episode,
                    option=option, target=[253 * index / 2048, 0., 0.]))
    write_rows(tmp_path / "branch_games.jsonl.gz", raw)
    write_rows(tmp_path / "new_rows.jsonl.gz", means)
    return tmp_path


def test_batch_preserves_root_split_and_mc_means_and_censors_whole_root(batch):
    roots, rows, log = module.load_batch(batch)
    assert len(roots) == 3 and len(rows) == 2 * 4 * 8 * 2
    assert {row["episode"] for row in rows} == {0, 4}
    assert roots[-1]["censored"] and roots[-1]["mc_rows"] == []
    assert all(len(values) == 8 for values in roots[-1]["prefixes"].values())
    assert all(len(root["mc_rows"]) == 4 for root in roots[:2])
    assert log["counts"]["new_environment_transitions"] == log["counts"]["tree_fits"] == 0
    assert log["counts"]["censored_root_trajectories"] == 40
    assert log["inherited_environment_work"]["sampled_transitions"] == 120 * 22
    assert log["largest_mean_difference"] == 0 and log["paired_crn_contract_matches"]


def test_original_mc_disagreement_fails_before_labels_can_be_used(batch):
    path = batch / "new_rows.jsonl.gz"
    means = list(module._rows(path))
    means[0]["target"][0] += 1
    write_rows(path, means)
    with pytest.raises(ValueError, match="MC means"):
        module.load_batch(batch)
