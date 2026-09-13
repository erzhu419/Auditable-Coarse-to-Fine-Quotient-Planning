"""Fixed generation, shared physical prefix and exact repeat-count replay."""

from collections import Counter
from copy import deepcopy
import json
import random

import pytest

from acfqp.domains.standard_2048 import legal_actions_v1, state_from_board_v1, Swipe2048Status
from acfqp.science import controlled_predictive_new_starts_v28 as core
from acfqp.science.controlled_predictive_quotient_v1 import Query


BOARD = (1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2, 4, 5, 6, 2, 8)
ROOT = 2, BOARD
A = 1, (0,) + BOARD[1:]
B = 1, BOARD[:1] + (0,) + BOARD[2:]
ACTIONS = ("DOWN", "LEFT", "RIGHT", "UP")


class PrefixProvider:
    calls = []

    def __init__(self, seed):
        self.seed = seed
        self.work_counts = Counter()
        self.provider_seconds = 0.

    def sample_batch(self, key, action, batch_index):
        self.calls.append((self.seed, key, action, batch_index))
        self.work_counts.update(row_requests=1, physical_draws=256)
        self.work_counts["first_batch_requests" if batch_index == 0 else "repeat_batch_requests"] += 1
        self.provider_seconds += .001
        probability = .75 if batch_index < 7 else .25
        return ((probability, A, 0.), (1. - probability, B, 0.))


@pytest.fixture
def prefix(monkeypatch):
    PrefixProvider.calls = []
    monkeypatch.setattr(core, "BatchRowSampleProvider", PrefixProvider)
    records, accounting = core.acquire_common_prefix(ROOT, 1234)
    return records, accounting


def test_generator_is_deterministic_active_and_retains_declared_pair_geometry():
    global_state = random.getstate()
    boards = [core.generate_board(seed) for seed in (17, 29, 43)]
    assert random.getstate() == global_state
    assert len(set(boards)) == 3
    overwritten = {0, 1, 10, 14}
    for seed, board in zip((17, 29, 43), boards):
        assert board == core.generate_board(seed)
        assert len(board) == 16 and all(1 <= rank <= 10 for rank in board)
        assert board[0] == board[1] and board[10] == board[14]
        assert state_from_board_v1(board).status is Swipe2048Status.ACTIVE
        assert tuple(sorted(action.value for action in legal_actions_v1(board))) == ACTIONS
        for cell in range(16):
            if cell % 4 and not {cell, cell - 1} & overwritten:
                assert board[cell] != board[cell - 1]
            if cell >= 4 and not {cell, cell - 4} & overwritten:
                assert board[cell] != board[cell - 4]


def test_physical_prefix_has_only_root_roundrobin_and_indices_zero_through_seven(prefix):
    records, accounting = prefix
    assert len(PrefixProvider.calls) == len(records) == 32
    assert PrefixProvider.calls == [(1234, ROOT, ACTIONS[index % 4], index // 4)
                                    for index in range(32)]
    assert [record["batch_index"] for record in records] == [index // 4 for index in range(32)]
    assert [record["kind"] for record in records] == ["FIRST_OBSERVATION"] * 4 + ["REPEAT_OBSERVATION"] * 28
    assert accounting["physical_batches"] == 32 and accounting["physical_draws"] == 8192
    assert accounting["root_action_batch_counts"] == dict.fromkeys(ACTIONS, 8)
    assert accounting["provider_counts"] == {"row_requests": 32, "physical_draws": 8192,
        "first_batch_requests": 4, "repeat_batch_requests": 28}
    assert accounting["planner_constructions"] == accounting["query_solves"] == 0


def test_query_replay_keeps_pooled_counts_and_only_prepares_one_query_without_provider(prefix, monkeypatch):
    records, _ = prefix
    records = json.loads(json.dumps(records))
    original = deepcopy(records)
    def forbidden(*args, **kwargs):
        pytest.fail("Query preparation sampled or performed a warm conversion")
    monkeypatch.setattr(core, "BatchRowSampleProvider", forbidden)
    monkeypatch.setattr(core.CachedGapPlannerState, "from_warm", forbidden)
    state, accounting = core.prepare_query(ROOT, "q", Query(1., 2., 3.), records)
    assert state.queries == {"q": Query(1., 2., 3.)}
    assert set(state.caches) == set(state.score_caches) == {"q"}
    assert not state.caches["q"].dirty and not state.score_caches["q"].dirty
    assert state.spent_batches == 32 and state.batch_counts == {(ROOT, action): 8 for action in ACTIONS}
    for action in ACTIONS:
        assert state.outcome_counts[ROOT, action] == {(A, 0.): 1408, (B, 0.): 640}
        assert state.rows[ROOT, action] == ((1408 / 2048, A, 0.), (640 / 2048, B, 0.))
    assert state.reverse_dependencies[A] == state.reverse_dependencies[B] == {ROOT}
    assert all(key == ROOT for key, _ in state.rows)
    assert state.profiles[A].status == state.profiles[B].status == "ACTIVE"
    assert accounting["retained_model_batches"] == accounting["replayed_batches"] == 32
    assert accounting["new_provider_calls"] == accounting["new_physical_draws"] == 0
    assert accounting["work_counts"]["gap_score_queries"] == 1
    assert accounting["work_counts"]["gap_score_cache_initializations"] == 1
    assert state.engine_seconds == accounting["whole_seconds"]
    assert records == original


def test_two_queries_and_branch_clones_do_not_share_pooled_counts_or_cache_maps(prefix):
    records, _ = prefix
    first, _ = core.prepare_query(ROOT, "first", Query(1., 1., 0.), records)
    second, _ = core.prepare_query(ROOT, "second", Query(1., 5., 0.), records)
    branch = first.clone()
    branch.observe_batch(ROOT, "LEFT", ((1., A, 0.),))
    branch.solve("first")
    branch._gap_scores("first")
    assert branch.batch_counts[ROOT, "LEFT"] == 9
    assert first.batch_counts[ROOT, "LEFT"] == second.batch_counts[ROOT, "LEFT"] == 8
    assert first.spent_batches == second.spent_batches == 32
    assert set(first.caches) == {"first"} and set(second.caches) == {"second"}
    assert first.rows[ROOT, "LEFT"] == second.rows[ROOT, "LEFT"]
    assert first.rows[ROOT, "LEFT"] != branch.rows[ROOT, "LEFT"]
    assert not first.caches["first"].dirty and not first.score_caches["first"].dirty


@pytest.mark.parametrize("change", ["length", "index", "order", "kind"])
def test_prefix_replay_rejects_real_record_order_and_batch_count_mismatches(prefix, change):
    records, _ = prefix
    records = deepcopy(records)
    if change == "length":
        records.pop()
    elif change == "index":
        records[4]["batch_index"] = 0
    elif change == "order":
        records[0], records[1] = records[1], records[0]
    else:
        records[4]["kind"] = "FIRST_OBSERVATION"
    with pytest.raises(ValueError, match="prefix"):
        core.prepare_query(ROOT, "q", Query(), records)
