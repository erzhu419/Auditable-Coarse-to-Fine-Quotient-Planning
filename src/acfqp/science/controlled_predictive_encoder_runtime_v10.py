"""Demand-driven board features cached only for one finite-model build.

The rule payload, 31 feature values, legal-action groups and terminal semantics
are unchanged. Cached boards and deterministic swipe results are construction
scratch data; they are never part of the executable rule artifact.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from time import perf_counter
from typing import Any

from acfqp.domains.standard_2048 import GOAL_RANK, Swipe2048Action, swipe_board_v1, validate_board_v1
from .controlled_predictive_encoder_runtime_v8 import _pool_rows
from .controlled_predictive_encoder_v7 import (
    ACTIONS, FEATURE_NAMES, Code, EncodingBuild, Group, RuleEncoder, _empty_adjacent, _pairs,
)
from .controlled_predictive_quotient_v1 import Cell, CompiledModel, FiniteModel, _actions

_ACTION_ENUMS = tuple(Swipe2048Action(action) for action in ACTIONS)


class _BoardEntry:
    def __init__(self, board: tuple[int, ...], work: Counter):
        validate_board_v1(board)
        work["board_cache_entry_validations"] += 1
        work["board_validations"] += 1
        self.board = board
        self.work = work
        self.maximum = max(board)
        work["board_maximum_scans"] += 1
        self.status = "WON" if self.maximum >= GOAL_RANK else None
        self.legal: tuple[str, ...] | None = None
        self.swipes: dict[int, tuple[tuple[int, ...], int, bool]] = {}
        self.features: dict[int, float] = {}
        self.pairs: dict[int, tuple[int, int]] = {}

    def swipe(self, action_index: int) -> tuple[tuple[int, ...], int, bool]:
        self.work["swipe_requests"] += 1
        if action_index in self.swipes:
            self.work["swipe_cache_hits"] += 1
            return self.swipes[action_index]
        self.work["deterministic_swipe_calls"] += 1
        self.work["swipe_internal_board_validations"] += 1
        self.work["board_validations"] += 1
        result = swipe_board_v1(self.board, _ACTION_ENUMS[action_index])
        self.swipes[action_index] = result
        return result

    def equal_pairs(self, key: int, board: tuple[int, ...]) -> tuple[int, int]:
        if key in self.pairs:
            self.work["adjacent_pair_cache_hits"] += 1
            return self.pairs[key]
        result = _pairs(board)
        self.pairs[key] = result
        self.work["adjacent_pair_pair_computations"] += 1
        self.work["adjacent_pair_tests"] += 24
        return result

    def value(self, index: int) -> float:
        self.work["feature_value_requests"] += 1
        if index in self.features:
            self.work["feature_value_cache_hits"] += 1
            return self.features[index]
        if not self.features:
            self.work["board_entries_with_requested_features"] += 1
        if index == 1:
            value = self.maximum
        elif index in (0, 2, 3, 4):
            rank = {0: 0, 2: 1, 3: 2, 4: 10}[index]
            value = self.board.count(rank)
            self.work["board_rank_count_scans"] += 1
        elif index in (5, 6):
            value = self.equal_pairs(-1, self.board)[index - 5]
        else:
            action_index, kind = divmod(index - 7, 6)
            after, reward, _ = self.swipe(action_index)
            if kind == 0:
                value = reward / 2048.0
            elif kind == 1:
                value = after.count(0)
                self.work["post_swipe_empty_count_scans"] += 1
            elif kind in (2, 3):
                value = self.equal_pairs(action_index, after)[kind - 2]
            else:
                value = _empty_adjacent(after, kind - 3)
                self.work["post_swipe_empty_adjacency_feature_calls"] += 1
        value = float(value)
        self.features[index] = value
        self.work["feature_values_computed"] += 1
        if len(self.features) == len(FEATURE_NAMES):
            self.work["fully_materialized_board_feature_vectors"] += 1
        return value


class LazyFeatures(Sequence[float]):
    """Index access computes one scalar; tuple(sequence) requests all 31."""
    def __init__(self, entry: _BoardEntry):
        self._entry = entry

    def __len__(self) -> int:
        return len(FEATURE_NAMES)

    def __getitem__(self, index: int | slice) -> float | tuple[float, ...]:
        if isinstance(index, slice):
            return tuple(self[i] for i in range(*index.indices(len(self))))
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return self._entry.value(index)


class FeatureCache:
    """Own deterministic board computations for a single caller-controlled build."""
    def __init__(self, work: Counter):
        self.work = work
        self._entries: dict[tuple[int, ...], _BoardEntry] = {}

    def profile(self, board: tuple[int, ...], remaining_horizon: int) -> tuple[Group, Sequence[float]]:
        if type(remaining_horizon) is not int or remaining_horizon < 0:
            raise ValueError("remaining horizon must be a nonnegative integer")
        # Supported inputs are rank tuples; validation happens once per stored
        # board, before any status, feature, or swipe is computed for that board.
        if type(board) is not tuple:
            validate_board_v1(board)
        self.work["states_profiled"] += 1
        self.work["board_cache_requests"] += 1
        if board in self._entries:
            self.work["board_cache_hits"] += 1
            entry = self._entries[board]
        else:
            self.work["board_cache_misses"] += 1
            entry = _BoardEntry(board, self.work)
            self._entries[board] = entry
            self.work["board_cache_entries"] = len(self._entries)
        if entry.status == "WON":
            self.work["terminal_feature_vectors_skipped"] += 1
            return (remaining_horizon, "WON", ()), ()
        if entry.status == "LOST":
            self.work["terminal_feature_vectors_skipped"] += 1
            return (remaining_horizon, "LOST", ()), ()
        if remaining_horizon == 0:
            if entry.status is None:
                for action_index in range(len(ACTIONS)):
                    if entry.swipe(action_index)[2]:
                        entry.status = "ACTIVE"
                        break
                else:
                    entry.status = "LOST"
            self.work["terminal_feature_vectors_skipped"] += 1
            return (0, "CUTOFF" if entry.status == "ACTIVE" else "LOST", ()), ()
        if entry.legal is None:
            entry.legal = tuple(action for index, action in enumerate(ACTIONS) if entry.swipe(index)[2])
            entry.status = "ACTIVE" if entry.legal else "LOST"
        if entry.status == "LOST":
            self.work["terminal_feature_vectors_skipped"] += 1
            return (remaining_horizon, "LOST", ()), ()
        self.work["active_feature_sequences_issued"] += 1
        return (remaining_horizon, "ACTIVE", entry.legal), LazyFeatures(entry)

    def encode(self, encoder: RuleEncoder, board: tuple[int, ...], remaining_horizon: int) -> Code:
        group, features = self.profile(board, remaining_horizon)
        return encoder._encode_profile(group, features, self.work)

    def diagnostics(self) -> dict[str, Any]:
        return {
            "board_entries": len(self._entries),
            "board_entries_with_requested_features": sum(bool(entry.features) for entry in self._entries.values()),
            "scalar_feature_values_cached": sum(len(entry.features) for entry in self._entries.values()),
            "deterministic_swipe_results_cached": sum(len(entry.swipes) for entry in self._entries.values()),
            "fully_materialized_board_feature_vectors": sum(len(entry.features) == len(FEATURE_NAMES) for entry in self._entries.values()),
            "work_counts": dict(self.work),
            "scope": "One build only; no shared cache across arms, cases, seeds or source fits.",
        }


class RuntimeEncoder(RuleEncoder):
    """Execute the unchanged artifact with an ephemeral demand-driven cache."""
    def encode(self, board: tuple[int, ...], remaining_horizon: int) -> Code:
        return FeatureCache(Counter()).encode(self, board, remaining_horizon)


def compile_encoded(empirical: FiniteModel, boards: dict[int, tuple[int, ...]],
                    encoder: RuleEncoder) -> EncodingBuild:
    """Encode with a fresh build cache and pool every current row once."""
    started = perf_counter()
    work: Counter = Counter()
    cache = FeatureCache(work)
    groups: dict[Code, list[int]] = defaultdict(list)
    unseen: Counter = Counter()
    actions = _actions(empirical)
    work["legal_action_rows_indexed"] = len(empirical.rows)
    for state in sorted(empirical.layers):
        group, features = cache.profile(boards[state], empirical.layers[state])
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
    cache_diagnostics = cache.diagnostics()
    return EncodingBuild(compiled, code_to_cell, {
        "states_encoded": len(mapping), "active_states_encoded": sum(status == "ACTIVE" for status in empirical.terminal.values()),
        "cells": len(cells), "active_cells": sum(cell.terminal == "ACTIVE" for cell in cells.values()),
        "unseen_group_states": sum(unseen.values()),
        "unseen_active_group_states": sum(count for group, count in unseen.items() if group[1] == "ACTIVE"),
        "unseen_groups": [{"horizon": group[0], "status": group[1], "legal": list(group[2]), "states": count}
                          for group, count in sorted(unseen.items())],
        "work_counts": dict(work), "cache": cache_diagnostics,
        "encoding_seconds": encoding_seconds, "grouping_seconds": grouping_seconds,
        "pooling_seconds": pooling_seconds, "build_seconds": perf_counter() - started,
        "pooling_rule": "uniform member mean; every member empirical row has the same sample count",
        "cell_diameters": "not measured", "runtime_profile": "v10_demand_driven_build_local_cache",
    })
