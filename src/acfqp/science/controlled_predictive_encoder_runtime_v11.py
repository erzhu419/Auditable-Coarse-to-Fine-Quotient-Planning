"""Execute unchanged rules using five demand-driven feature blocks per state.

Terminal profiling uses the V8 short circuit. Each ACTIVE state owns its four
deterministic swipe results and five optional tuples; nothing is cached by board
or shared between states, horizons, builds, or runtime queries.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from time import perf_counter
from typing import Any

from acfqp.domains.standard_2048 import GOAL_RANK, Swipe2048Action, swipe_board_v1, validate_board_v1
from .controlled_predictive_encoder_v7 import (
    ACTIONS, FEATURE_NAMES, Code, EncodingBuild, Group, RuleEncoder, _empty_adjacent, _pairs,
)
from .controlled_predictive_encoder_runtime_v8 import _pool_rows
from .controlled_predictive_quotient_v1 import Cell, CompiledModel, FiniteModel, _actions


_ACTION_ENUMS = tuple((name, Swipe2048Action(name)) for name in ACTIONS)


class BlockFeatures(Sequence[float]):
    """Cache the global seven features and each action's six as five tuples."""

    def __init__(self, board: tuple[int, ...], maximum: int,
                 swipes: tuple[tuple[tuple[int, ...], int], ...], work: Counter):
        self.board = board
        self.maximum = maximum
        self.swipes = swipes
        self.work = work
        self._blocks: list[tuple[float, ...] | None] = [None] * 5
        self._computed_blocks = 0
        self._full: tuple[float, ...] | None = None
        work.update(active_feature_contexts_created=1, aggregate_swipe_results_stored=4)

    def __len__(self) -> int:
        return len(FEATURE_NAMES)

    def _block(self, block: int) -> tuple[float, ...]:
        self.work["feature_block_requests"] += 1
        cached = self._blocks[block]
        if cached is not None:
            self.work["feature_block_cache_hits"] += 1
            return cached
        if block == 0:
            horizontal, vertical = _pairs(self.board)
            result = tuple(float(value) for value in (
                self.board.count(0), self.maximum, self.board.count(1),
                self.board.count(2), self.board.count(10), horizontal, vertical,
            ))
            self.work.update(global_feature_blocks_computed=1, board_rank_count_scans=4,
                             adjacent_pair_tests=24, feature_values_computed=7)
        else:
            after, reward = self.swipes[block - 1]
            horizontal, vertical = _pairs(after)
            result = tuple(float(value) for value in (
                reward / 2048.0, after.count(0), horizontal, vertical,
                _empty_adjacent(after, 1), _empty_adjacent(after, 2),
            ))
            self.work.update(action_feature_blocks_computed=1, post_swipe_empty_count_scans=1,
                             adjacent_pair_tests=24, post_swipe_empty_adjacency_feature_calls=2,
                             feature_values_computed=6)
        self._blocks[block] = result
        self._computed_blocks += 1
        self.work["feature_blocks_computed"] += 1
        if self._computed_blocks == 5:
            self.work["fully_materialized_state_feature_vectors"] += 1
        return result

    def __getitem__(self, index: int | slice) -> float | tuple[float, ...]:
        if isinstance(index, slice):
            return tuple(self[i] for i in range(*index.indices(len(self))))
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        self.work["feature_value_requests"] += 1
        if index < 7:
            return self._block(0)[index]
        block, offset = divmod(index - 7, 6)
        return self._block(block + 1)[offset]

    def materialize(self) -> tuple[float, ...]:
        """Batch missing blocks without dispatching 31 scalar index requests."""
        self.work["feature_materialization_calls"] += 1
        if self._full is not None:
            self.work["feature_materialization_cache_hits"] += 1
            return self._full
        values = []
        for index, cached in enumerate(self._blocks):
            values.extend(self._block(index) if cached is None else cached)
        self._full = tuple(values)
        return self._full


def profile(board: tuple[int, ...], remaining_horizon: int,
            work: Counter) -> tuple[Group, BlockFeatures | tuple[()]]:
    """Preserve V8 status/action semantics and create contexts only for ACTIVE."""
    validate_board_v1(board)
    if type(remaining_horizon) is not int or remaining_horizon < 0:
        raise ValueError("remaining horizon must be a nonnegative integer")
    maximum = max(board)
    work.update(states_profiled=1, profile_board_validations=1,
                board_validations=1, board_maximum_scans=1)
    if maximum >= GOAL_RANK:
        work["terminal_feature_vectors_skipped"] += 1
        return (remaining_horizon, "WON", ()), ()

    legal = []
    swipes = []
    for name, action in _ACTION_ENUMS:
        after, reward, changed = swipe_board_v1(board, action)
        swipes.append((after, reward))
        if changed:
            if remaining_horizon == 0:
                calls = len(swipes)
                work.update(deterministic_swipe_calls=calls, swipe_internal_board_validations=calls,
                            board_validations=calls, terminal_feature_vectors_skipped=1)
                return (0, "CUTOFF", ()), ()
            legal.append(name)
    work.update(deterministic_swipe_calls=4, swipe_internal_board_validations=4, board_validations=4)
    if not legal:
        work["terminal_feature_vectors_skipped"] += 1
        return (remaining_horizon, "LOST", ()), ()
    return (remaining_horizon, "ACTIVE", tuple(legal)), BlockFeatures(board, maximum, tuple(swipes), work)


def feature_work_summary(work: Counter) -> dict[str, Any]:
    """Cumulative work counts; these are not peak or currently retained memory."""
    return {
        "active_feature_contexts_created": work["active_feature_contexts_created"],
        "terminal_feature_contexts_created": 0,
        "feature_blocks_computed": work["feature_blocks_computed"],
        "scalar_feature_values_computed": work["feature_values_computed"],
        "aggregate_swipe_results_stored": work["aggregate_swipe_results_stored"],
        "fully_materialized_state_feature_vectors": work["fully_materialized_state_feature_vectors"],
        "context_scope": "Independent per ACTIVE state; cumulative counts, not peak/current retention. No board-keyed cache.",
    }


class RuntimeEncoder(RuleEncoder):
    """Execute the unchanged portable payload using ephemeral state contexts."""

    def encode(self, board: tuple[int, ...], remaining_horizon: int) -> Code:
        work: Counter = Counter()
        group, features = profile(board, remaining_horizon, work)
        return self._encode_profile(group, features, work)


def compile_encoded(empirical: FiniteModel, boards: dict[int, tuple[int, ...]],
                    encoder: RuleEncoder) -> EncodingBuild:
    """Profile each state independently and pool the unchanged code partition."""
    started = perf_counter()
    work: Counter = Counter()
    groups: dict[Code, list[int]] = defaultdict(list)
    unseen: Counter = Counter()
    actions = _actions(empirical)
    work["legal_action_rows_indexed"] = len(empirical.rows)
    for state in sorted(empirical.layers):
        group, features = profile(boards[state], empirical.layers[state], work)
        if group[1] != empirical.terminal[state] or group[2] != actions.get(state, ()):
            raise ValueError("empirical state status/actions differ from executable board semantics")
        code = encoder._encode_profile(group, features, work)
        groups[code].append(state)
        if group not in encoder.trees:
            unseen[group] += 1
    encoding_seconds = perf_counter() - started
    grouping_started = perf_counter()
    mapping, cells, code_to_cell = {}, {}, {}
    for cell, (code, members) in enumerate(sorted(groups.items())):
        cells[cell] = Cell(code[0], code[1], tuple(members))
        code_to_cell[code] = cell
        for state in members:
            mapping[state] = cell
    grouping_seconds = perf_counter() - grouping_started
    pooling_started = perf_counter()
    rows = _pool_rows(empirical, cells, mapping, actions, work)
    pooling_seconds = perf_counter() - pooling_started
    compiled = CompiledModel(cells, rows, tuple(mapping[root] for root in empirical.roots), mapping, {})
    summary = feature_work_summary(work)
    return EncodingBuild(compiled, code_to_cell, {
        "states_encoded": len(mapping), "active_states_encoded": sum(s == "ACTIVE" for s in empirical.terminal.values()),
        "cells": len(cells), "active_cells": sum(cell.terminal == "ACTIVE" for cell in cells.values()),
        "unseen_group_states": sum(unseen.values()),
        "unseen_active_group_states": work["unseen_active_group_fallbacks"],
        "unseen_groups": [{"horizon": group[0], "status": group[1], "legal": list(group[2]), "states": count}
                          for group, count in sorted(unseen.items())],
        "feature_work_summary": summary, "work_counts": dict(work),
        "encoding_seconds": encoding_seconds, "grouping_seconds": grouping_seconds,
        "pooling_seconds": pooling_seconds, "build_seconds": perf_counter() - started,
        "pooling_rule": "uniform member mean; every member empirical row has the same sample count",
        "cell_diameters": "not measured", "runtime_profile": "v11_per_state_five_feature_blocks",
    })
