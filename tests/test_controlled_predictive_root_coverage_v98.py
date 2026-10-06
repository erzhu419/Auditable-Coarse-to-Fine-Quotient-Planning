"""Hard acquisition budgets and complete variable-replica Bellman cohorts."""
from collections import Counter
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_budgeted_fragments_v86 as budgeted
from acfqp.science import controlled_predictive_root_coverage_v98 as module


ROOT = Path(__file__).resolve().parents[1]
MOCK_COUNTS = Counter()
BOARD = [1] * 10 + [0] * 6
LENGTHS = dict(zip(module.OPTIONS, (5, 6, 7, 8, 9)))


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    before = request.session.testsfailed
    MOCK_COUNTS.clear()
    yield
    path = ROOT / "reports/controlled_predictive_root_coverage_v98.checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, test_failures=request.session.testsfailed - before,
        scope="V86 budget scheduling with synthetic trajectories and real V96 row extraction; no physical environment or fitting.",
        mock_calls=dict(MOCK_COUNTS), ground_calls=0, tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture
def fake_environment(monkeypatch):
    calls = {"source": [], "branch": []}

    class Controller:
        def __init__(self, selector, query, rule, rng, mode="FRAGMENT", immediate=False, fixed_option=None):
            self.option, self.rng = fixed_option, rng
            self.work, self.events = Counter(), []
            self.fragment_actions = self.remaining_actions = 0
            self.initiation_step = self.selected_option = None
            self.finished_fragment = False

        def choose(self, board, step):
            if self.option is not None and self.selected_option is None:
                self.selected_option, self.initiation_step = self.option, step
                self.remaining_actions = 0 if self.option == "H2" else int(self.option.split("_")[1])
                self.events.append(dict(option=self.option, step=step))
            if self.remaining_actions:
                self.fragment_actions += 1
                self.remaining_actions -= 1
            self.finished_fragment = not self.remaining_actions
            for _ in range(4):
                self.rng.random()
            self.work["model_uniform_draws"] += 4
            return self.option or "H2"

    def trajectory(board, seed, actor, max_steps, desired, source=False):
        length = min(max_steps, desired)
        status = "LOST" if length == desired else "CUTOFF"
        steps = []
        for index in range(length):
            actor(tuple(board), index)
            steps.append(dict(board=list(board), next_board=list(board), score=4,
                status=status if index == length - 1 else "ACTIVE"))
        return dict(seed=seed, initial_board=list(board), initial_spawns=[1, 2] if source else [],
            final_board=list(board), steps=steps, status=status, steps_count=length,
            return_score=4 * length, work=dict(sampled_transitions=length,
                environment_random_draws=2 * length + (4 if source else 0)))

    def source(seed, actor, max_steps):
        MOCK_COUNTS["source_games"] += 1
        calls["source"].append((seed, max_steps))
        return trajectory(BOARD, seed, actor, max_steps, 2, source=True)

    def branch(board, seed, actor, max_steps):
        MOCK_COUNTS["branch_games"] += 1
        calls["branch"].append((seed, actor.__self__.option, max_steps))
        return trajectory(board, seed, actor, max_steps, LENGTHS[actor.__self__.option])

    monkeypatch.setattr(budgeted, "FragmentController", Controller)
    monkeypatch.setattr(budgeted, "run_episode", source)
    monkeypatch.setattr(budgeted, "rollout_from_board", branch)
    return calls


def read_rows(path):
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle]


def assert_accounted(log):
    source = log["source"]["ground_work"].get("sampled_transitions", 0)
    branches = log["branches"]["ground_work"].get("sampled_transitions", 0)
    assert source + branches == log["used_transitions"]
    assert sum(part["total_transitions"] for part in log["cost_partition"].values()) == source + branches
    for kind, total in (("source", source), ("branch", branches)):
        assert sum(part[f"{kind}_transitions"] for part in log["cost_partition"].values()) == total


def test_four_and_eight_replicas_extract_complete_roots_and_share_physics_seeds(fake_environment, tmp_path):
    retained = {}
    for replicas in (4, 8):
        budget = 2 + sum(LENGTHS.values()) * replicas
        folder = tmp_path / str(replicas)
        rows, cursor, log = module.acquire_batch(9, replicas, None, budget, 0, folder)
        assert cursor == 1 and log["episode_cutoff"] == 1
        assert log["used_transitions"] == budget and log["unused_budget"] == 0
        assert log["counts"]["complete_roots"] == log["counts"]["training_roots"] == 1
        assert log["counts"]["branch_trajectories"] == 5 * replicas
        assert len(rows) == 4 * replicas and all(row["weight"] == 1 / 32 for row in rows)
        assert all(row["step"] == 4 and row["query"] == "reward" and row["episode"] == 0 for row in rows)
        assert {row["replica"] for row in rows} == set(range(replicas))
        for row in rows:
            assert row["target"] == row["n_target"] == [4 * (LENGTHS[row["option"]] - 5) / 2048, 0., 0.]
        assert log["completed_roots"][0]["paired_rows"] == 4 * replicas
        assert log["cost_partition"]["training"]["total_transitions"] == budget
        assert log["root_records"][0]["complete_block"] and log["root_records"][0]["discard_reason"] is None
        assert_accounted(log)
        retained[replicas] = read_rows(folder / "branch_games.jsonl.gz")
        assert len(read_rows(folder / "source_games.jsonl.gz")) == 1
    assert fake_environment["source"][0][0] == fake_environment["source"][1][0] == module.source_seed(9, 0, "reward")
    assert retained[4] == retained[8][:20]
    for raw in retained[8]:
        assert raw["env_seed"] == module.branch_seed(9, 0, "reward") + raw["replica"]
        assert raw["model_seed"] == raw["env_seed"] + 10 ** 12


def test_partial_root_spends_exact_budget_and_next_stage_advances_without_resumption(fake_environment, tmp_path):
    rows, cursor, first = module.acquire_batch(9, 4, None, 43, 0, tmp_path / "first")
    assert rows == [] and cursor == 1
    assert first["used_transitions"] == 43 and first["budget_exhausted"]
    assert first["counts"]["branch_trajectories"] == 7 and first["counts"]["incomplete_roots"] == 1
    assert first["root_records"][0]["branch_cutoff_cause"] == "budget"
    assert first["cost_partition"]["unincorporated"] == {
        "source_transitions": 2, "branch_transitions": 41, "total_transitions": 43}
    assert read_rows(tmp_path / "first/branch_games.jsonl.gz")[-1]["game"]["status"] == "CUTOFF"
    rows, next_cursor, second = module.acquire_batch(9, 4, None, 142, cursor, tmp_path / "second")
    assert next_cursor == 2 and second["start_cursor"] == 1
    assert len(rows) == 16 and {row["query"] for row in rows} == {"risk_goal"}
    assert second["root_records"][0]["episode"] == 0
    assert fake_environment["source"][-1][0] == module.source_seed(9, 0, "risk_goal")
    assert first["used_transitions"] + second["used_transitions"] == 185
    assert_accounted(first)
    assert_accounted(second)


def test_truncated_source_with_observed_trigger_produces_no_labels_or_branch_calls(fake_environment, tmp_path):
    rows, cursor, log = module.acquire_batch(10, 8, None, 1, 0, tmp_path)
    assert rows == [] and cursor == 1 and fake_environment["branch"] == []
    record = log["root_records"][0]
    assert record["root"] is not None and record["source_status"] == "CUTOFF"
    assert record["source_cutoff_cause"] == "budget" and record["discard_reason"] == "source_cutoff"
    assert log["completed_roots"] == [] and log["counts"]["source_cutoffs"] == 1
    assert log["cost_partition"]["unincorporated"]["total_transitions"] == 1
    assert len(read_rows(tmp_path / "source_games.jsonl.gz")) == 1
    assert read_rows(tmp_path / "branch_games.jsonl.gz") == []
    assert_accounted(log)


def test_complete_heldout_root_is_retained_and_charged_separately(fake_environment, tmp_path):
    rows, cursor, log = module.acquire_batch(10, 4, None, 142, 8, tmp_path)
    assert cursor == 9 and log["episode_cutoff"] == 5
    assert len(rows) == 16 and all(row["episode"] == 4 for row in rows)
    assert log["counts"]["training_roots"] == 0 and log["counts"]["heldout_roots"] == 1
    assert log["queries"]["reward"]["heldout_episodes"] == [4]
    assert log["queries"]["reward"]["training_episodes"] == []
    assert log["cost_partition"]["heldout"]["total_transitions"] == 142
    assert log["completed_roots"][0]["heldout"]
    assert_accounted(log)
