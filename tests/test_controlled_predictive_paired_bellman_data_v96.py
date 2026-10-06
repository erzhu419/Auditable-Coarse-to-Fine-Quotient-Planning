"""Paired Bellman reward/event accounting and original-root compatibility."""
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_paired_bellman_data_v96 as module
from acfqp.science.controlled_predictive_paired_continuation_data_v92 import (
    extract_paired_tail_rows, load_batch as load_v92,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    before = request.session.testsfailed
    yield
    path = ROOT / "reports/controlled_predictive_paired_bellman_data_v96.data_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, test_failures=request.session.testsfailed - before,
        scope="Synthetic paired terminal records and V92 root compatibility; no environment or fitting.",
        ground_calls=0, main_campaign_calls=0, tree_fits=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def trajectory(option="SNAKE_4", n=38, status="LOST", episode=0, replica=0, query="reward", prefix_bonus=0):
    boards = [[1, 1, 2, 3, 4, index % 7 + 1] + [0] * 10 for index in range(n + 1)]
    steps = [dict(board=boards[i], next_board=boards[i + 1], score=i + 1 + (prefix_bonus if i < 4 else 0),
        status=status if i == n - 1 and status in module.TERMINAL else "ACTIVE") for i in range(n)]
    seed = 93_340_000_000 + episode * 100 + replica
    duration = 0 if option == "H2" else int(option.split("_")[1])
    return dict(root=dict(board=boards[0], query=query, episode=episode), option=option, replica=replica,
        env_seed=seed, model_seed=seed + 1_000_000_000_000,
        game=dict(seed=seed, initial_board=boards[0], initial_spawns=[], final_board=boards[-1],
            steps=steps, status=status, return_score=sum(step["score"] for step in steps),
            work=dict(sampled_transitions=n, environment_random_draws=2 * n)),
        planning_counts=dict(model_uniform_draws=4 * n),
        controller=dict(selected_option=option, initiation_step=0, fragment_actions=min(duration, n)))


def write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_unequal_terminal_times_preserve_synchronous_grid_and_telescope_exactly():
    candidate, reference = trajectory(n=7), trajectory("H2", status="WON")
    rows = module.extract_paired_bellman_rows(candidate, reference)
    previous = extract_paired_tail_rows(candidate, reference)
    assert [row["step"] for row in rows] == [4, 20, 36]
    assert [row["target"] for row in rows] == [row["target"] for row in previous]
    assert [row["n_target"] for row in rows] == [
        [-182 / 2048, 1., 0.], [-456 / 2048, 0., 0.], [-75 / 2048, 0., -1.]]
    assert [sum(row["n_target"][i] for row in rows) for i in range(3)] == rows[0]["target"]
    assert rows[0]["target"] == [-713 / 2048, 1., -1.]
    assert [row["candidate_steps"] for row in rows] == [3, 0, 0]
    assert [row["reference_steps"] for row in rows] == [16, 16, 2]
    assert [row["candidate_active"] for row in rows] == [True, False, False]
    assert [row["next_reference_active"] for row in rows] == [True, True, False]
    assert all(not row["next_candidate_active"] for row in rows)
    assert all(row["next_candidate_board"] == candidate["game"]["final_board"] for row in rows)
    for current, following in zip(rows, rows[1:]):
        assert current["next_reference_board"] == following["reference_board"]
        assert current["next_candidate_board"] == following["candidate_board"]
    assert rows[-1]["next_reference_board"] == reference["game"]["final_board"]
    assert all(row["weight"] == 1 / 32 for row in rows)


@pytest.mark.parametrize("candidate_length", [2, 4])
def test_initially_absorbed_side_never_repeats_its_terminal_event(candidate_length):
    candidate = trajectory(n=candidate_length, episode=4, query="risk_goal")
    reference = trajectory("H2", n=21, status="WON", episode=4, query="risk_goal")
    rows = module.extract_paired_bellman_rows(candidate, reference)
    assert [row["n_target"] for row in rows] == [[-200 / 2048, 0., 0.], [-21 / 2048, 0., -1.]]
    assert all(not row["candidate_active"] and not row["next_candidate_active"] for row in rows)
    assert all(row["candidate_steps"] == 0 and row["query"] == "risk_goal" and row["episode"] == 4 for row in rows)


@pytest.mark.parametrize("n,indices", [(4, []), (5, [4]), (20, [4]), (21, [4, 20])])
def test_terminal_boundary_includes_event_once_without_outcome_selected_last_row(n, indices):
    rows = module.extract_paired_bellman_rows(trajectory(n=n), trajectory("H2", n=n, status="WON"))
    assert [row["step"] for row in rows] == indices
    if rows:
        assert rows[-1]["n_target"] == [0., 1., -1.]
        assert not rows[-1]["next_candidate_active"] and not rows[-1]["next_reference_active"]
        assert sum(row["n_target"][1] for row in rows) == 1
        assert all(row["weight"] == 1 / 32 for row in rows)


def test_coalesced_synchronous_states_have_zero_bellman_and_complete_difference():
    rows = module.extract_paired_bellman_rows(trajectory(prefix_bonus=100), trajectory("H2"))
    assert rows
    for row in rows:
        assert row["candidate_board"] == row["reference_board"]
        assert row["next_candidate_board"] == row["next_reference_board"]
        assert row["candidate_active"] == row["reference_active"]
        assert row["next_candidate_active"] == row["next_reference_active"]
        assert row["target"] == row["n_target"] == [0., 0., 0.]


def test_cutoff_cannot_supply_bellman_labels():
    assert module.extract_paired_bellman_rows(trajectory(status="CUTOFF"), trajectory("H2")) == []


@pytest.fixture
def batch(tmp_path):
    raw, means = [], []
    for episode, query in ((0, "reward"), (4, "risk_goal"), (1, "reward")):
        for replica in range(8):
            for index, option in enumerate(module.OPTIONS):
                status = "CUTOFF" if episode == 1 and replica == 7 and option == "SNAKE_4" else "LOST"
                raw.append(trajectory(option, n=22, status=status, episode=episode,
                                      replica=replica, query=query, prefix_bonus=index))
        if episode != 1:
            means.extend(dict(board=raw[-1]["root"]["board"], query=query, episode=episode,
                option=option, target=[4 * index / 2048, 0., 0.])
                for index, option in enumerate(module.OPTIONS[1:], start=1))
    write_rows(tmp_path / "branch_games.jsonl.gz", raw)
    write_rows(tmp_path / "new_rows.jsonl.gz", means)
    return tmp_path


def test_batch_matches_v92_roots_and_reads_once_with_whole_censor_costs_retained(batch, monkeypatch):
    opened, original = [], module._rows

    def recorded(path):
        opened.append(Path(path).name)
        yield from original(path)

    monkeypatch.setattr(module, "_rows", recorded)
    roots, rows, log = module.load_batch(batch)
    previous, _, previous_log = load_v92(batch)
    assert opened == ["new_rows.jsonl.gz", "branch_games.jsonl.gz"]
    assert roots == previous
    assert len(roots) == 3 and len(rows) == 128
    assert {(row["query"], row["episode"]) for row in rows} == {("reward", 0), ("risk_goal", 4)}
    assert roots[-1]["censored"] and roots[-1]["mc_rows"] == []
    assert all(len(prefixes) == 8 for prefixes in roots[-1]["prefixes"].values())
    counts = log["counts"]
    assert counts["training_paired_rows"] == counts["heldout_paired_rows"] == 64
    assert counts["bootstrap_rows"] == counts["terminal_anchor_rows"] == 64
    assert counts["zero_diagonal_rows"] == counts["diagonal_rows"] == 128
    assert counts["candidate_absorbed_rows"] == counts["reference_absorbed_rows"] == 0
    assert counts["next_candidate_absorbed_rows"] == counts["next_reference_absorbed_rows"] == 64
    assert counts["censored_root_trajectories"] == 40
    assert log["inherited_environment_work"] == previous_log["inherited_environment_work"]
    assert log["inherited_planning_work"] == previous_log["inherited_planning_work"]
    assert log["inherited_environment_work"]["sampled_transitions"] == 120 * 22
    assert counts["new_environment_transitions"] == counts["tree_fits"] == 0
    assert log["retained_means_match"] and log["paired_crn_contract_matches"]


def test_loader_rejects_unaligned_execution_contract(batch):
    path = batch / "branch_games.jsonl.gz"
    rows = list(module._rows(path))
    rows[1]["planning_counts"]["model_uniform_draws"] -= 4
    write_rows(path, rows)
    with pytest.raises(ValueError, match="execution contract"):
        module.load_batch(batch)


def test_loader_requires_original_mc_means_to_match(batch):
    path = batch / "new_rows.jsonl.gz"
    rows = list(module._rows(path))
    rows[0]["target"][0] += 1
    write_rows(path, rows)
    with pytest.raises(ValueError, match="MC means"):
        module.load_batch(batch)
