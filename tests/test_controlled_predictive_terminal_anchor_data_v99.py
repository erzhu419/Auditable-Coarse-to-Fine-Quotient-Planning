"""Single-pass retained V98 loading, variable replicas and whole-root censoring."""
from collections import Counter
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_terminal_anchor_data_v99 as module
from acfqp.science.controlled_predictive_root_coverage_v98 import source_seed, branch_seed


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    before = request.session.testsfailed
    yield
    path = ROOT / "reports/controlled_predictive_terminal_anchor_data_v99.checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, test_failures=request.session.testsfailed - before,
        scope="Synthetic V98 retained files; real V96 extraction, no physical environment or fitting.",
        ground_calls=0, tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def batch(folder, replicas):
    board, raw, accepted, records = [1] * 10 + [0] * 6, [], [], []
    work, planning, outcomes = Counter(), Counter(), Counter()
    partition = {name: dict(source_transitions=0, branch_transitions=0, total_transitions=0)
                 for name in ("training", "heldout", "unincorporated")}
    for cursor in (7, 8, 9):
        episode, qi = divmod(cursor, 2)
        query = tuple(module.QUERIES)[qi]
        root = dict(board=board, episode=episode, query=query, step=0,
                    source_seed=source_seed(9, episode, query))
        complete = cursor != 9
        disposition = ("training" if episode % 5 != 4 else "heldout") if complete else "unincorporated"
        size = replicas if complete else replicas // 2
        seed_base = branch_seed(9, episode, query)
        for replica in range(size):
            for index, option in enumerate(module.OPTIONS):
                seed = seed_base + replica
                steps = [dict(board=board, next_board=board, score=4 * (index + 1),
                    status="LOST" if step == 21 else "ACTIVE") for step in range(22)]
                ground, controller_work = {"sampled_transitions": 22, "environment_random_draws": 44}, {"model_uniform_draws": 88}
                raw.append(dict(root=root, option=option, replica=replica, env_seed=seed, model_seed=seed + 10 ** 12,
                    game=dict(seed=seed, initial_board=board, initial_spawns=[], final_board=board,
                        steps=steps, return_score=88 * (index + 1), status="LOST", work=ground),
                    planning_counts=controller_work, controller=dict(selected_option=option, initiation_step=0,
                        fragment_actions=0 if option == "H2" else int(option.split("_")[1]))))
                work.update(ground)
                planning.update(controller_work)
                outcomes["LOST"] += 1
        branch_steps = size * 5 * 22
        record = dict(cursor=cursor, episode=episode, query=query, replicas=replicas, root=root,
            branch_seed=seed_base, source_status="LOST", branch_trajectories=size * 5,
            branch_transitions=branch_steps, source_transitions=2, branch_cutoff_trajectories=0,
            complete_block=complete, disposition=disposition, paired_rows=replicas * 4 * 2 if complete else 0)
        records.append(record)
        for name, value in (("source_transitions", 2), ("branch_transitions", branch_steps), ("total_transitions", branch_steps + 2)):
            partition[disposition][name] += value
        if complete:
            accepted.append(dict(root, replicas=replicas, heldout=episode % 5 == 4,
                paired_rows=replicas * 8, source_transitions=2, branch_transitions=branch_steps))
    source_work = dict(sampled_transitions=6, environment_random_draws=24)
    counts = dict(complete_roots=2, training_roots=1, heldout_roots=1, paired_rows=replicas * 16,
        training_paired_rows=replicas * 8, heldout_paired_rows=replicas * 8,
        terminal_anchor_rows=replicas * 8, bootstrap_rows=replicas * 8)
    acquisition = dict(life=9, replicas=replicas, budget=6 + work["sampled_transitions"],
        used_transitions=6 + work["sampled_transitions"], start_cursor=7, next_cursor=10, episode_cutoff=6,
        root_records=records, completed_roots=accepted, counts=counts, cost_partition=partition,
        source=dict(ground_work=source_work, planning_counts={"model_uniform_draws": 24}),
        branches=dict(ground_work=dict(work), planning_counts=dict(planning), outcomes=dict(outcomes)))
    (folder / "construction.json").write_text(json.dumps(dict(acquisition=acquisition)))
    write_rows(folder / "branch_games.jsonl.gz", raw)
    return acquisition, raw


@pytest.mark.parametrize("replicas", [4, 8])
def test_variable_complete_cohorts_single_branch_read_and_inherited_costs(tmp_path, monkeypatch, replicas):
    acquisition, raw = batch(tmp_path, replicas)
    opened, original = [], module._rows

    def recorded(path):
        opened.append(Path(path).name)
        yield from original(path)

    monkeypatch.setattr(module, "_rows", recorded)
    rows, log = module.load_batch(tmp_path)
    assert opened == ["branch_games.jsonl.gz"]
    assert log["replicas"] == replicas and log["start_cursor"] == 7 and log["next_cursor"] == 10
    assert log["episode_cutoff"] == 6 and len(rows) == replicas * 16
    assert {(row["query"], row["episode"]) for row in rows} == {("risk_goal", 3), ("reward", 4)}
    assert all(row["weight"] == 1 / 32 for row in rows)
    for row in rows:
        option_index = module.OPTIONS.index(row["option"])
        remaining = 18 if row["step"] == 4 else 2
        segment = 16 if row["step"] == 4 else 2
        assert row["target"] == [remaining * 4 * option_index / 2048, 0., 0.]
        assert row["n_target"] == [segment * 4 * option_index / 2048, 0., 0.]
    assert log["counts"]["excluded_branch_roots"] == 1
    assert log["counts"]["excluded_branch_trajectories"] == 5 * replicas // 2
    assert log["counts"]["trajectories_read"] == len(raw)
    assert log["counts"]["steps_read"] == len(raw) * 22
    assert log["counts"]["training_paired_rows"] == log["counts"]["heldout_paired_rows"] == replicas * 8
    assert log["root_rosters"]["risk_goal"]["training"][0]["episode"] == 3
    assert log["root_rosters"]["reward"]["heldout"][0]["episode"] == 4
    assert log["inherited_source_work"] == acquisition["source"]["ground_work"]
    assert log["inherited_branch_work"] == acquisition["branches"]["ground_work"]
    assert log["inherited_cost_partition"] == acquisition["cost_partition"]
    assert log["inherited_physical_transitions"] == acquisition["used_transitions"]
    assert log["counts"]["source_trajectory_files_read"] == 0
    assert log["counts"]["new_environment_transitions"] == log["counts"]["tree_fits"] == 0


def test_first_four_complete_replicas_of_incomplete_eight_replica_root_never_supply_rows(tmp_path):
    acquisition, raw = batch(tmp_path, 8)
    partial = [record for record in raw if record["root"]["query"] == "risk_goal" and record["root"]["episode"] == 4]
    assert len(partial) == 20 and all(record["game"]["status"] == "LOST" for record in partial)
    rows, log = module.load_batch(tmp_path)
    assert not any(row["query"] == "risk_goal" and row["episode"] == 4 for row in rows)
    assert log["inherited_cost_partition"]["unincorporated"]["branch_transitions"] == 20 * 22


@pytest.mark.parametrize("change", ["cursor", "root_roster", "branch_cost", "source_cost", "row_count"])
def test_ledger_window_roster_and_cost_mismatches_prevent_loading(tmp_path, change):
    acquisition, raw = batch(tmp_path, 4)
    if change == "cursor":
        acquisition["root_records"][0]["episode"] += 1
    elif change == "root_roster":
        acquisition["completed_roots"].pop()
    elif change == "branch_cost":
        acquisition["branches"]["ground_work"]["sampled_transitions"] += 1
    elif change == "source_cost":
        acquisition["source"]["ground_work"]["sampled_transitions"] += 1
    else:
        acquisition["completed_roots"][0]["paired_rows"] += 1
    (tmp_path / "construction.json").write_text(json.dumps(dict(acquisition=acquisition)))
    with pytest.raises(ValueError, match="window|accepted|ledger|costs"):
        module.load_batch(tmp_path)
