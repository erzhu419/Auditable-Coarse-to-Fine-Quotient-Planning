"""Canonical role-free templates for cross-occurrence terminal relations.

Column numbers and status tokens are erased from a source V28 program.  Every
referenced-column permutation is considered and the lexicographically minimum
tree becomes the reusable template.  A target instantiation enumerates only
injective anonymous-column bindings and accepts a template iff it exactly
classifies every retained target row.  The result is proposal-only.
"""

from __future__ import annotations

import hashlib
from itertools import permutations
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


_OPCODES = ("EQ", "LT", "LE", "GT", "GE")


class GenericRoleFreeRelationalTemplateV33Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRoleFreeRelationalTemplateV33Error(message)


def _columns(node: Any) -> set[int]:
    if type(node) is not dict:
        _fail("V33 relation tree changed")
    if node.get("kind") == "LEAF":
        if node.get("terminal_class") not in ("ACTIVE", "ACCEPT", "REJECT"):
            _fail("V33 terminal leaf changed")
        return set()
    if node.get("kind") != "RELATION" or node.get("opcode") not in _OPCODES:
        _fail("V33 relation node changed")
    left, right = node.get("left_column"), node.get("right_column")
    if type(left) is not int or type(right) is not int or left == right:
        _fail("V33 relation columns changed")
    return {
        left,
        right,
        *_columns(node.get("when_true")),
        *_columns(node.get("when_false")),
    }


def _role_tree(node: dict[str, Any], projection: Mapping[int, int]) -> dict[str, Any]:
    if node["kind"] == "LEAF":
        return {"kind": "LEAF", "terminal_class": node["terminal_class"]}
    return {
        "kind": "RELATION",
        "opcode": node["opcode"],
        "left_role": projection[node["left_column"]],
        "right_role": projection[node["right_column"]],
        "when_true": _role_tree(node["when_true"], projection),
        "when_false": _role_tree(node["when_false"], projection),
    }


def _canonical_tree(node: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    columns = sorted(_columns(node))
    if not columns:
        _fail("V33 reusable template requires at least one relation")
    choices = []
    for order in permutations(columns):
        projection = {column: role for role, column in enumerate(order)}
        tree = _role_tree(node, projection)
        choices.append((canonical_json_bytes(tree), tree))
    _encoded, tree = min(choices)
    return len(columns), tree


def compile_role_free_relational_template_library_v33(
    source_programs: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    if type(source_programs) is not tuple or not source_programs:
        _fail("V33 source program inventory changed")
    templates = {}
    source_ids = []
    for program in source_programs:
        if (
            type(program) is not dict
            or program.get("schema")
            != "acfqp.generic_relational_terminal_program.v28"
            or program.get("empirical_program_only") is not True
            or program.get("future_unseen_terminal_authority_present") is not False
        ):
            _fail("V33 source program boundary changed")
        source_ids.append(program.get("terminal_program_id"))
        frontier = program.get("decision_tree_candidate_frontier")
        if type(frontier) is not list or not frontier:
            _fail("V33 source frontier changed")
        for row in frontier:
            variable_count, tree = _canonical_tree(row.get("decision_tree"))
            encoded = canonical_json_bytes(tree)
            templates.setdefault(
                encoded,
                {
                    "role_variable_count": variable_count,
                    "role_free_decision_tree": tree,
                    "role_free_tree_sha256": hashlib.sha256(encoded).hexdigest(),
                    "source_terminal_program_ids": [],
                },
            )["source_terminal_program_ids"].append(program["terminal_program_id"])
    ordered = []
    for index, encoded in enumerate(sorted(templates)):
        row = templates[encoded]
        row["template_index"] = index
        row["source_terminal_program_ids"] = sorted(
            set(row["source_terminal_program_ids"])
        )
        ordered.append(row)
    payload = {
        "schema": "acfqp.generic_role_free_relational_template_library.v33",
        "source_terminal_program_ids": source_ids,
        "source_program_count": len(source_programs),
        "role_free_templates": ordered,
        "role_free_template_count": len(ordered),
        "raw_column_numbers_retained": False,
        "source_status_tokens_retained": False,
        "domain_or_state_role_names_present": False,
        "cross_occurrence_proposal_only": True,
        "future_target_prediction_authority_present": False,
        "abstract_plan_safety_authority_present": False,
    }
    return {
        **payload,
        "template_library_id": hashlib.sha256(
            b"acfqp:generic-role-free-relational-template-library:v33\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V33 target legal-action evidence changed")
    if legal:
        if terminal is not None:
            _fail("V33 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V33 target terminal row omitted its label")


def _relation(opcode: str, left: int, right: int, state: tuple[int, ...]) -> bool:
    if opcode == "EQ":
        return state[left] == state[right]
    if opcode == "LT":
        return state[left] < state[right]
    if opcode == "LE":
        return state[left] <= state[right]
    if opcode == "GT":
        return state[left] > state[right]
    if opcode == "GE":
        return state[left] >= state[right]
    _fail("V33 target relation opcode changed")


def _evaluate_role_tree(
    node: Mapping[str, Any], binding: tuple[int, ...], state: tuple[int, ...]
) -> str:
    while node.get("kind") == "RELATION":
        left = binding[node["left_role"]]
        right = binding[node["right_role"]]
        node = node["when_true"] if _relation(
            node["opcode"], left, right, state
        ) else node["when_false"]
    if node.get("kind") != "LEAF":
        _fail("V33 role-free tree leaf changed")
    return node.get("terminal_class")


def _column_tree(
    node: Mapping[str, Any], binding: tuple[int, ...], tokens: Mapping[str, int]
) -> dict[str, Any]:
    if node["kind"] == "LEAF":
        label = node["terminal_class"]
        return {
            "kind": "LEAF",
            "terminal_class": label,
            "status_token": tokens[label],
        }
    return {
        "kind": "RELATION",
        "opcode": node["opcode"],
        "left_column": binding[node["left_role"]],
        "right_column": binding[node["right_role"]],
        "when_true": _column_tree(node["when_true"], binding, tokens),
        "when_false": _column_tree(node["when_false"], binding, tokens),
    }


def _node_count(node: Mapping[str, Any]) -> int:
    if node["kind"] == "LEAF":
        return 1
    return 1 + _node_count(node["when_true"]) + _node_count(node["when_false"])


def instantiate_role_free_relational_template_v33(
    library: Mapping[str, Any],
    target_evidence: Mapping[str, Any],
    *,
    maximum_exact_instantiations: int = 32,
) -> dict[str, Any]:
    if (
        type(library) is not dict
        or library.get("schema")
        != "acfqp.generic_role_free_relational_template_library.v33"
        or library.get("cross_occurrence_proposal_only") is not True
        or type(maximum_exact_instantiations) is not int
        or not 1 <= maximum_exact_instantiations <= 128
    ):
        _fail("V33 template library changed")
    layout = target_evidence.get("layout")
    rows = target_evidence.get("raw_transition_rows")
    unknown = target_evidence.get("unknown_residual_target_columns")
    if (
        type(layout) is not dict
        or type(rows) is not list
        or not rows
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
    ):
        _fail("V33 target evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list:
        _fail("V33 target layout changed")
    states = []
    labels = []
    for row in rows:
        post = row.get("post_vector") if type(row) is dict else None
        if type(post) is not list or sorted(order) != list(range(len(post))):
            _fail("V33 target state width changed")
        states.append(tuple(post[index] for index in order))
        labels.append(_label(row))
    classes = sorted(set(labels))
    status_candidates = []
    for target in unknown:
        tokens = {}
        reverse = {}
        valid = True
        for state, label in zip(states, labels, strict=True):
            token = state[target]
            if (
                (label in tokens and tokens[label] != token)
                or (token in reverse and reverse[token] != label)
            ):
                valid = False
                break
            tokens[label] = token
            reverse[token] = label
        if valid and set(tokens) == set(classes):
            status_candidates.append((target, tokens))
    if len(status_candidates) != 1:
        _fail("V33 target status coordinate is not uniquely identified")
    status_target, tokens = status_candidates[0]
    available = tuple(index for index in range(len(states[0])) if index != status_target)
    attempts = 0
    matches = []
    truncated = False
    for template in library.get("role_free_templates", []):
        variable_count = template.get("role_variable_count")
        tree = template.get("role_free_decision_tree")
        if type(variable_count) is not int or not 0 < variable_count <= len(available):
            continue
        for binding in permutations(available, variable_count):
            attempts += 1
            if all(
                _evaluate_role_tree(tree, binding, state) == label
                for state, label in zip(states, labels, strict=True)
            ):
                matches.append(
                    {
                        "template_index": template["template_index"],
                        "role_free_tree_sha256": template["role_free_tree_sha256"],
                        "target_role_binding": list(binding),
                        "source_terminal_program_ids": template[
                            "source_terminal_program_ids"
                        ],
                    }
                )
                if len(matches) == maximum_exact_instantiations:
                    truncated = True
                    break
        if truncated:
            break
    matches.sort(key=canonical_json_bytes)
    frontier = []
    templates_by_index = {
        row["template_index"]: row for row in library["role_free_templates"]
    }
    for index, match in enumerate(matches):
        template = templates_by_index[match["template_index"]]
        binding = tuple(match["target_role_binding"])
        tree = _column_tree(
            template["role_free_decision_tree"], binding, tokens
        )
        encoded = canonical_json_bytes(tree)
        frontier.append(
            {
                "candidate_index": index,
                "decision_tree_node_count": _node_count(tree),
                "decision_tree_byte_count": len(encoded),
                "decision_tree_sha256": hashlib.sha256(encoded).hexdigest(),
                "decision_tree": tree,
                "role_free_tree_sha256": match["role_free_tree_sha256"],
                "target_role_binding": match["target_role_binding"],
            }
        )
    instantiated_program = None
    if frontier:
        relation_signatures = set()
        relation_evaluations = 0
        for left in available:
            for right in available:
                if left == right:
                    continue
                for opcode in _OPCODES:
                    signature = tuple(
                        _relation(opcode, left, right, state) for state in states
                    )
                    relation_evaluations += len(states)
                    if any(signature) and not all(signature):
                        relation_signatures.add(signature)
        program_payload = {
            "schema": "acfqp.generic_relational_terminal_program.v28",
            "status_target_column": status_target,
            "terminal_classes_observed": classes,
            "status_token_by_terminal_class": tokens,
            "decision_tree": frontier[0]["decision_tree"],
            "decision_tree_node_count": frontier[0]["decision_tree_node_count"],
            "decision_tree_candidate_frontier": frontier,
            "decision_tree_candidate_count": len(frontier),
            "maximum_tree_depth": 5,
            "maximum_program_candidates": maximum_exact_instantiations,
            "relation_opcode_registry": list(_OPCODES),
            "relation_feature_signature_count": len(relation_signatures),
            "relation_feature_evaluation_count": relation_evaluations,
            "primary_raw_transition_row_count": len(rows),
            "source_evidence_occurrence_count": 1,
            "source_raw_transition_row_counts": [len(rows)],
            "raw_transition_row_count": len(rows),
            "cross_occurrence_relation_structure_required": True,
            "exact_on_complete_frozen_query_pool": True,
            "anonymous_status_coordinate_derived_from_raw_labels": True,
            "state_column_roles_preregistered": False,
            "status_token_values_preregistered": False,
            "domain_specific_terminal_rule_present": False,
            "empirical_program_only": True,
            "future_unseen_terminal_authority_present": False,
            "abstract_plan_safety_authority_present": False,
            "global_exact_terminal_dynamics_claimed": False,
            "role_free_template_library_id": library["template_library_id"],
            "cross_occurrence_role_free_template_instantiation_present": True,
        }
        instantiated_program = {
            **program_payload,
            "terminal_program_id": hashlib.sha256(
                b"acfqp:generic-relational-terminal-program:v28\x00"
                + canonical_json_bytes(program_payload)
            ).hexdigest(),
        }
    payload = {
        "schema": "acfqp.generic_role_free_relational_template_instantiation.v33",
        "template_library_id": library.get("template_library_id"),
        "target_status_column": status_target,
        "target_status_token_by_terminal_class": tokens,
        "target_raw_transition_row_count": len(rows),
        "binding_evaluation_count": attempts,
        "exact_target_instantiations": matches,
        "exact_target_instantiation_count": len(matches),
        "selected_instantiation": None if not matches else matches[0],
        "instantiated_terminal_program": instantiated_program,
        "maximum_exact_instantiations": maximum_exact_instantiations,
        "instantiation_search_truncated_after_cap": truncated,
        "target_observation_exactness_required": True,
        "unmatched_target_rejected_as_ood": not matches,
        "cross_occurrence_proposal_only": True,
        "future_target_prediction_authority_present": False,
        "abstract_plan_safety_authority_present": False,
    }
    return {
        **payload,
        "instantiation_id": hashlib.sha256(
            b"acfqp:generic-role-free-relational-template-instantiation:v33\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "compile_role_free_relational_template_library_v33",
    "instantiate_role_free_relational_template_v33",
)
