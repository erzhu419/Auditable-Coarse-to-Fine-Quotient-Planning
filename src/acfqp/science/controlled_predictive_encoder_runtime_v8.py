"""V7-equivalent executable rules with terminal-aware feature extraction.

The encoder uses the existing rule payload and the same 31 ACTIVE features.
Terminal codes require only status and horizon, so their unused feature vectors
are omitted. Compiling reuses the action index for empirical row pooling.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from time import perf_counter

from acfqp.domains.standard_2048 import GOAL_RANK, Swipe2048Action, swipe_board_v1, validate_board_v1
from .controlled_predictive_encoder_v7 import (
    ACTIONS, FEATURE_NAMES, Code, EncodingBuild, Group, RuleEncoder, _empty_adjacent, _pairs,
)
from .controlled_predictive_quotient_v1 import Cell, CompiledModel, FiniteModel, Outcome, _actions


_ACTION_ENUMS = tuple((name, Swipe2048Action(name)) for name in ACTIONS)


def profile(board: tuple[int, ...], remaining_horizon: int, work: Counter) -> tuple[Group, tuple[float, ...]]:
    """Return unchanged ACTIVE features and feature-free terminal groups."""
    validate_board_v1(board)
    if type(remaining_horizon) is not int or remaining_horizon < 0:
        raise ValueError("remaining horizon must be a nonnegative integer")
    work["states_profiled"] += 1
    maximum = max(board)
    work["board_maximum_scans"] += 1
    if maximum >= GOAL_RANK:
        work["terminal_feature_vectors_skipped"] += 1
        return (remaining_horizon, "WON", ()), ()

    # A legal move establishes CUTOFF at h=0; LOST still takes precedence when
    # every action is unchanged. No terminal code contains a legal-action list.
    legal = []
    swipes = []
    for name, action in _ACTION_ENUMS:
        after, reward, changed = swipe_board_v1(board, action)
        work["deterministic_swipe_calls"] += 1
        if changed:
            if remaining_horizon == 0:
                work["terminal_feature_vectors_skipped"] += 1
                return (0, "CUTOFF", ()), ()
            legal.append(name)
        swipes.append((after, reward))
    if not legal:
        work["terminal_feature_vectors_skipped"] += 1
        return (remaining_horizon, "LOST", ()), ()

    horizontal, vertical = _pairs(board)
    features = [board.count(0), maximum, board.count(1), board.count(2),
                board.count(10), horizontal, vertical]
    for after, reward in swipes:
        h_pairs, v_pairs = _pairs(after)
        features.extend((reward / 2048.0, after.count(0), h_pairs, v_pairs,
                         _empty_adjacent(after, 1), _empty_adjacent(after, 2)))
    work.update(feature_extractions=1, feature_values_computed=len(FEATURE_NAMES),
                adjacent_pair_tests=120, post_swipe_empty_adjacency_feature_calls=8)
    return (remaining_horizon, "ACTIVE", tuple(legal)), tuple(float(value) for value in features)


class RuntimeEncoder(RuleEncoder):
    """Execute the unchanged rule trees using the terminal-aware profile."""

    def encode(self, board: tuple[int, ...], remaining_horizon: int) -> Code:
        work: Counter = Counter()
        group, features = profile(board, remaining_horizon, work)
        return self._encode_profile(group, features, work)


def _pool_rows(empirical: FiniteModel, cells: dict[int, Cell], mapping: dict[int, int],
               actions: dict[int, tuple[str, ...]], work: Counter) -> dict[tuple[int, str], tuple[Outcome, ...]]:
    """Keep V7 accumulation order while reusing the already built action index."""
    rows = {}
    for cell_id, cell in cells.items():
        if cell.terminal != "ACTIVE":
            continue
        for action in actions[cell.members[0]]:
            mass: dict[int, list[float]] = defaultdict(list)
            reward_mass: dict[int, list[float]] = defaultdict(list)
            for state in cell.members:
                row = empirical.rows[state, action]
                work["pooling_action_rows_read"] += 1
                work["pooling_successor_entries_read"] += len(row)
                for outcome in row:
                    if outcome.probability:
                        target = mapping[outcome.next_state]
                        mass[target].append(outcome.probability)
                        reward_mass[target].append(outcome.probability * outcome.reward)
            rows[cell_id, action] = tuple(
                Outcome(math.fsum(parts) / len(cell.members), target,
                        math.fsum(reward_mass[target]) / math.fsum(parts))
                for target, parts in sorted(mass.items())
            )
    return rows


def compile_encoded(empirical: FiniteModel, boards: dict[int, tuple[int, ...]],
                    encoder: RuleEncoder) -> EncodingBuild:
    """Pool the same code partition and empirical dynamics with reduced profiling."""
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
    mapping = {}
    cells = {}
    code_to_cell = {}
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
    return EncodingBuild(compiled, code_to_cell, {
        "states_encoded": len(mapping), "active_states_encoded": sum(s == "ACTIVE" for s in empirical.terminal.values()),
        "cells": len(cells), "active_cells": sum(cell.terminal == "ACTIVE" for cell in cells.values()),
        "unseen_group_states": sum(unseen.values()),
        "unseen_active_group_states": work["unseen_active_group_fallbacks"],
        "unseen_groups": [{"horizon": group[0], "status": group[1], "legal": list(group[2]), "states": count}
                          for group, count in sorted(unseen.items())],
        "work_counts": dict(work), "encoding_seconds": encoding_seconds,
        "grouping_seconds": grouping_seconds, "pooling_seconds": pooling_seconds,
        "build_seconds": perf_counter() - started,
        "pooling_rule": "uniform member mean; every member empirical row has the same sample count",
        "cell_diameters": "not measured",
        "runtime_profile": "v8_terminal_aware_v7_equivalent_active_features",
    })
