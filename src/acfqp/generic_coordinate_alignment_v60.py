"""Infer a source-to-target coordinate projection from anonymous observations.

The source model is not refit.  The compiler enumerates only type-compatible
state/action bijections, instantiates the frozen applicability relation, and
retains mappings that replay every observed partial factor, residual support,
and terminal label.  The resulting projection is proposal-only; exact local
certificates remain the sole safety authority.
"""

from __future__ import annotations

import hashlib
from itertools import permutations, product
from typing import Any, Mapping, NoReturn

from acfqp.generic_action_applicability_compiler_v58 import _predicate
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_contextual_ordinal_residual_v54 import _value
from acfqp.generic_joint_successor_version_space_planner_v42 import _partial_support
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_projected_disagreement_model_compiler_v56 import (
    verify_projected_disagreement_model_v56,
)
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)
from acfqp.phase3e_ids import canonical_json_bytes


_ALIGNMENT_DOMAIN = b"acfqp:generic-coordinate-alignment:v60\x00"


class GenericCoordinateAlignmentV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCoordinateAlignmentV60Error(message)


def _canonical_rows(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...]]:
    if type(candidate) is not PartialFactorCandidateV15 or not rows or not catalogue:
        _fail("V60 target alignment inventory changed")
    return align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )


def _applicability_examples(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[tuple[tuple[int, ...], tuple[int, ...], bool], ...]:
    actions = {row.key: row.fields for row in catalogue}
    states: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in rows:
        for state, legal in ((row.pre, row.legal_before), (row.post, row.legal_after)):
            prior = states.setdefault(state, legal)
            if prior != legal:
                _fail("V60 one target state carried inconsistent legal actions")
    examples = []
    for state in sorted(states):
        legal = set(states[state])
        if not legal <= set(actions):
            _fail("V60 target legal action lacks anonymous metadata")
        for key in sorted(actions):
            examples.append((state, actions[key], key in legal))
    return tuple(examples)


def _exact_applicability_bindings(
    opcode: str,
    state_width: int,
    action_width: int,
    examples: tuple[tuple[tuple[int, ...], tuple[int, ...], bool], ...],
) -> tuple[tuple[tuple[int, int], ...], int]:
    exact = []
    evaluations = 0
    for state_column in range(state_width):
        for action_field in range(action_width):
            evaluations += len(examples)
            if all(
                _predicate(opcode, state[state_column], action[action_field])
                == expected
                for state, action, expected in examples
            ):
                exact.append((state_column, action_field))
    return tuple(exact), evaluations


def _state_mapping_candidates(
    model: Mapping[str, Any], target: Mapping[str, Any]
) -> tuple[tuple[int, ...], ...]:
    width = model["state_width"]
    source_assignments = {
        row["target_column"]: row for row in model["known_partial_factor_assignments"]
    }
    target_assignments = {
        row["target_column"]: row for row in target["compiled_factor_assignments"]
    }

    def descriptor(assignments: Mapping[int, Mapping[str, Any]], column: int):
        row = assignments.get(column)
        return (
            ("UNKNOWN",)
            if row is None
            else ("KNOWN", row["result_type"], row["signature_sha256"])
        )

    source_groups: dict[tuple[Any, ...], list[int]] = {}
    target_groups: dict[tuple[Any, ...], list[int]] = {}
    for column in range(width):
        source_groups.setdefault(descriptor(source_assignments, column), []).append(column)
        target_groups.setdefault(descriptor(target_assignments, column), []).append(column)
    if set(source_groups) != set(target_groups) or any(
        len(source_groups[key]) != len(target_groups[key]) for key in source_groups
    ):
        return ()
    groups = sorted(source_groups, key=lambda row: canonical_json_bytes(list(row)))
    results = []
    for choices in product(
        *(permutations(target_groups[key]) for key in groups)
    ):
        mapping = [-1] * width
        for key, targets in zip(groups, choices, strict=True):
            for source_column, target_column in zip(
                source_groups[key], targets, strict=True
            ):
                mapping[source_column] = target_column
        if sorted(mapping) == list(range(width)):
            results.append(tuple(mapping))
    return tuple(results)


def _action_mapping_candidates(
    model: Mapping[str, Any],
    target: Mapping[str, Any],
    state_mapping: tuple[int, ...],
    source_applicability: tuple[int, int],
    target_applicability: tuple[int, int],
) -> tuple[tuple[int, ...], ...]:
    width = model["action_field_width"]
    source_assignments = {
        row["target_column"]: row for row in model["known_partial_factor_assignments"]
    }
    target_assignments = {
        row["target_column"]: row for row in target["compiled_factor_assignments"]
    }
    bindings: dict[int, int] = {source_applicability[1]: target_applicability[1]}
    for source_column, source_row in source_assignments.items():
        target_row = target_assignments[state_mapping[source_column]]
        source_dependencies = source_row["action_dependencies"]
        target_dependencies = target_row["action_dependencies"]
        if len(source_dependencies) != len(target_dependencies):
            return ()
        for source_field, target_field in zip(
            source_dependencies, target_dependencies, strict=True
        ):
            if source_field in bindings and bindings[source_field] != target_field:
                return ()
            bindings[source_field] = target_field
    if len(set(bindings.values())) != len(bindings):
        return ()
    source_remaining = [field for field in range(width) if field not in bindings]
    target_remaining = [field for field in range(width) if field not in bindings.values()]
    results = []
    for choice in permutations(target_remaining):
        mapping = [-1] * width
        for source_field, target_field in bindings.items():
            mapping[source_field] = target_field
        for source_field, target_field in zip(source_remaining, choice, strict=True):
            mapping[source_field] = target_field
        results.append(tuple(mapping))
    return tuple(results)


def _source_views(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    state_mapping: tuple[int, ...],
    action_mapping: tuple[int, ...],
) -> tuple[tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...]]:
    actions = tuple(
        FlatRawActionV4(
            action.key,
            tuple(action.fields[target] for target in action_mapping),
        )
        for action in catalogue
    )
    transformed = tuple(
        FlatRawTransitionV4(
            row.occurrence,
            row.index,
            tuple(row.pre[target] for target in state_mapping),
            row.legal_before,
            FlatRawActionV4(
                row.action.key,
                tuple(row.action.fields[target] for target in action_mapping),
            ),
            tuple(row.post[target] for target in state_mapping),
            row.legal_after,
            row.terminal_acceptance_after,
            row.outcome_tape_sha256,
        )
        for row in rows
    )
    return transformed, actions


def _mapping_replays(
    model: Mapping[str, Any],
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    state_mapping: tuple[int, ...],
    action_mapping: tuple[int, ...],
) -> bool:
    transformed, actions = _source_views(
        rows, catalogue, state_mapping, action_mapping
    )
    supports = {
        0: tuple(
            tuple(sorted({action.fields[field] for action in actions}))
            for field in range(model["action_field_width"])
        )
    }
    assignments = model["known_partial_factor_assignments"]
    residual_spaces = model["residual_version_spaces"]
    status_target = model["status_target_column"]
    terminal_frontier = model["mdl_minimal_terminal_candidate_frontier"]
    for row in transformed:
        if any(
            row.post[assignment["target_column"]]
            not in _partial_support(assignment, row.pre, row.action.fields)
            for assignment in assignments
        ):
            return False
        for space in residual_spaces:
            target = space["target_column"]
            for expression in space["batch_exact_candidate_frontier"]:
                prediction = _value(
                    expression["normalized_expression"],
                    row.pre,
                    row.action.fields,
                    target,
                    expression.get("action_field_binding"),
                    expression.get("anonymous_integer_constant_binding"),
                    0,
                    supports,
                )
                if row.post[target] not in prediction:
                    return False
        expected = (
            "ACTIVE"
            if row.legal_after
            else "ACCEPT"
            if row.terminal_acceptance_after is True
            else "REJECT"
        )
        for terminal in terminal_frontier:
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": terminal["decision_tree"],
                },
                row.post,
            )
            if (
                prediction.get("terminal_class") != expected
                or prediction.get("status_token") != row.post[status_target]
            ):
                return False
    return True


def compile_coordinate_alignment_v60(
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    verified = verify_projected_disagreement_model_v56(model)
    if (
        type(applicability_program) is not dict
        or applicability_program.get("schema")
        != "acfqp.generic_action_applicability_program.v58"
        or applicability_program.get("source_model_id")
        != verified["projected_disagreement_successor_model_id"]
        or applicability_program.get("training_exact") is not True
        or applicability_program.get("heldout_exact") is not True
    ):
        _fail("V60 frozen applicability template changed")
    target = target_candidate.public_document
    if (
        target.get("state_width") != verified["state_width"]
        or target.get("action_field_width") != verified["action_field_width"]
        or target.get("layout", {}).get("schema_signature")
        != verified["source_layout"].get("schema_signature")
    ):
        _fail("V60 target is not in the registered structural schema family")
    rows, actions = _canonical_rows(target_candidate, observed_rows, catalogue)
    relation = applicability_program["selected_program"]
    target_bindings, relation_evaluations = _exact_applicability_bindings(
        relation["opcode"],
        verified["state_width"],
        verified["action_field_width"],
        _applicability_examples(rows, actions),
    )
    source_applicability = (relation["state_column"], relation["action_field"])
    mappings = []
    mapping_replays = 0
    state_candidates = _state_mapping_candidates(verified, target)
    action_candidate_count = 0
    for state_mapping in state_candidates:
        for target_applicability in target_bindings:
            if state_mapping[source_applicability[0]] != target_applicability[0]:
                continue
            action_candidates = _action_mapping_candidates(
                verified,
                target,
                state_mapping,
                source_applicability,
                target_applicability,
            )
            action_candidate_count += len(action_candidates)
            for action_mapping in action_candidates:
                mapping_replays += len(rows)
                if _mapping_replays(
                    verified, rows, actions, state_mapping, action_mapping
                ):
                    mappings.append(
                        {
                            "source_state_to_target_canonical": list(state_mapping),
                            "source_action_to_target_canonical": list(action_mapping),
                            "target_applicability_state_column": target_applicability[0],
                            "target_applicability_action_field": target_applicability[1],
                        }
                    )
    unique = {canonical_json_bytes(row): row for row in mappings}
    mappings = [unique[key] for key in sorted(unique)]
    if len(mappings) != 1:
        _fail(
            "V60 observations did not identify exactly one source/target projection; "
            f"retained={len(mappings)}"
        )
    selected = mappings[0]
    payload = {
        "schema": "acfqp.generic_coordinate_alignment.v60",
        "source_model_id": verified["projected_disagreement_successor_model_id"],
        "source_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "target_partial_candidate_id": target["candidate_id"],
        "target_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in observed_rows])
        ).hexdigest(),
        "target_raw_transition_count": len(observed_rows),
        "state_width": verified["state_width"],
        "action_field_width": verified["action_field_width"],
        "source_applicability_relation_opcode": relation["opcode"],
        "target_exact_applicability_binding_count": len(target_bindings),
        "target_applicability_relation_evaluations": relation_evaluations,
        "type_compatible_state_mapping_candidate_count": len(state_candidates),
        "type_compatible_action_mapping_candidate_count": action_candidate_count,
        "full_model_replay_row_evaluations": mapping_replays,
        "exact_full_model_projection_count": 1,
        **selected,
        "alignment_derived_only_from_target_common_partial_observations": True,
        "target_episode_outcomes_used": False,
        "source_model_or_applicability_refit": False,
        "semantic_names_used": False,
        "alignment_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "coordinate_alignment_id": hashlib.sha256(
            _ALIGNMENT_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def aligned_source_views_v60(
    alignment: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> tuple[tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...]]:
    if (
        type(alignment) is not dict
        or alignment.get("schema") != "acfqp.generic_coordinate_alignment.v60"
        or alignment.get("target_partial_candidate_id")
        != target_candidate.public_document.get("candidate_id")
        or alignment.get("alignment_used_as_safety_authority") is not False
    ):
        _fail("V60 aligned-view authority changed")
    payload = {
        key: value for key, value in alignment.items() if key != "coordinate_alignment_id"
    }
    if hashlib.sha256(_ALIGNMENT_DOMAIN + canonical_json_bytes(payload)).hexdigest() != alignment.get(
        "coordinate_alignment_id"
    ):
        _fail("V60 alignment content identity changed")
    rows, actions = _canonical_rows(target_candidate, observed_rows, catalogue)
    return _source_views(
        rows,
        actions,
        tuple(alignment["source_state_to_target_canonical"]),
        tuple(alignment["source_action_to_target_canonical"]),
    )


__all__ = ("aligned_source_views_v60", "compile_coordinate_alignment_v60")
