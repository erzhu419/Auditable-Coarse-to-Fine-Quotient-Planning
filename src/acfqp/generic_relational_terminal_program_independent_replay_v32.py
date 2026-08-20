"""Independent, producer-free reconstruction of a V28 relation program.

The implementation imports neither V28 nor V30.  It re-derives the anonymous
status coordinate, finite relation features, minimum exact decision trees, and
content identity from retained raw rows.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


_OPCODES = ("EQ", "LT", "LE", "GT", "GE")


class GenericRelationalTerminalProgramIndependentReplayV32Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRelationalTerminalProgramIndependentReplayV32Error(message)


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V32 legal-action evidence changed")
    if legal:
        if terminal is not None:
            _fail("V32 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V32 terminal row omitted its acceptance label")


def _relation(opcode: str, left: int, right: int, row: tuple[int, ...]) -> bool:
    if opcode == "EQ":
        return row[left] == row[right]
    if opcode == "LT":
        return row[left] < row[right]
    if opcode == "LE":
        return row[left] <= row[right]
    if opcode == "GT":
        return row[left] > row[right]
    if opcode == "GE":
        return row[left] >= row[right]
    _fail("V32 relation opcode escaped its grammar")


def reconstruct_relational_terminal_program_v32(
    source: Mapping[str, Any],
    *,
    maximum_tree_depth: int = 5,
    maximum_program_candidates: int = 32,
) -> dict[str, Any]:
    if (
        type(source) is not dict
        or type(maximum_tree_depth) is not int
        or not 1 <= maximum_tree_depth <= 8
        or type(maximum_program_candidates) is not int
        or not 1 <= maximum_program_candidates <= 128
    ):
        _fail("V32 reconstruction input changed")
    layout = source.get("layout")
    rows = source.get("raw_transition_rows")
    unknown = source.get("unknown_residual_target_columns")
    if (
        type(layout) is not dict
        or type(rows) is not list
        or not rows
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
    ):
        _fail("V32 source inventory changed")
    state_order = layout.get("state_canonical_to_raw")
    state_colors = layout.get("state_structural_colors")
    if (
        type(state_order) is not list
        or type(state_colors) is not list
        or len(state_colors) != len(state_order)
        or len(set(state_colors)) != len(state_colors)
    ):
        _fail("V32 anonymous layout changed")
    posts = []
    labels = []
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(state_order) != list(range(len(post))):
            _fail("V32 raw successor width changed")
        posts.append(tuple(post[index] for index in state_order))
        labels.append(_label(row))
    classes = sorted(set(labels))
    if "ACTIVE" not in classes or "ACCEPT" not in classes:
        _fail("V32 source omitted active or accepting behavior")
    status_candidates = []
    for target in unknown:
        token_by_class: dict[str, int] = {}
        class_by_token: dict[int, str] = {}
        valid = True
        for state, label in zip(posts, labels, strict=True):
            token = state[target]
            if (
                (label in token_by_class and token_by_class[label] != token)
                or (token in class_by_token and class_by_token[token] != label)
            ):
                valid = False
                break
            token_by_class[label] = token
            class_by_token[token] = label
        if valid and set(token_by_class) == set(classes):
            status_candidates.append((target, token_by_class))
    if len(status_candidates) != 1:
        _fail("V32 anonymous terminal coordinate is not uniquely identified")
    status_target, token_by_class = status_candidates[0]
    width = len(posts[0])
    relation_by_signature = {}
    evaluations = 0
    for left in range(width):
        if left == status_target:
            continue
        for right in range(width):
            if right == left or right == status_target:
                continue
            for opcode in _OPCODES:
                signature = tuple(_relation(opcode, left, right, row) for row in posts)
                evaluations += len(posts)
                if all(signature) or not any(signature):
                    continue
                relation_by_signature.setdefault(signature, (opcode, left, right))
    relations = sorted(
        relation_by_signature.items(),
        key=lambda row: (row[1][0], row[1][1], row[1][2]),
    )
    if not relations:
        _fail("V32 relation grammar exposed no separating predicate")

    @lru_cache(maxsize=None)
    def build(
        indices: tuple[int, ...], depth: int
    ) -> tuple[int, bytes, dict[str, Any]] | None:
        selected = {labels[index] for index in indices}
        if len(selected) == 1:
            label = next(iter(selected))
            leaf = {
                "kind": "LEAF",
                "terminal_class": label,
                "status_token": token_by_class[label],
            }
            return 1, canonical_json_bytes(leaf), leaf
        if depth == 0:
            return None
        choices = []
        for signature, (opcode, left, right) in relations:
            yes_indices = tuple(index for index in indices if signature[index])
            no_indices = tuple(index for index in indices if not signature[index])
            if not yes_indices or not no_indices:
                continue
            yes = build(yes_indices, depth - 1)
            no = build(no_indices, depth - 1)
            if yes is None or no is None:
                continue
            node = {
                "kind": "RELATION",
                "opcode": opcode,
                "left_column": left,
                "right_column": right,
                "when_true": yes[2],
                "when_false": no[2],
            }
            encoded = canonical_json_bytes(node)
            choices.append((1 + yes[0] + no[0], len(encoded), encoded, node))
        if not choices:
            return None
        nodes, _length, encoded, node = min(choices)
        return nodes, encoded, node

    root = tuple(range(len(posts)))
    choices = []
    for signature, (opcode, left, right) in relations:
        yes_indices = tuple(index for index in root if signature[index])
        no_indices = tuple(index for index in root if not signature[index])
        if not yes_indices or not no_indices:
            continue
        yes = build(yes_indices, maximum_tree_depth - 1)
        no = build(no_indices, maximum_tree_depth - 1)
        if yes is None or no is None:
            continue
        node = {
            "kind": "RELATION",
            "opcode": opcode,
            "left_column": left,
            "right_column": right,
            "when_true": yes[2],
            "when_false": no[2],
        }
        encoded = canonical_json_bytes(node)
        choices.append((1 + yes[0] + no[0], len(encoded), encoded, node))
    choices.sort()
    unique = []
    seen = set()
    for choice in choices:
        if choice[2] in seen:
            continue
        seen.add(choice[2])
        unique.append(choice)
        if len(unique) == maximum_program_candidates:
            break
    if not unique:
        _fail("V32 relation grammar found no exact terminal tree")
    node_count, _length, _encoded, tree = unique[0]
    frontier = [
        {
            "candidate_index": index,
            "decision_tree_node_count": nodes,
            "decision_tree_byte_count": byte_count,
            "decision_tree_sha256": hashlib.sha256(encoded).hexdigest(),
            "decision_tree": candidate,
        }
        for index, (nodes, byte_count, encoded, candidate) in enumerate(unique)
    ]
    payload = {
        "schema": "acfqp.generic_relational_terminal_program.v28",
        "status_target_column": status_target,
        "terminal_classes_observed": classes,
        "status_token_by_terminal_class": token_by_class,
        "decision_tree": tree,
        "decision_tree_node_count": node_count,
        "decision_tree_candidate_frontier": frontier,
        "decision_tree_candidate_count": len(frontier),
        "maximum_tree_depth": maximum_tree_depth,
        "maximum_program_candidates": maximum_program_candidates,
        "relation_opcode_registry": list(_OPCODES),
        "relation_feature_signature_count": len(relations),
        "relation_feature_evaluation_count": evaluations,
        "primary_raw_transition_row_count": len(rows),
        "source_evidence_occurrence_count": 1,
        "source_raw_transition_row_counts": [len(rows)],
        "raw_transition_row_count": len(rows),
        "cross_occurrence_relation_structure_required": False,
        "exact_on_complete_frozen_query_pool": True,
        "anonymous_status_coordinate_derived_from_raw_labels": True,
        "state_column_roles_preregistered": False,
        "status_token_values_preregistered": False,
        "domain_specific_terminal_rule_present": False,
        "empirical_program_only": True,
        "future_unseen_terminal_authority_present": False,
        "abstract_plan_safety_authority_present": False,
        "global_exact_terminal_dynamics_claimed": False,
    }
    return {
        **payload,
        "terminal_program_id": hashlib.sha256(
            b"acfqp:generic-relational-terminal-program:v28\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def verify_source_complete_relational_program_v32(
    source: Mapping[str, Any], expected: Mapping[str, Any]
) -> dict[str, Any]:
    reconstructed = reconstruct_relational_terminal_program_v32(source)
    if reconstructed != expected:
        _fail("V32 independent terminal reconstruction changed")
    return {
        "terminal_program_id": reconstructed["terminal_program_id"],
        "raw_transition_row_count": reconstructed["raw_transition_row_count"],
        "anonymous_status_coordinate_rederived": True,
        "relation_feature_inventory_rederived": True,
        "decision_tree_frontier_rederived": True,
        "producer_imported": False,
        "v28_imported": False,
        "v30_imported": False,
    }


__all__ = (
    "reconstruct_relational_terminal_program_v32",
    "verify_source_complete_relational_program_v32",
)
