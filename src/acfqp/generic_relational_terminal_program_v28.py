"""Infer an anonymous terminal/status program from raw successor relations.

The constructor first identifies a categorical coordinate whose successor
tokens are in one-to-one correspondence with ACTIVE/ACCEPT/REJECT labels that
are already present in raw transition evidence.  It then searches a finite
relation grammar over the *other* anonymous successor columns and builds the
minimum exact decision tree.  No domain, state-role, or token name is supplied.
The result is empirical and proposal-only; certificates still control every
ground query and terminal decision used for safety.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


RELATION_OPCODES_V28 = ("EQ", "LT", "LE", "GT", "GE")


class GenericRelationalTerminalProgramV28Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRelationalTerminalProgramV28Error(message)


def _label(row: Mapping[str, Any]) -> str:
    legal_after = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal_after) is not list:
        _fail("V28 legal-action evidence changed")
    if legal_after:
        if terminal is not None:
            _fail("V28 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V28 terminal row omitted its acceptance label")


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
    _fail("V28 relation opcode escaped its grammar")


def evaluate_relational_terminal_program_v28(
    program: Mapping[str, Any], canonical_state: tuple[int, ...]
) -> dict[str, Any]:
    if (
        type(program) is not dict
        or program.get("schema") != "acfqp.generic_relational_terminal_program.v28"
        or type(canonical_state) is not tuple
    ):
        _fail("V28 program evaluation input changed")
    node = program.get("decision_tree")
    while type(node) is dict and node.get("kind") == "RELATION":
        left = node.get("left_column")
        right = node.get("right_column")
        opcode = node.get("opcode")
        if (
            type(left) is not int
            or type(right) is not int
            or not 0 <= left < len(canonical_state)
            or not 0 <= right < len(canonical_state)
            or opcode not in RELATION_OPCODES_V28
        ):
            _fail("V28 decision node changed")
        node = node["when_true"] if _relation(
            opcode, left, right, canonical_state
        ) else node["when_false"]
    if type(node) is not dict or node.get("kind") != "LEAF":
        _fail("V28 decision leaf changed")
    return {
        "terminal_class": node.get("terminal_class"),
        "status_token": node.get("status_token"),
    }


def synthesize_relational_terminal_program_v28(
    evidence: Mapping[str, Any],
    *,
    additional_evidence: tuple[Mapping[str, Any], ...] = (),
    maximum_tree_depth: int = 5,
    maximum_program_candidates: int = 32,
) -> dict[str, Any]:
    if (
        type(maximum_tree_depth) is not int
        or not 1 <= maximum_tree_depth <= 8
        or type(additional_evidence) is not tuple
        or len(additional_evidence) > 8
        or type(maximum_program_candidates) is not int
        or not 1 <= maximum_program_candidates <= 128
    ):
        _fail("V28 decision-tree depth changed")

    def parse(source: Mapping[str, Any]) -> tuple[
        list[tuple[int, ...]], list[str], int, dict[str, int], int, list[str]
    ]:
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
            _fail("V28 evidence inventory changed")
        state_order = layout.get("state_canonical_to_raw")
        state_colors = layout.get("state_structural_colors")
        if (
            type(state_order) is not list
            or type(state_colors) is not list
            or len(state_colors) != len(state_order)
            or len(set(state_colors)) != len(state_colors)
        ):
            _fail("V28 anonymous state layout changed")
        posts = []
        row_labels = []
        for row in rows:
            post = row.get("post_vector") if type(row) is dict else None
            if (
                type(post) is not list
                or sorted(state_order) != list(range(len(post)))
            ):
                _fail("V28 raw successor width changed")
            posts.append(tuple(post[index] for index in state_order))
            row_labels.append(_label(row))
        classes = sorted(set(row_labels))
        if "ACTIVE" not in classes or "ACCEPT" not in classes:
            _fail("V28 evidence omitted active or accepting behavior")
        candidates = []
        for target in unknown:
            token_by_class: dict[str, int] = {}
            class_by_token: dict[int, str] = {}
            valid = True
            for state, label in zip(posts, row_labels, strict=True):
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
                candidates.append((target, token_by_class))
        if len(candidates) != 1:
            _fail("V28 anonymous terminal coordinate is not uniquely identified")
        target, tokens = candidates[0]
        return posts, row_labels, target, tokens, len(rows), state_colors

    parsed = [parse(evidence), *(parse(row) for row in additional_evidence)]
    (
        primary_posts,
        primary_labels,
        status_target,
        token_by_class,
        primary_count,
        primary_colors,
    ) = parsed[0]
    width = len(primary_posts[0])
    canonical_posts = []
    labels = []
    row_counts = []
    for posts, row_labels, target, tokens, row_count, colors in parsed:
        if set(colors) != set(primary_colors):
            _fail("V28 cross-occurrence structural color inventory changed")
        projection = [colors.index(color) for color in primary_colors]
        projected_posts = [
            tuple(state[index] for index in projection) for state in posts
        ]
        projected_target = primary_colors.index(colors[target])
        if (
            projected_target != status_target
            or tokens != token_by_class
            or len(projected_posts[0]) != width
        ):
            _fail("V28 cross-occurrence terminal binding changed")
        canonical_posts.extend(projected_posts)
        labels.extend(row_labels)
        row_counts.append(row_count)
    classes = sorted(set(labels))
    relation_by_signature = {}
    evaluation_count = 0
    for left in range(width):
        if left == status_target:
            continue
        for right in range(width):
            if right == left or right == status_target:
                continue
            for opcode in RELATION_OPCODES_V28:
                signature = tuple(
                    _relation(opcode, left, right, state)
                    for state in canonical_posts
                )
                evaluation_count += len(canonical_posts)
                if all(signature) or not any(signature):
                    continue
                relation_by_signature.setdefault(signature, (opcode, left, right))
    relations = sorted(
        relation_by_signature.items(),
        key=lambda row: (row[1][0], row[1][1], row[1][2]),
    )
    if not relations:
        _fail("V28 relation grammar exposed no separating predicate")

    @lru_cache(maxsize=None)
    def build(indices: tuple[int, ...], depth: int) -> tuple[int, bytes, dict[str, Any]] | None:
        selected_labels = {labels[index] for index in indices}
        if len(selected_labels) == 1:
            label = next(iter(selected_labels))
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
            truth = tuple(index for index in indices if signature[index])
            false = tuple(index for index in indices if not signature[index])
            if not truth or not false:
                continue
            yes = build(truth, depth - 1)
            no = build(false, depth - 1)
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

    root_indices = tuple(range(len(canonical_posts)))
    root_choices = []
    for signature, (opcode, left, right) in relations:
        truth = tuple(index for index in root_indices if signature[index])
        false = tuple(index for index in root_indices if not signature[index])
        if not truth or not false:
            continue
        yes = build(truth, maximum_tree_depth - 1)
        no = build(false, maximum_tree_depth - 1)
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
        root_choices.append((1 + yes[0] + no[0], len(encoded), encoded, node))
    root_choices.sort()
    unique_choices = []
    seen_trees = set()
    for choice in root_choices:
        if choice[2] in seen_trees:
            continue
        seen_trees.add(choice[2])
        unique_choices.append(choice)
        if len(unique_choices) == maximum_program_candidates:
            break
    if not unique_choices:
        _fail("V28 relation grammar found no exact terminal tree")
    node_count, _byte_count, _encoded, tree = unique_choices[0]
    frontier = [
        {
            "candidate_index": index,
            "decision_tree_node_count": nodes,
            "decision_tree_byte_count": byte_count,
            "decision_tree_sha256": hashlib.sha256(encoded).hexdigest(),
            "decision_tree": candidate_tree,
        }
        for index, (nodes, byte_count, encoded, candidate_tree) in enumerate(
            unique_choices
        )
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
        "relation_opcode_registry": list(RELATION_OPCODES_V28),
        "relation_feature_signature_count": len(relations),
        "relation_feature_evaluation_count": evaluation_count,
        "primary_raw_transition_row_count": primary_count,
        "source_evidence_occurrence_count": len(parsed),
        "source_raw_transition_row_counts": row_counts,
        "raw_transition_row_count": len(canonical_posts),
        "cross_occurrence_relation_structure_required": len(parsed) > 1,
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
    result = {
        **payload,
        "terminal_program_id": hashlib.sha256(
            b"acfqp:generic-relational-terminal-program:v28\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    for state, label in zip(canonical_posts, labels, strict=True):
        replay = evaluate_relational_terminal_program_v28(result, state)
        if (
            replay["terminal_class"] != label
            or replay["status_token"] != state[status_target]
        ):
            _fail("V28 terminal program failed exact replay")
    return result


__all__ = (
    "evaluate_relational_terminal_program_v28",
    "synthesize_relational_terminal_program_v28",
)
