"""Outcome-blind V28 board generation and shared root-only observation prefix."""

from collections import Counter
import random
from time import perf_counter

from acfqp.domains.standard_2048 import (
    Swipe2048Status, legal_actions_v1, state_from_board_v1,
)
from .controlled_predictive_sampling_v15 import BatchRowSampleProvider
from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


PREFIX_BATCHES = 32
SAMPLES_PER_BATCH = 256


def _key(value):
    return value[0], tuple(value[1])


def _json_key(value):
    return [value[0], list(value[1])]


def generate_board(seed):
    """Draw one fixed dense board, then inject the two declared merge pairs."""
    rng = random.Random(seed)
    board = []
    for cell in range(16):
        excluded = set()
        if cell % 4:
            excluded.add(board[cell - 1])
        if cell >= 4:
            excluded.add(board[cell - 4])
        board.append(rng.choice([rank for rank in range(1, 11) if rank not in excluded]))
    board[0] = board[1] = rng.randint(1, 10)
    board[10] = board[14] = rng.randint(1, 10)
    return tuple(board)


def acquire_common_prefix(root, seed):
    """Physically acquire 32 root batches, independent of queries and values."""
    started = perf_counter()
    root = _key(root)
    state = state_from_board_v1(root[1])
    if root[0] != 2 or state.status is not Swipe2048Status.ACTIVE:
        raise ValueError("The common prefix requires an ACTIVE H2 root")
    actions = tuple(sorted(action.value for action in legal_actions_v1(root[1])))
    provider = BatchRowSampleProvider(seed)
    batches, records = Counter(), []
    for index in range(PREFIX_BATCHES):
        action = actions[index % len(actions)]
        batch_index = batches[action]
        sampled = provider.sample_batch(root, action, batch_index)
        records.append({"row_key": [_json_key(root), action], "batch_index": batch_index,
            "kind": "FIRST_OBSERVATION" if batch_index == 0 else "REPEAT_OBSERVATION",
            "outcomes": [[probability, _json_key(successor), reward]
                         for probability, successor, reward in sampled]})
        batches[action] += 1
    return records, {
        "whole_seconds": perf_counter() - started,
        "provider_seconds": provider.provider_seconds, "provider_counts": dict(provider.work_counts),
        "physical_batches": len(records), "physical_draws": len(records) * SAMPLES_PER_BATCH,
        "root_legal_actions": list(actions), "root_action_batch_counts": dict(batches),
        "planner_constructions": 0, "query_solves": 0,
        "scope": "One physical root-only prefix per board; provider time is included in whole_seconds. Every query reuses these paid observations.",
    }


def prepare_query(root, name, query, records):
    """Replay the retained prefix into one query's caches without sampling."""
    started = perf_counter()
    root = _key(root)
    if len(records) != PREFIX_BATCHES:
        raise ValueError("The retained prefix must contain exactly 32 batches")
    state = CachedGapPlannerState(root, {name: query})
    if root[0] != 2 or state.profiles[root].status != "ACTIVE":
        raise ValueError("Query preparation requires an ACTIVE H2 root")
    actions = state.profiles[root].legal_actions
    for index, record in enumerate(records):
        pair = _key(record["row_key"][0]), record["row_key"][1]
        expected = root, actions[index % len(actions)]
        batch_index = state.batch_counts.get(pair, 0)
        kind = "FIRST_OBSERVATION" if batch_index == 0 else "REPEAT_OBSERVATION"
        if pair != expected or record["batch_index"] != batch_index or record["kind"] != kind:
            raise ValueError("Retained prefix order, batch index or observation kind differs")
        batch = tuple((probability, _key(successor), reward)
                      for probability, successor, reward in record["outcomes"])
        state.observe_batch(*pair, batch)
    state.solve(name)
    state._gap_scores(name)
    whole_seconds = perf_counter() - started
    state.engine_seconds = whole_seconds
    return state, {
        "whole_seconds": whole_seconds, "work_counts": dict(state.work_counts),
        "replayed_batches": len(records), "retained_model_batches": state.spent_batches,
        "current_query": name, "prepared_query_count": 1,
        "new_provider_calls": 0, "new_physical_draws": 0,
        "scope": "One query's constructor, prefix replay and initial solve/gap-cache preparation, charged once in whole_seconds; historical prefix acquisition is separate.",
    }
