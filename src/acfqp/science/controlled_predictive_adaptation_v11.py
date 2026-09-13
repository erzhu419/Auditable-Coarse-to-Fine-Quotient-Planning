"""V9-identical target rules with feature blocks and ACTIVE-state intermediates.

Pure signature groups keep their source code without filling unused blocks.
Mixed groups batch all five blocks before the unchanged split algorithm.
Terminal states retain no feature contexts; no state shares cached computations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from time import perf_counter
from typing import Any

from .controlled_predictive_adaptation_v9 import TargetBuild, _install, _inventory, _original_code, _shape
from .controlled_predictive_encoder_runtime_v8 import _pool_rows
from .controlled_predictive_encoder_runtime_v11 import RuntimeEncoder, profile, feature_work_summary
from .controlled_predictive_encoder_v7 import Code, Group, RuleEncoder, TrainingModel
from .controlled_predictive_encoder_v8 import _constraint_tree, _envelopes, _leaf_nodes, _normalize_and_audit
from .controlled_predictive_quotient_v1 import Cell, CompiledModel, _actions


def _build(source: RuleEncoder, target: TrainingModel, mode: str) -> TargetBuild:
    started = perf_counter()
    work: Counter = Counter()
    copied = perf_counter()
    trees = deepcopy(source.trees)
    copy_seconds = perf_counter() - copied
    encoder = RuntimeEncoder(trees)
    source_inventory = {group: tuple(_inventory(tree, work)) for group, tree in trees.items()}
    empirical = target.empirical
    actions = _actions(empirical)
    work["legal_action_rows_indexed"] = len(empirical.rows)
    profiles = {}
    groups: dict[Group, list[int]] = defaultdict(list)
    original_codes: dict[int, Code] = {}
    occupied_paths = set()
    missing: Counter = Counter()
    profile_started = perf_counter()
    for state in sorted(empirical.layers):
        group, features = profile(target.boards[state], empirical.layers[state], work)
        if group[1] != empirical.terminal[state] or group[2] != actions.get(state, ()):
            raise ValueError("empirical state status/actions differ from executable board semantics")
        profiles[state] = (group, features)
        groups[group].append(state)
        if group not in source.trees:
            missing[group] += 1
        if group[1] != "ACTIVE":
            output = 0
            occupied_paths.add((group, ()))
        elif group not in source.trees:
            output = -1
        else:
            output, path = _original_code(source.trees[group], features, work)
            occupied_paths.add((group, path))
        original_codes[state] = (*group, output)
    profile_seconds = perf_counter() - profile_started
    final_codes: dict[int, Code] = {}
    records = []
    unresolved_layers = set()
    refined = repaired = partially_repaired = untouched_pure = irreducible_mixed = 0
    initial_impure_by_layer: Counter = Counter()
    initial_nodes = sum(2 * len(leaves) - 1 for leaves in source_inventory.values())
    initial_leaf_occurrences = sum(len(leaves) for leaves in source_inventory.values())
    empty_codegroups = empty_leaf_retained = empty_leaf_patched = 0
    target_signature_seconds = rule_fit_seconds = audit_seconds = install_seconds = 0.0
    feature_materialization_seconds = 0.0
    pre_split_witnesses = []
    for group, states in sorted(groups.items()):
        by_base: dict[int, list[int]] = defaultdict(list)
        for state in states:
            by_base[original_codes[state][-1]].append(state)
        original_tree = trees.get(group, {"leaf": 0 if group[1] != "ACTIVE" else -1})
        old_leaves = source_inventory.get(group, (((), original_tree["leaf"]),)) if group not in trees else source_inventory[group]
        unoccupied_codes = {code for _, code in old_leaves} - by_base.keys()
        empty_codegroups += len(unoccupied_codes)
        empty_leaf_retained += sum(code in unoccupied_codes for _, code in old_leaves)
        if group[1] != "ACTIVE":
            trees[group] = original_tree
            for state in states:
                final_codes[state] = (*group, 0)
            records.append({"horizon": group[0], "status": group[1], "legal": [],
                            "target_state_records": len(states), "original_output_codes": [],
                            "unresolved_signature_pairs": 0, "local_predictive_constraints_satisfied": True})
            continue
        signature_started = perf_counter()
        targets: dict[int, dict[tuple, float]] = {}
        signatures = {}
        for state in states:
            vector: dict[tuple, float] = defaultdict(float)
            for action in group[2]:
                work["target_validation_action_rows_read"] += 1
                for outcome in empirical.rows[state, action]:
                    work["target_validation_successor_entries_read"] += 1
                    if outcome.probability:
                        vector[action, "reward"] += outcome.probability * outcome.reward
                        vector[action, "successor", final_codes[outcome.next_state]] += outcome.probability
            targets[state] = dict(vector)
            signatures[state] = tuple(sorted(vector.items()))
            work["target_empirical_signatures_constructed"] += 1
            work["target_empirical_signature_coordinates"] += len(vector)
        target_signature_seconds += perf_counter() - signature_started
        next_code = max(code for _, code in old_leaves) + 1
        patches = {}
        reports = []
        for base_code, members in sorted(by_base.items()):
            vectors = [targets[state] for state in members]
            member_signatures = [signatures[state] for state in members]
            class_map = {signature: i for i, signature in enumerate(sorted(set(member_signatures)))}
            classes = [class_map[signature] for signature in member_signatures]
            mixed_before = len(class_map) > 1
            initial_impure_by_layer[group[0]] += mixed_before
            materialization_started = perf_counter()
            if mixed_before:
                features = [profiles[state][1].materialize() for state in members]
                work["mixed_group_feature_vector_materializations"] += len(members)
            else:
                # All signatures agree, so no conflicting feature pair can exist.
                # The constant-leaf audit reads numeric targets but needs no features.
                features = [()] * len(members)
                work["pure_group_full_feature_vectors_not_requested"] += len(members)
            feature_materialization_seconds += perf_counter() - materialization_started
            fit_started = perf_counter()
            tree = _constraint_tree(features, classes, work) if mixed_before else {"leaf": 0}
            rule_fit_seconds += perf_counter() - fit_started
            audit_started = perf_counter()
            report = _normalize_and_audit(tree, features, vectors, member_signatures, classes,
                [(0, state) for state in members], (target,), group[2], work)
            if mixed_before and len(pre_split_witnesses) < 3:
                different = next(i for i in range(1, len(members)) if classes[i] != classes[0])
                pre_split_witnesses.append({"horizon": group[0], "legal": list(group[2]),
                    "original_output_code": base_code, "target_states": [members[0], members[different]],
                    "scope": "Two empirical signatures before this local split, not the whole-cell envelope.",
                    "action_envelopes": _envelopes([0, different], vectors, group[2], work)})
            local_codes = sorted({node["leaf"] for node in _leaf_nodes(tree)})
            changed = "leaf" not in tree
            if changed:
                code_map = dict(zip(local_codes, range(next_code, next_code + len(local_codes))))
                next_code += len(local_codes)
                refined += 1
                if report["unresolved_signature_pairs"] == 0:
                    repaired += 1
                else:
                    partially_repaired += 1
            else:
                code_map = {local_codes[0]: base_code}
                if mixed_before:
                    irreducible_mixed += 1
                else:
                    untouched_pure += 1
            for node in _leaf_nodes(tree):
                node["leaf"] = code_map[node["leaf"]]
            for mixed_leaf in report["mixed_leaves"]:
                mixed_leaf["output_code"] = code_map[mixed_leaf["output_code"]]
            if changed:
                patches[base_code] = tree
            report.update(original_output_code=base_code, mixed_before_local_split=mixed_before,
                          rule_patch_inserted=changed, final_output_codes=sorted(code_map.values()))
            reports.append(report)
            audit_seconds += perf_counter() - audit_started
        install_started = perf_counter()
        trees[group] = _install(original_tree, patches, work) if patches else original_tree
        empty_leaf_patched += sum(code in patches and (group, path) not in occupied_paths for path, code in old_leaves)
        install_seconds += perf_counter() - install_started
        audit_started = perf_counter()
        for state in states:
            final_codes[state] = encoder._encode_profile(group, profiles[state][1], work)
        unresolved = sum(row["unresolved_signature_pairs"] for row in reports)
        record = {"horizon": group[0], "status": group[1], "legal": list(group[2]),
                  "target_state_records": len(states), "original_output_codes": reports,
                  "unresolved_signature_pairs": unresolved,
                  "local_predictive_constraints_satisfied": unresolved == 0,
                  "unresolved_lower_horizon_group_present": any(layer < group[0] for layer in unresolved_layers)}
        if unresolved:
            unresolved_layers.add(group[0])
        records.append(record)
        audit_seconds += perf_counter() - audit_started
    absent_source_groups = source.trees.keys() - groups.keys()
    for group in absent_source_groups:
        empty_codegroups += len({code for _, code in source_inventory[group]})
        empty_leaf_retained += len(source_inventory[group])
    grouping_started = perf_counter()
    cell_members: dict[Code, list[int]] = defaultdict(list)
    for state in sorted(final_codes):
        cell_members[final_codes[state]].append(state)
    mapping, cells, code_to_cell = {}, {}, {}
    for cell, (code, members) in enumerate(sorted(cell_members.items())):
        cells[cell] = Cell(code[0], code[1], tuple(members))
        code_to_cell[code] = cell
        for state in members:
            mapping[state] = cell
    grouping_seconds = perf_counter() - grouping_started
    pooling_started = perf_counter()
    rows = _pool_rows(empirical, cells, mapping, actions, work)
    pooling_seconds = perf_counter() - pooling_started
    compiled = CompiledModel(cells, rows, tuple(mapping[root] for root in empirical.roots), mapping, {})
    inventory_started = perf_counter()
    shapes = {group: _shape(tree, work) for group, tree in trees.items()}
    final_nodes = sum(shape[0] for shape in shapes.values())
    final_leaves = sum(shape[1] for shape in shapes.values())
    for record in records:
        group = (record["horizon"], record["status"], tuple(record["legal"]))
        record["maximum_tree_depth"] = shapes[group][2]
    inventory_seconds = perf_counter() - inventory_started
    reports = [r for group in records for r in group["original_output_codes"]]
    unresolved = sum(r["unresolved_signature_pairs"] for r in reports)
    initial_active = len({code for code in original_codes.values() if code[1] == "ACTIVE"})
    final_active = sum(cell.terminal == "ACTIVE" for cell in cells.values())
    return TargetBuild(encoder, compiled, code_to_cell, {
        "method": mode, "target_name": target.name, "groups": records,
        "target_state_records": len(profiles), "target_active_state_records": sum(status == "ACTIVE" for status in empirical.terminal.values()),
        "states_encoded": len(profiles), "initial_active_cells": initial_active,
        "final_active_cells": final_active, "active_cells": final_active, "cells": len(cells),
        "impure_base_code_groups_when_visited_by_layer": dict(sorted(initial_impure_by_layer.items())),
        "refined_source_code_groups": refined, "repaired_source_code_groups": repaired,
        "partially_repaired_source_code_groups": partially_repaired, "untouched_pure_source_code_groups": untouched_pure,
        "irreducible_mixed_source_code_groups": irreducible_mixed,
        "initial_source_tree_nodes": initial_nodes, "final_tree_nodes": final_nodes,
        "added_tree_nodes_including_new_groups": final_nodes - initial_nodes,
        "initial_source_leaf_occurrences": initial_leaf_occurrences, "final_leaf_occurrences": final_leaves,
        "maximum_tree_depth": max((shape[2] for shape in shapes.values()), default=0),
        "source_output_codes_without_target_records_retained": empty_codegroups,
        "source_leaf_occurrences_with_unoccupied_output_code_retained": empty_leaf_retained,
        "unvisited_source_leaf_occurrences_patched_via_shared_code": empty_leaf_patched,
        "source_group_trees_without_target_states_retained": len(absent_source_groups),
        "source_unseen_group_states": sum(missing.values()),
        "source_unseen_active_group_states": sum(n for group, n in missing.items() if group[1] == "ACTIVE"),
        "source_missing_groups": [{"horizon": group[0], "status": group[1], "legal": list(group[2]), "states": count}
                                  for group, count in sorted(missing.items())],
        "unresolved_signature_pairs": unresolved,
        "identical_feature_conflicting_pairs": sum(r["identical_feature_conflicting_pairs"] for r in reports),
        "unresolved_feature_separable_pairs": sum(r["unresolved_feature_separable_pairs"] for r in reports),
        "all_target_predictive_constraints_satisfied": unresolved == 0,
        "recursive_empirical_equivalence_supported": unresolved == 0,
        "first_three_pre_split_empirical_signature_witnesses": pre_split_witnesses,
        "partition_rule": "Refine original source output codes; no merge across original codes. Unoccupied source codes retain their rules.",
        "target_work_scope": "Per-ACTIVE-state swipe intermediates and five feature blocks; mixed-signature groups batch materialize all 31; no cross-state cache; all target rows validated and finally pooled once.",
        "feature_storage": feature_work_summary(work),
        "feature_materialization_seconds": feature_materialization_seconds,
        "work_counts": dict(work), "source_deepcopy_seconds": copy_seconds,
        "profile_seconds": profile_seconds, "target_signature_seconds": target_signature_seconds,
        "rule_fit_seconds": rule_fit_seconds, "constraint_audit_seconds": audit_seconds,
        "rule_patch_install_seconds": install_seconds, "final_grouping_seconds": grouping_seconds,
        "final_pooling_seconds": pooling_seconds, "final_tree_inventory_seconds": inventory_seconds,
        "build_seconds": perf_counter() - started,
    })


def build_adapted_target(source: RuleEncoder, target: TrainingModel) -> TargetBuild:
    return _build(source, target, "source_initialized_target_constraint_adaptation_block_features")


def build_scratch_target(target: TrainingModel) -> TargetBuild:
    return _build(RuntimeEncoder({}), target, "from_scratch_target_constraint_rules_block_features")
