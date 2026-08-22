"""Lower observation-derived anonymous relations into the generic V122 VM.

The source synthesizer may select ``E03`` occurrence constants and ``E04``
finite relation lookups.  Historical V121/V122 intentionally predate those
runtime atoms.  This additive compiler freezes the observed binding and lowers
it to literals plus typed equality/conditional expressions.  The resulting
carrier can therefore be replayed and planned by the unchanged historical VM.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v144 as domains
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    robust_dictionary_factor_stop_update_v131r2,
)


class GenericRelationalFactorExecutionProjectionV144Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRelationalFactorExecutionProjectionV144Error(message)


def _action_only_value(expression: Any, fields: tuple[int, ...]) -> int | bool:
    if type(expression) in {int, bool}:
        return expression
    if type(expression) is not list or not expression:
        _fail("V144 lowered relation key shape changed")
    opcode = expression[0]
    if opcode == "E01":
        index = expression[1]
        if type(index) is not int or index not in range(len(fields)):
            _fail("V144 lowered relation key used an absent action field")
        return fields[index]
    values = [_action_only_value(item, fields) for item in expression[1:]]
    if opcode == "E05":
        return int(values[0]) + int(values[1])
    if opcode == "E06":
        divisor = int(values[1])
        if divisor == 0:
            _fail("V144 lowered relation key used zero modulo divisor")
        return int(values[0]) % divisor
    if opcode == "E08":
        return values[0] == values[1]
    if opcode == "E09":
        return int(values[0]) > int(values[1])
    if opcode == "E10":
        return bool(values[0]) and bool(values[1])
    if opcode == "E11":
        return not bool(values[0])
    if opcode == "E12":
        return int(values[1]) if bool(values[0]) else int(values[2])
    if opcode == "E13":
        return int(values[0]) | int(values[1])
    _fail("V144 relation key is not action-only in the registered VM")


def _lower_expression(
    expression: Any,
    binding: Mapping[str, Any],
    catalogue: tuple[Any, ...],
) -> Any:
    if type(expression) in {int, bool}:
        return expression
    if type(expression) is not list or not expression:
        _fail("V144 relational expression shape changed")
    opcode = expression[0]
    if opcode in {"E00", "E01"}:
        if len(expression) != 2 or type(expression[1]) is not int:
            _fail("V144 causal atom shape changed")
        return list(expression)
    if opcode == "E02" or opcode == "T":
        _fail("V144 execution projection received a noncausal runtime atom")
    if opcode == "E03":
        if len(expression) != 2 or expression[1] not in binding["constants"]:
            _fail("V144 occurrence constant is absent from the frozen binding")
        return binding["constants"][expression[1]]
    if opcode == "E04":
        if len(expression) != 3:
            _fail("V144 relation lookup shape changed")
        name = expression[1]
        relation_rows = binding["relations"].get(name)
        if type(relation_rows) is not list or len(relation_rows) < 2:
            _fail("V144 relation is absent from the frozen binding")
        relation = {key: value for key, value in relation_rows}
        if len(relation) != len(relation_rows):
            _fail("V144 relation binding contains duplicate keys")
        key_expression = _lower_expression(expression[2], binding, catalogue)
        state_dependencies, _action_dependencies = _dependencies(key_expression)
        if state_dependencies:
            _fail("V144 finite relation key depends on projected runtime state")
        reachable = {
            _action_only_value(key_expression, action.fields) for action in catalogue
        }
        if reachable != set(relation):
            _fail("V144 finite relation does not cover the exact action catalogue")
        ordered = sorted(relation.items())
        lowered: Any = ordered[-1][1]
        for key, value in reversed(ordered[:-1]):
            lowered = ["E12", ["E08", copy.deepcopy(key_expression), key], value, lowered]
        return lowered
    if type(opcode) is not str or opcode not in atomic.GENERIC_ATOMIC_OPCODE_NAMES_V4:
        _fail("V144 expression used an unregistered opcode")
    return [
        opcode,
        *(
            _lower_expression(item, binding, catalogue)
            for item in expression[1:]
        ),
    ]


def compile_relational_factor_execution_projection_v144(
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
) -> PartialFactorCandidateV15:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(rows) is not tuple
        or not rows
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V144 execution projection inventory changed")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    binding = atomic._derive_binding(aligned_rows, aligned_catalogue)  # noqa: SLF001
    assignments = []
    for assignment in candidate.assignments:
        lowered = _lower_expression(
            assignment["expression"], binding, aligned_catalogue
        )
        state_dependencies, action_dependencies = _dependencies(lowered)
        assignments.append(
            {
                **copy.deepcopy(dict(assignment)),
                "expression": lowered,
                "state_dependencies": state_dependencies,
                "action_dependencies": action_dependencies,
            }
        )
    source = candidate.public_document
    payload = {
        **{
            key: copy.deepcopy(value)
            for key, value in source.items()
            if key not in {"schema", "candidate_id", "compiled_factor_assignments"}
        },
        "schema": "acfqp.relational_factor_execution_projection.v144",
        "source_relational_candidate_id": source["candidate_id"],
        "compiled_factor_assignments": assignments,
        "frozen_anonymous_binding": copy.deepcopy(binding),
        "source_raw_transition_count": len(rows),
        "source_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "occurrence_constants_lowered_to_integer_literals": True,
        "finite_relations_lowered_to_typed_conditionals": True,
        "relation_key_support_exactly_equals_action_catalogue_support": True,
        "historical_v121_v122_modules_modified": False,
        "ground_rows_required_by_planner": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {
        **payload,
        "candidate_id": domains.extension_content_id_v144(
            domains.CONSTRUCTION_K7_RELATIONAL_FACTOR_EXECUTION_PROJECTION_V144_DOMAIN,
            payload,
        ),
    }
    projected = PartialFactorCandidateV15(
        document, candidate.layout, tuple(assignments), aligned_rows
    )
    replay = exact_generic_artifact_factor_replay_v121(
        projected, rows, catalogue
    )
    if replay["exact"] is not True:
        _fail("V144 lowered execution projection is not exact on its source rows")
    return projected


def robust_relational_dictionary_factor_stop_update_v144(
    source_candidate: PartialFactorCandidateV15,
    execution_candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    *,
    factor_prior_enabled: bool,
    candidate_epoch: int,
    invalidated_candidate_count: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    if (
        execution_candidate.public_document.get("source_relational_candidate_id")
        != source_candidate.public_document.get("candidate_id")
    ):
        _fail("V144 stop update crossed source and execution candidates")
    result = robust_dictionary_factor_stop_update_v131r2(
        execution_candidate,
        rows,
        catalogue,
        factor_prior_enabled=factor_prior_enabled,
        candidate_epoch=candidate_epoch,
        invalidated_candidate_count=invalidated_candidate_count,
        post_issuance_exact_prediction_success_count=(
            post_issuance_exact_prediction_success_count
        ),
        global_alpha_denominator=global_alpha_denominator,
    )
    replay = dict(result["current_partial_factor_replay"])
    replay["source_relational_candidate_id"] = source_candidate.public_document[
        "candidate_id"
    ]
    return {
        **result,
        "schema": "acfqp.robust_relational_dictionary_factor_stop_update.v144",
        "source_relational_candidate_id": source_candidate.public_document[
            "candidate_id"
        ],
        "execution_projection_candidate_id": execution_candidate.public_document[
            "candidate_id"
        ],
        "current_partial_factor_replay": replay,
        "same_lowered_execution_projection_used_by_replay_and_planner": True,
    }


__all__ = (
    "GenericRelationalFactorExecutionProjectionV144Error",
    "compile_relational_factor_execution_projection_v144",
    "robust_relational_dictionary_factor_stop_update_v144",
)
