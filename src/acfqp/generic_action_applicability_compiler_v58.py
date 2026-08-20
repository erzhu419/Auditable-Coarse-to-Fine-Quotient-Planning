"""Discover anonymous state-action applicability from source observations."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


_PROGRAM_DOMAIN = b"acfqp:generic-action-applicability-program:v58\x00"
_OPCODES = ("EQ", "NE", "LT", "LE", "GT", "GE")


class GenericActionApplicabilityCompilerV58Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericActionApplicabilityCompilerV58Error(message)


def _predicate(opcode: str, left: int, right: int) -> bool:
    return {
        "EQ": left == right,
        "NE": left != right,
        "LT": left < right,
        "LE": left <= right,
        "GT": left > right,
        "GE": left >= right,
    }[opcode]


def _member_examples(
    member: Mapping[str, Any], receipt: Mapping[str, Any]
) -> tuple[tuple[tuple[int, ...], tuple[int, ...], bool], ...]:
    state_order = receipt.get("state_canonical_to_raw")
    action_order = receipt.get("action_canonical_to_raw")
    catalogue = member.get("action_catalogue")
    evidence = member.get("source_evidence")
    rows = evidence.get("raw_transition_rows") if type(evidence) is dict else None
    if (
        type(state_order) is not list
        or type(action_order) is not list
        or type(catalogue) is not list
        or not catalogue
        or type(rows) is not list
        or not rows
    ):
        _fail("V58 source member inventory changed")
    actions = {}
    for action in catalogue:
        key = action.get("action_key") if type(action) is dict else None
        fields = action.get("anonymous_fields") if type(action) is dict else None
        if (
            type(key) is not int
            or type(fields) is not list
            or sorted(action_order) != list(range(len(fields)))
            or any(type(value) is not int for value in fields)
        ):
            _fail("V58 anonymous action catalogue changed")
        actions[key] = tuple(fields[index] for index in action_order)
    states: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in rows:
        pre = row.get("pre_vector") if type(row) is dict else None
        post = row.get("post_vector") if type(row) is dict else None
        before = row.get("legal_action_keys_before") if type(row) is dict else None
        after = row.get("legal_action_keys_after") if type(row) is dict else None
        if (
            type(pre) is not list
            or type(post) is not list
            or type(before) is not list
            or type(after) is not list
            or sorted(state_order) != list(range(len(pre)))
            or len(pre) != len(post)
        ):
            _fail("V58 raw state/legal observation changed")
        states[tuple(pre[index] for index in state_order)] = tuple(before)
        states[tuple(post[index] for index in state_order)] = tuple(after)
    result = []
    for state in sorted(states):
        legal = set(states[state])
        if not legal <= set(actions):
            _fail("V58 legal action lacks an anonymous descriptor")
        for key in sorted(actions):
            result.append((state, actions[key], key in legal))
    return tuple(result)


def _exact(
    program: Mapping[str, Any],
    examples: tuple[tuple[tuple[int, ...], tuple[int, ...], bool], ...],
) -> bool:
    state_column = program["state_column"]
    action_field = program["action_field"]
    opcode = program["opcode"]
    return all(
        _predicate(opcode, state[state_column], action[action_field]) == expected
        for state, action, expected in examples
    )


def compile_action_applicability_program_v58(
    campaign: Mapping[str, Any],
    *,
    source_campaign_id: str,
    source_campaign_sha256: str,
    source_model_id: str,
) -> dict[str, Any]:
    if (
        type(campaign) is not dict
        or campaign.get("campaign_id") != source_campaign_id
        or hashlib.sha256(canonical_json_bytes(campaign)).hexdigest()
        != source_campaign_sha256
    ):
        _fail("V58 frozen source campaign changed")
    groups = campaign.get("structural_group_results")
    partition = campaign.get("structural_source_partition")
    members = campaign.get("source_members")
    if type(groups) is not list or type(partition) is not dict or type(members) is not list:
        _fail("V58 source campaign structure changed")
    selected = [
        row
        for row in groups
        if type(row) is dict
        and type(row.get("projected_disagreement_successor_model")) is dict
        and row["projected_disagreement_successor_model"].get(
            "projected_disagreement_successor_model_id"
        )
        == source_model_id
    ]
    if len(selected) != 1:
        _fail("V58 source model structural group changed")
    group = selected[0]
    partition_rows = partition.get("structural_groups")
    if type(partition_rows) is not list:
        _fail("V58 structural partition changed")
    source_group = next(
        (
            row
            for row in partition_rows
            if row.get("structural_signature_id")
            == group.get("structural_signature_id")
        ),
        None,
    )
    evidence = source_group.get("source_evidence") if type(source_group) is dict else None
    receipts = evidence.get("source_member_receipts") if type(evidence) is dict else None
    if type(receipts) is not list or len(receipts) < 2:
        _fail("V58 source receipts changed")
    member_by_id = {row.get("member_id"): row for row in members if type(row) is dict}
    ordered = sorted(receipts, key=lambda row: row["member_id"])
    training_receipts = ordered[:-1]
    heldout_receipts = ordered[-1:]
    training = tuple(
        example
        for receipt in training_receipts
        for example in _member_examples(member_by_id[receipt["member_id"]], receipt)
    )
    heldout = tuple(
        example
        for receipt in heldout_receipts
        for example in _member_examples(member_by_id[receipt["member_id"]], receipt)
    )
    if not training or not heldout:
        _fail("V58 training/heldout split changed")
    state_width = len(training[0][0])
    action_width = len(training[0][1])
    candidates = []
    evaluations = 0
    for opcode in _OPCODES:
        for state_column in range(state_width):
            for action_field in range(action_width):
                evaluations += len(training)
                row = {
                    "schema": "acfqp.generic_action_applicability_relation.v58",
                    "opcode": opcode,
                    "state_column": state_column,
                    "action_field": action_field,
                    "result_type": "BOOL",
                    "semantic_names_used": False,
                }
                if _exact(row, training):
                    candidates.append(row)
    if not candidates:
        _fail("V58 grammar found no exact applicability relation")
    candidates.sort(key=lambda row: (len(canonical_json_bytes(row)), canonical_json_bytes(row)))
    selected_program = candidates[0]
    if not _exact(selected_program, heldout):
        _fail("V58 selected applicability relation failed heldout")
    payload = {
        "schema": "acfqp.generic_action_applicability_program.v58",
        "source_campaign_id": source_campaign_id,
        "source_campaign_sha256": source_campaign_sha256,
        "source_model_id": source_model_id,
        "source_structural_signature_id": group["structural_signature_id"],
        "training_member_ids": [row["member_id"] for row in training_receipts],
        "heldout_member_ids": [row["member_id"] for row in heldout_receipts],
        "state_width": state_width,
        "action_field_width": action_width,
        "typed_relation_grammar": {
            "opcodes": list(_OPCODES),
            "left_operands": "ALL_ANONYMOUS_STATE_COLUMNS",
            "right_operands": "ALL_ANONYMOUS_ACTION_FIELDS",
            "selection": "MIN_CANONICAL_PROGRAM_BYTES_THEN_BYTES",
        },
        "selected_program": selected_program,
        "training_state_action_classification_count": len(training),
        "training_positive_count": sum(row[2] for row in training),
        "training_negative_count": sum(not row[2] for row in training),
        "training_exact_candidate_count": len(candidates),
        "heldout_state_action_classification_count": len(heldout),
        "heldout_positive_count": sum(row[2] for row in heldout),
        "heldout_negative_count": sum(not row[2] for row in heldout),
        "grammar_relation_evaluations": evaluations,
        "training_exact": True,
        "heldout_exact": True,
        "source_member_split_fixed_before_v87_target_outcomes": True,
        "state_action_classifications_are_derived_views_not_physical_labels": True,
        "future_target_outcome_input_present": False,
        "applicability_program_safety_authority_present": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "action_applicability_program_id": hashlib.sha256(
            _PROGRAM_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def applicable_action_keys_v58(
    program: Mapping[str, Any],
    state: tuple[int, ...],
    actions: tuple[Any, ...],
) -> tuple[int, ...]:
    relation = program.get("selected_program") if type(program) is dict else None
    if (
        type(relation) is not dict
        or program.get("schema") != "acfqp.generic_action_applicability_program.v58"
        or type(state) is not tuple
        or len(state) != program.get("state_width")
    ):
        _fail("V58 applicability execution inventory changed")
    result = []
    for action in actions:
        fields = getattr(action, "fields", None)
        key = getattr(action, "key", None)
        if type(fields) is not tuple or type(key) is not int:
            _fail("V58 applicability action changed")
        if _predicate(
            relation["opcode"],
            state[relation["state_column"]],
            fields[relation["action_field"]],
        ):
            result.append(key)
    return tuple(result)


__all__ = (
    "applicable_action_keys_v58",
    "compile_action_applicability_program_v58",
)
