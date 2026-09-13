"""Query-independent executable board rules learned from empirical kernels.

A small regression tree for each horizon/status/legal-action group predicts
per-action rewards and distributions of recursively encoded successors. The
runtime encoder contains tree splits only; board and state maps exist only
transiently while fitting or compiling a covered empirical model.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from time import perf_counter
from typing import Any

from acfqp.domains.standard_2048 import (
    GOAL_RANK, Swipe2048Action, swipe_board_v1, validate_board_v1,
)
from acfqp.science.controlled_predictive_quotient_v1 import (
    Cell, CompiledModel, FiniteModel, _actions, _compile_rows,
)

ACTIONS = tuple(sorted(action.value for action in Swipe2048Action))
FEATURE_NAMES = (
    "empty_count", "maximum_rank", "rank_1_count", "rank_2_count", "rank_10_count",
    "horizontal_equal_nonzero_pairs", "vertical_equal_nonzero_pairs",
) + tuple(f"{action.lower()}_{name}" for action in ACTIONS for name in (
    "merge_reward", "post_empty_count", "post_horizontal_equal_nonzero_pairs",
    "post_vertical_equal_nonzero_pairs", "post_empty_adjacent_rank_1_count",
    "post_empty_adjacent_rank_2_count",
))
Group = tuple[int, str, tuple[str, ...]]
Code = tuple[int, str, tuple[str, ...], int]


@dataclass(frozen=True)
class TrainingModel:
    name: str
    empirical: FiniteModel
    boards: dict[int, tuple[int, ...]]


@dataclass(frozen=True)
class EncoderFit:
    encoder: RuleEncoder
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class EncodingBuild:
    compiled: CompiledModel
    code_to_cell: dict[Code, int]
    diagnostics: dict[str, Any]


def _pairs(board: tuple[int, ...]) -> tuple[int, int]:
    horizontal = sum(board[i] != 0 and board[i] == board[i + 1]
                     for i in range(16) if i % 4 < 3)
    vertical = sum(board[i] != 0 and board[i] == board[i + 4] for i in range(12))
    return horizontal, vertical


def _empty_adjacent(board: tuple[int, ...], rank: int) -> int:
    count = 0
    for i, value in enumerate(board):
        if value:
            continue
        neighbours = []
        if i % 4:
            neighbours.append(i - 1)
        if i % 4 < 3:
            neighbours.append(i + 1)
        if i >= 4:
            neighbours.append(i - 4)
        if i < 12:
            neighbours.append(i + 4)
        count += any(board[j] == rank for j in neighbours)
    return count


def _profile(board: tuple[int, ...], horizon: int, work: Counter) -> tuple[Group, tuple[float, ...]]:
    validate_board_v1(board)
    if type(horizon) is not int or horizon < 0:
        raise ValueError("remaining horizon must be a nonnegative integer")
    horizontal, vertical = _pairs(board)
    features = [board.count(0), max(board), board.count(1), board.count(2),
                board.count(10), horizontal, vertical]
    legal = []
    for action in ACTIONS:
        after, reward, changed = swipe_board_v1(board, Swipe2048Action(action))
        if changed:
            legal.append(action)
        h_pairs, v_pairs = _pairs(after)
        features.extend((reward / 2048.0, after.count(0), h_pairs, v_pairs,
                         _empty_adjacent(after, 1), _empty_adjacent(after, 2)))
    status = ("WON" if max(board) >= GOAL_RANK else "LOST" if not legal
              else "CUTOFF" if horizon == 0 else "ACTIVE")
    group = (horizon, status, tuple(legal) if status == "ACTIVE" else ())
    work.update(feature_extractions=1, deterministic_swipe_calls=4,
                feature_values_computed=len(features), adjacent_pair_tests=120)
    return group, tuple(float(value) for value in features)


def board_features(board: tuple[int, ...]) -> tuple[float, ...]:
    """The fixed 31 structural features; no stochastic successor enumeration."""
    return _profile(board, 1, Counter())[1]


def _leaf(tree: dict[str, Any], features: tuple[float, ...], work: Counter) -> int:
    while "leaf" not in tree:
        work["tree_split_nodes_visited"] += 1
        tree = tree["left"] if features[tree["feature"]] <= tree["threshold"] else tree["right"]
    work["tree_leaves_visited"] += 1
    return tree["leaf"]


@dataclass(frozen=True)
class RuleEncoder:
    trees: dict[Group, dict[str, Any]]

    def _encode_profile(self, group: Group, features: tuple[float, ...], work: Counter) -> Code:
        if group[1] != "ACTIVE":
            return (*group, 0)
        tree = self.trees.get(group)
        if tree is None:
            work["unseen_active_group_fallbacks"] += 1
            return (*group, -1)
        return (*group, _leaf(tree, features, work))

    def encode(self, board: tuple[int, ...], remaining_horizon: int) -> Code:
        work = Counter()
        group, features = _profile(board, remaining_horizon, work)
        return self._encode_profile(group, features, work)

    def to_payload(self) -> dict[str, Any]:
        # Trees contain JSON-native scalars/lists/dicts, never sample records.
        return {
            "schema": "controlled_predictive_rule_encoder_v7",
            "feature_names": list(FEATURE_NAMES),
            "trees": [{"horizon": group[0], "status": group[1], "legal": list(group[2]),
                       "tree": tree} for group, tree in sorted(self.trees.items())],
            "unseen_active_group_leaf": -1,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RuleEncoder:
        if (payload["schema"] != "controlled_predictive_rule_encoder_v7"
                or tuple(payload["feature_names"]) != FEATURE_NAMES):
            raise ValueError("encoder schema or fixed feature family differs")
        return cls({(row["horizon"], row["status"], tuple(row["legal"])): row["tree"]
                    for row in payload["trees"]})


def _fit_tree(features: list[tuple[float, ...]], targets: list[dict[tuple, float]],
              max_depth: int, min_leaf: int, work: Counter) -> tuple[dict[str, Any], dict[str, Any]]:
    next_leaf = 0
    leaf_losses: list[float] = []
    split_features: Counter = Counter()

    def fit(indices: list[int], depth: int) -> dict[str, Any]:
        nonlocal next_leaf
        totals: dict[tuple, float] = defaultdict(float)
        square_sum = 0.0
        for index in indices:
            for coordinate, value in targets[index].items():
                totals[coordinate] += value
                square_sum += value * value
                work["node_target_coordinate_reads"] += 1
        total_norm = math.fsum(value * value for value in totals.values())
        loss = max(0.0, square_sum - total_norm / len(indices))
        best_gain = 0.0
        best = None
        if depth < max_depth and len(indices) >= 2 * min_leaf and loss > 1e-12:
            for feature in range(len(FEATURE_NAMES)):
                ordered = sorted(indices, key=lambda index: features[index][feature])
                work["feature_sort_items"] += len(ordered)
                left: dict[tuple, float] = defaultdict(float)
                right = dict(totals)
                left_norm, right_norm = 0.0, total_norm
                for position, index in enumerate(ordered[:-1], 1):
                    for coordinate, value in targets[index].items():
                        before_left = left[coordinate]
                        before_right = right[coordinate]
                        left_norm += 2 * before_left * value + value * value
                        right_norm += -2 * before_right * value + value * value
                        left[coordinate] = before_left + value
                        right[coordinate] = before_right - value
                        work["split_target_coordinate_updates"] += 1
                    if (position < min_leaf or len(ordered) - position < min_leaf
                            or features[index][feature] == features[ordered[position]][feature]):
                        continue
                    work["candidate_thresholds_evaluated"] += 1
                    gain = (left_norm / position + right_norm / (len(ordered) - position)
                            - total_norm / len(ordered))
                    if gain > 1e-12 and (best is None or gain > best_gain + 1e-12):
                        best_gain = gain
                        threshold = (features[index][feature] + features[ordered[position]][feature]) / 2
                        best = (feature, threshold, ordered[:position], ordered[position:])
        if best is None:
            result = {"leaf": next_leaf}
            next_leaf += 1
            leaf_losses.append(loss)
            work["tree_leaves_fitted"] += 1
            return result
        feature, threshold, left_indices, right_indices = best
        split_features[FEATURE_NAMES[feature]] += 1
        work["tree_split_nodes_fitted"] += 1
        return {"feature": feature, "threshold": threshold,
                "left": fit(left_indices, depth + 1), "right": fit(right_indices, depth + 1)}

    tree = fit(list(range(len(features))), 0)
    dimension = len({coordinate for target in targets for coordinate in target})
    return tree, {"training_examples": len(features), "target_dimension": dimension,
                  "target_squared_error": math.fsum(leaf_losses), "leaves": next_leaf,
                  "split_features": dict(split_features)}


def fit_encoder(training: list[TrainingModel] | tuple[TrainingModel, ...], *,
                max_depth: int = 4, min_leaf: int = 2) -> EncoderFit:
    """Fit bottom-up from only the supplied empirical transitions and boards."""
    if not training or max_depth < 0 or min_leaf < 1:
        raise ValueError("training must be nonempty with valid tree limits")
    started = perf_counter()
    work: Counter = Counter()
    profiles: dict[tuple[int, int], tuple[Group, tuple[float, ...]]] = {}
    groups: dict[Group, list[tuple[int, int]]] = defaultdict(list)
    unique_board_layers = set()
    profile_started = perf_counter()
    for model_index, item in enumerate(training):
        actions = _actions(item.empirical)
        for state in sorted(item.empirical.layers):
            horizon = item.empirical.layers[state]
            board = item.boards[state]
            group, features = _profile(board, horizon, work)
            if (group[1] != item.empirical.terminal[state]
                    or group[2] != actions.get(state, ())):
                raise ValueError("empirical state status/actions differ from executable board semantics")
            profiles[model_index, state] = (group, features)
            groups[group].append((model_index, state))
            unique_board_layers.add((horizon, board))
    profile_seconds = perf_counter() - profile_started
    trees = {}
    encoder = RuleEncoder(trees)
    codes: dict[tuple[int, int], Code] = {}
    diagnostics = []
    target_seconds = tree_seconds = 0.0
    for group, records in sorted(groups.items()):
        target_started = perf_counter()
        targets: list[dict[tuple, float]] = []
        features = [profiles[record][1] for record in records]
        if group[1] == "ACTIVE":
            for model_index, state in records:
                target: dict[tuple, float] = defaultdict(float)
                for action in group[2]:
                    row = training[model_index].empirical.rows[state, action]
                    work["training_action_rows_read"] += 1
                    for outcome in row:
                        work["training_successor_entries_read"] += 1
                        if outcome.probability:
                            target[action, "reward"] += outcome.probability * outcome.reward
                            target[action, "successor", codes[model_index, outcome.next_state]] += outcome.probability
                targets.append(dict(target))
        target_seconds += perf_counter() - target_started
        tree_started = perf_counter()
        if group[1] == "ACTIVE":
            tree, report = _fit_tree(features, targets, max_depth, min_leaf, work)
        else:
            tree = {"leaf": 0}
            report = {"training_examples": len(records), "target_dimension": 0,
                      "target_squared_error": 0.0, "leaves": 1, "split_features": {}}
            work["terminal_groups_constant"] += 1
        trees[group] = tree
        tree_seconds += perf_counter() - tree_started
        for record in records:
            codes[record] = encoder._encode_profile(group, profiles[record][1], work)
        diagnostics.append({"horizon": group[0], "status": group[1], "legal": list(group[2]), **report})
    active_reports = [row for row in diagnostics if row["status"] == "ACTIVE"]
    return EncoderFit(encoder, {
        "training_models": [item.name for item in training],
        "training_state_records": len(profiles), "unique_training_board_horizon_pairs": len(unique_board_layers),
        "training_active_state_records": sum(row["training_examples"] for row in active_reports),
        "max_depth": max_depth, "min_leaf": min_leaf, "minimum_split_gain": 1e-12,
        "feature_names": list(FEATURE_NAMES), "groups": diagnostics,
        "active_tree_count": len(active_reports), "active_leaf_count": sum(row["leaves"] for row in active_reports),
        "training_target_squared_error": math.fsum(row["target_squared_error"] for row in active_reports),
        "training_target_dimension_sum": sum(row["target_dimension"] for row in active_reports),
        "work_counts": dict(work), "feature_seconds": profile_seconds, "target_seconds": target_seconds,
        "tree_fit_seconds": tree_seconds, "fit_seconds": perf_counter() - started,
    })


def compile_encoded(empirical: FiniteModel, boards: dict[int, tuple[int, ...]],
                    encoder: RuleEncoder) -> EncodingBuild:
    """Pool covered empirical rows by frozen rules, without refitting the rules."""
    started = perf_counter()
    work: Counter = Counter()
    groups: dict[Code, list[int]] = defaultdict(list)
    unseen: Counter = Counter()
    actions = _actions(empirical)
    for state in sorted(empirical.layers):
        group, features = _profile(boards[state], empirical.layers[state], work)
        if group[1] != empirical.terminal[state] or group[2] != actions.get(state, ()):
            raise ValueError("empirical state status/actions differ from executable board semantics")
        code = encoder._encode_profile(group, features, work)
        groups[code].append(state)
        if group not in encoder.trees:
            unseen[group] += 1
    encoding_seconds = perf_counter() - started
    mapping = {}
    cells = {}
    code_to_cell = {}
    for cell, (code, members) in enumerate(sorted(groups.items())):
        cells[cell] = Cell(code[0], code[1], tuple(members))
        code_to_cell[code] = cell
        for state in members:
            mapping[state] = cell
    pooling_started = perf_counter()
    rows = _compile_rows(empirical, cells, mapping)
    work["pooling_action_rows_read"] = len(empirical.rows)
    work["pooling_successor_entries_read"] = sum(len(row) for row in empirical.rows.values())
    compiled = CompiledModel(cells, rows, tuple(mapping[root] for root in empirical.roots), mapping, {})
    return EncodingBuild(compiled, code_to_cell, {
        "states_encoded": len(mapping), "active_states_encoded": sum(s == "ACTIVE" for s in empirical.terminal.values()),
        "cells": len(cells), "active_cells": sum(cell.terminal == "ACTIVE" for cell in cells.values()),
        "unseen_group_states": sum(unseen.values()),
        "unseen_active_group_states": work["unseen_active_group_fallbacks"],
        "unseen_groups": [{"horizon": group[0], "status": group[1], "legal": list(group[2]), "states": count}
                          for group, count in sorted(unseen.items())],
        "work_counts": dict(work), "encoding_seconds": encoding_seconds,
        "pooling_seconds": perf_counter() - pooling_started, "build_seconds": perf_counter() - started,
        "pooling_rule": "uniform member mean; every member empirical row has the same sample count",
        "cell_diameters": "not measured",
    })
