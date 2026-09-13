"""Exact empirical signature constraints for executable bottom-up board rules.

Training signatures contain per-action mean rewards and distributions over
already encoded successors. A signature constraint is a finite empirical
requirement, not a guarantee concerning the independently audited true kernel.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from time import perf_counter
from typing import Any

from .controlled_predictive_encoder_runtime_v8 import RuntimeEncoder, profile
from .controlled_predictive_encoder_v7 import (
    Code, EncoderFit, FEATURE_NAMES, Group, TrainingModel, _fit_tree, _leaf,
)
from .controlled_predictive_quotient_v1 import _actions

Signature = tuple[tuple[tuple, float], ...]


def _incompatible_pairs(counts: Counter) -> int:
    size = sum(counts.values())
    return (size * size - sum(count * count for count in counts.values())) // 2


def _constraint_tree(features: list[tuple[float, ...]], classes: list[int],
                     work: Counter) -> dict[str, Any]:
    """Split by exact integer counts of incompatible pairs separated."""
    next_leaf = 0

    def fit(indices: list[int]) -> dict[str, Any]:
        nonlocal next_leaf
        totals = Counter(classes[index] for index in indices)
        work["constraint_node_class_reads"] += len(indices)
        best_gain, best = 0, None
        if len(totals) > 1:
            for feature in range(len(FEATURE_NAMES)):
                ordered = sorted(indices, key=lambda index: features[index][feature])
                work["feature_sort_items"] += len(ordered)
                left: Counter = Counter()
                right = totals.copy()
                same_class_cross_pairs = 0
                for position, index in enumerate(ordered[:-1], 1):
                    label = classes[index]
                    same_class_cross_pairs += right[label] - left[label] - 1
                    left[label] += 1
                    right[label] -= 1
                    work["constraint_split_class_updates"] += 1
                    if features[index][feature] == features[ordered[position]][feature]:
                        continue
                    work["candidate_thresholds_evaluated"] += 1
                    separated = position * (len(ordered) - position) - same_class_cross_pairs
                    if separated > best_gain:
                        best_gain = separated
                        threshold = (features[index][feature] + features[ordered[position]][feature]) / 2
                        best = (feature, threshold, ordered[:position], ordered[position:])
        if best is None:
            result = {"leaf": next_leaf}
            next_leaf += 1
            work["tree_leaves_fitted"] += 1
            return result
        feature, threshold, left_indices, right_indices = best
        work["tree_split_nodes_fitted"] += 1
        work["constraint_incompatible_pairs_separated"] += best_gain
        return {"feature": feature, "threshold": threshold,
                "left": fit(left_indices), "right": fit(right_indices)}

    return fit(list(range(len(features))))


def _leaf_nodes(tree: dict[str, Any]):
    if "leaf" in tree:
        yield tree
    else:
        yield from _leaf_nodes(tree["left"])
        yield from _leaf_nodes(tree["right"])


def _envelopes(indices: list[int], targets: list[dict[tuple, float]],
               actions: tuple[str, ...], work: Counter) -> dict[str, Any]:
    """Exact within-leaf empirical ranges; no statistical tolerance is fitted."""
    result = {}
    for action in actions:
        rewards = [targets[index].get((action, "reward"), 0.0) for index in indices]
        masses = [{coordinate[2]: value for coordinate, value in targets[index].items()
                   if coordinate[:2] == (action, "successor")} for index in indices]
        worst_tv = 0.0
        for position, left in enumerate(masses):
            for right in masses[position + 1:]:
                coordinates = left.keys() | right.keys()
                tv = .5 * math.fsum(abs(left.get(code, 0.0) - right.get(code, 0.0))
                                     for code in coordinates)
                worst_tv = max(worst_tv, tv)
                work["constraint_audit_mass_pairs"] += 1
                work["constraint_audit_mass_coordinates"] += len(coordinates)
        result[action] = {"minimum_mean_reward": min(rewards), "maximum_mean_reward": max(rewards),
                          "reward_range": max(rewards) - min(rewards), "maximum_successor_tv": worst_tv}
    return result


def _normalize_and_audit(tree: dict[str, Any], features: list[tuple[float, ...]],
                         targets: list[dict[tuple, float]], signatures: list[Signature],
                         classes: list[int], records: list[tuple[int, int]],
                         training: tuple[TrainingModel, ...], actions: tuple[str, ...],
                         work: Counter) -> dict[str, Any]:
    """Share pure-signature codes and retain mixed leaves as distinct outputs."""
    by_leaf: dict[int, list[int]] = defaultdict(list)
    by_features: dict[tuple[float, ...], list[int]] = defaultdict(list)
    for index, feature_values in enumerate(features):
        by_leaf[_leaf(tree, feature_values, work)].append(index)
        by_features[feature_values].append(index)
    signature_count = len(set(classes))
    next_mixed_code = signature_count
    pure_codes = set()
    mixed = []
    leaf_losses = []
    unresolved_pairs = 0
    for node in _leaf_nodes(tree):
        indices = by_leaf[node["leaf"]]
        labels = Counter(classes[index] for index in indices)
        pair_count = _incompatible_pairs(labels)
        unresolved_pairs += pair_count
        totals: dict[tuple, float] = defaultdict(float)
        square_sum = 0.0
        for index in indices:
            for coordinate, value in targets[index].items():
                totals[coordinate] += value
                square_sum += value * value
                work["constraint_audit_target_coordinate_reads"] += 1
        leaf_losses.append(max(0.0, square_sum - math.fsum(value * value for value in totals.values()) / len(indices)))
        if len(labels) == 1:
            node["leaf"] = next(iter(labels))
            pure_codes.add(node["leaf"])
        else:
            node["leaf"] = next_mixed_code
            next_mixed_code += 1
            representatives = list({classes[index]: index for index in indices}.values())
            mixed.append({"output_code": node["leaf"], "training_examples": len(indices),
                          "signature_classes": len(labels), "unresolved_signature_pairs": pair_count,
                          "distinct_feature_vectors": len({features[index] for index in indices}),
                          "action_envelopes": _envelopes(representatives, targets, actions, work)})
    collision_pairs, witness = 0, None
    for feature_values, indices in by_features.items():
        labels = Counter(classes[index] for index in indices)
        pairs = _incompatible_pairs(labels)
        collision_pairs += pairs
        if not pairs or witness is not None:
            continue
        left = indices[0]
        right = next(index for index in indices if classes[index] != classes[left])
        def record(index: int) -> dict[str, Any]:
            model_index, state = records[index]
            return {"source_model": training[model_index].name, "source_state": state,
                    "empirical_signature": signatures[index]}
        witness = {"feature_values": feature_values, "left": record(left), "right": record(right)}
    pure_leaves = len(by_leaf) - len(mixed)
    maximum_depth = 0
    pending = [(tree, 0)]
    while pending:
        node, depth = pending.pop()
        work["tree_diagnostic_nodes_read"] += 1
        maximum_depth = max(maximum_depth, depth)
        if "leaf" not in node:
            pending.extend(((node["left"], depth + 1), (node["right"], depth + 1)))
    return {"training_examples": len(features), "target_dimension": len({key for target in targets for key in target}),
            "signature_classes": signature_count, "leaves": len(by_leaf), "maximum_tree_depth": maximum_depth,
            "output_codes": len(pure_codes) + len(mixed), "pure_leaves": pure_leaves,
            "pure_signature_codes": len(pure_codes), "pure_leaf_code_reuses": pure_leaves - len(pure_codes),
            "mixed_leaves": mixed, "mixed_leaf_count": len(mixed),
            "unresolved_signature_pairs": unresolved_pairs,
            "identical_feature_conflicting_pairs": collision_pairs,
            "unresolved_feature_separable_pairs": unresolved_pairs - collision_pairs,
            "identical_feature_collision_witness": witness,
            "local_predictive_constraints_satisfied": unresolved_pairs == 0,
            "target_squared_error": math.fsum(leaf_losses)}


def _fit(training: tuple[TrainingModel, ...], method: str) -> EncoderFit:
    if not training:
        raise ValueError("training must be nonempty")
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
            group, features = profile(board, horizon, work)
            if group[1] != item.empirical.terminal[state] or group[2] != actions.get(state, ()):
                raise ValueError("empirical state status/actions differ from executable board semantics")
            profiles[model_index, state] = (group, features)
            groups[group].append((model_index, state))
            unique_board_layers.add((horizon, board))
    profile_seconds = perf_counter() - profile_started
    trees = {}
    encoder = RuntimeEncoder(trees)
    codes: dict[tuple[int, int], Code] = {}
    diagnostics = []
    unresolved_layers = set()
    target_seconds = tree_seconds = constraint_audit_seconds = 0.0
    for group, records in sorted(groups.items()):
        features = [profiles[record][1] for record in records]
        target_started = perf_counter()
        targets: list[dict[tuple, float]] = []
        for model_index, state in records if group[1] == "ACTIVE" else ():
            target: dict[tuple, float] = defaultdict(float)
            for action in group[2]:
                work["training_action_rows_read"] += 1
                for outcome in training[model_index].empirical.rows[state, action]:
                    work["training_successor_entries_read"] += 1
                    if outcome.probability:
                        target[action, "reward"] += outcome.probability * outcome.reward
                        target[action, "successor", codes[model_index, outcome.next_state]] += outcome.probability
            targets.append(dict(target))
        signatures = [tuple(sorted(target.items())) for target in targets]
        class_map = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
        classes = [class_map[signature] for signature in signatures]
        work["full_empirical_signatures_constructed"] += len(signatures)
        work["full_empirical_signature_coordinates"] += sum(len(signature) for signature in signatures)
        target_seconds += perf_counter() - target_started
        tree_started = perf_counter()
        if group[1] == "ACTIVE":
            if method == "signature_constraint":
                tree = _constraint_tree(features, classes, work)
            else:
                tree, _ = _fit_tree(features, targets, max_depth=len(records), min_leaf=1, work=work)
        else:
            tree = {"leaf": 0}
            work["terminal_groups_constant"] += 1
        tree_seconds += perf_counter() - tree_started
        audit_started = perf_counter()
        if group[1] == "ACTIVE":
            report = _normalize_and_audit(tree, features, targets, signatures, classes, records, training, group[2], work)
        else:
            report = {"training_examples": len(records), "target_dimension": 0, "signature_classes": 1,
                      "leaves": 1, "maximum_tree_depth": 0, "output_codes": 1, "pure_leaves": 1, "pure_signature_codes": 1,
                      "pure_leaf_code_reuses": 0, "mixed_leaves": [], "mixed_leaf_count": 0,
                      "unresolved_signature_pairs": 0, "identical_feature_conflicting_pairs": 0,
                      "unresolved_feature_separable_pairs": 0, "identical_feature_collision_witness": None,
                      "local_predictive_constraints_satisfied": True, "target_squared_error": 0.0}
        report["unresolved_lower_horizon_group_present"] = any(layer < group[0] for layer in unresolved_layers)
        if report["unresolved_signature_pairs"]:
            unresolved_layers.add(group[0])
        trees[group] = tree
        for record in records:
            codes[record] = encoder._encode_profile(group, profiles[record][1], work)
        constraint_audit_seconds += perf_counter() - audit_started
        diagnostics.append({"horizon": group[0], "status": group[1], "legal": list(group[2]), **report})
    active = [row for row in diagnostics if row["status"] == "ACTIVE"]
    unresolved_pairs = sum(row["unresolved_signature_pairs"] for row in active)
    return EncoderFit(encoder, {
        "method": method, "training_models": [item.name for item in training],
        "training_state_records": len(profiles), "unique_training_board_horizon_pairs": len(unique_board_layers),
        "training_active_state_records": sum(row["training_examples"] for row in active),
        "feature_names": list(FEATURE_NAMES), "groups": diagnostics,
        "active_tree_count": len(active), "active_leaf_count": sum(row["leaves"] for row in active),
        "active_output_code_count": sum(row["output_codes"] for row in active),
        "maximum_tree_depth": max((row["maximum_tree_depth"] for row in active), default=0),
        "pure_leaf_code_reuses": sum(row["pure_leaf_code_reuses"] for row in active),
        "training_target_squared_error": math.fsum(row["target_squared_error"] for row in active),
        "training_target_dimension_sum": sum(row["target_dimension"] for row in active),
        "full_empirical_signature_class_count": sum(row["signature_classes"] for row in active),
        "unresolved_signature_pairs": unresolved_pairs,
        "identical_feature_conflicting_pairs": sum(row["identical_feature_conflicting_pairs"] for row in active),
        "unresolved_feature_separable_pairs": sum(row["unresolved_feature_separable_pairs"] for row in active),
        "mixed_leaf_count": sum(row["mixed_leaf_count"] for row in active),
        "all_training_predictive_constraints_satisfied": unresolved_pairs == 0,
        "recursive_empirical_equivalence_supported": unresolved_pairs == 0,
        "constraint_scope": "Local signatures use frozen lower codes; recursive empirical equivalence requires every training group to resolve all incompatible signatures.",
        "min_leaf": 1, "depth_limit": "nonbinding training group record count" if method == "uncapped_sse" else None,
        "scientific_signature_tolerance": 0.0,
        "minimum_sse_gain": 1e-12 if method == "uncapped_sse" else None,
        "work_counts": dict(work), "feature_seconds": profile_seconds, "target_seconds": target_seconds,
        "tree_fit_seconds": tree_seconds, "constraint_audit_seconds": constraint_audit_seconds,
        "fit_seconds": perf_counter() - started,
    })


def fit_constraint_encoder(training: list[TrainingModel] | tuple[TrainingModel, ...]) -> EncoderFit:
    return _fit(tuple(training), "signature_constraint")


def fit_uncapped_sse_encoder(training: list[TrainingModel] | tuple[TrainingModel, ...]) -> EncoderFit:
    return _fit(tuple(training), "uncapped_sse")
