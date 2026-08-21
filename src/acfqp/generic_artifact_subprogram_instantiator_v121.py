"""Generic binder and evaluator for artifact-derived anonymous subprograms.

V15 recognizes three normalized expression shapes with dedicated branches.
This additive successor instead interprets a finite typed opcode registry,
discovers all symbolic state/action variables in each normalized expression,
enumerates their bindings, and evaluates the resulting expression tree.  It
still returns the historical ``PartialFactorCandidateV15`` carrier so the
frozen downstream planner can consume it; replacement of that planner's own
shape-specific execution adapter remains a later construction boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import product
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GENERIC_ATOMIC_OPCODES_V4,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    integer_sequence_prefix_bits_v14,
    unsigned_integer_prefix_bits_v14,
    utf8_prefix_bits_v14,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


OPCODE_TYPES = {
    code: (tuple(arguments), result)
    for code, _name, arguments, result in GENERIC_ATOMIC_OPCODES_V4
}
CAUSAL_FACTOR_ATOMS = frozenset({"E00", "E01"})


class GenericArtifactSubprogramInstantiatorV121Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericArtifactSubprogramInstantiatorV121Error(message)


@dataclass(frozen=True, slots=True)
class _FiniteSupportV121:
    values: tuple[int, ...]


def _symbols(expression: Any) -> tuple[tuple[str, int], ...]:
    found: set[tuple[str, int]] = set()

    def visit(item: Any) -> None:
        if type(item) is not list or not item:
            return
        if (
            len(item) == 2
            and item[0] in {"S", "A"}
            and type(item[1]) is int
            and item[1] >= 0
        ):
            found.add((item[0], item[1]))
            return
        if item == ["S", "SELF"]:
            return
        for nested in item[1:]:
            visit(nested)

    visit(expression)
    return tuple(sorted(found))


def _bind(
    expression: Any,
    target_column: int,
    assignment: Mapping[tuple[str, int], int],
) -> Any:
    if type(expression) in {int, bool}:
        return expression
    if type(expression) is not list or not expression:
        _fail("V121 normalized expression shape changed")
    if expression == ["S", "SELF"]:
        return ["E00", target_column]
    if (
        len(expression) == 2
        and expression[0] in {"S", "A"}
        and type(expression[1]) is int
    ):
        symbol = (expression[0], expression[1])
        if symbol not in assignment:
            _fail("V121 normalized symbol lacks a binding")
        return ["E00" if expression[0] == "S" else "E01", assignment[symbol]]
    if type(expression[0]) is not str or expression[0] not in OPCODE_TYPES:
        _fail("V121 normalized expression used an unknown opcode")
    return [expression[0], *(_bind(item, target_column, assignment) for item in expression[1:])]


def _type(expression: Any) -> str:
    if type(expression) is bool:
        return "BOOL"
    if type(expression) is int:
        return "INT"
    if type(expression) is not list or not expression:
        _fail("V121 bound expression shape changed")
    head = expression[0]
    if head in CAUSAL_FACTOR_ATOMS:
        if len(expression) != 2 or type(expression[1]) is not int:
            _fail("V121 causal atom shape changed")
        return "INT"
    if head not in OPCODE_TYPES:
        _fail("V121 bound expression used an unknown opcode")
    argument_types, result_type = OPCODE_TYPES[head]
    if len(expression) - 1 != len(argument_types):
        _fail("V121 opcode arity changed")
    actual = tuple(_type(item) for item in expression[1:])
    if actual != argument_types:
        _fail("V121 opcode argument type changed")
    return result_type


def _evaluate(
    expression: Any, state: tuple[int, ...], action: FlatRawActionV4
) -> int | bool | _FiniteSupportV121:
    if type(expression) in {int, bool}:
        return expression
    head = expression[0]
    if head == "E00":
        return state[expression[1]]
    if head == "E01":
        return action.fields[expression[1]]
    values = [_evaluate(item, state, action) for item in expression[1:]]
    if any(isinstance(value, _FiniteSupportV121) for value in values):
        _fail("V121 finite support escaped its registered expression boundary")
    if head == "E05":
        return int(values[0]) + int(values[1])
    if head == "E06":
        divisor = int(values[1])
        if divisor == 0:
            _fail("V121 modulo divisor is zero")
        return int(values[0]) % divisor
    if head == "E07":
        return _FiniteSupportV121(tuple(sorted({int(values[0]), int(values[1])})))
    if head == "E08":
        return values[0] == values[1]
    if head == "E09":
        return int(values[0]) > int(values[1])
    if head == "E10":
        return bool(values[0]) and bool(values[1])
    if head == "E11":
        return not bool(values[0])
    if head == "E12":
        return int(values[1]) if bool(values[0]) else int(values[2])
    if head == "E13":
        return int(values[0]) | int(values[1])
    _fail("V121 expression escaped the causal opcode evaluator")


def _support(
    expression: Any, state: tuple[int, ...], action: FlatRawActionV4
) -> tuple[int, ...]:
    value = _evaluate(expression, state, action)
    if isinstance(value, _FiniteSupportV121):
        return value.values
    if type(value) is int:
        return (value,)
    _fail("V121 factor expression did not return integer support")


def _dependencies(expression: Any) -> tuple[list[int], list[int]]:
    state: set[int] = set()
    action: set[int] = set()

    def visit(item: Any) -> None:
        if type(item) is not list or not item:
            return
        if item[0] == "E00":
            state.add(item[1])
            return
        if item[0] == "E01":
            action.add(item[1])
            return
        for nested in item[1:]:
            visit(nested)

    visit(expression)
    return sorted(state), sorted(action)


def instantiate_normalized_subprograms_v121(
    target_column: int,
    state_width: int,
    action_field_width: int,
    library: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if (
        type(target_column) is not int
        or target_column not in range(state_width)
        or state_width <= 0
        or action_field_width <= 0
        or library.get("schema")
        != "acfqp.cross_schema_factor_template_projection.v15"
        or library.get("target_slot_inventory_supplied") is not False
    ):
        _fail("V121 generic instantiation contract changed")
    result = []
    for template in library.get("cross_schema_subprograms", []):
        normalized = template.get("normalized_expression")
        symbols = _symbols(normalized)
        domains = [
            range(state_width) if kind == "S" else range(action_field_width)
            for kind, _index in symbols
        ]
        for values in product(*domains):
            binding = dict(zip(symbols, values, strict=True))
            expression = _bind(normalized, target_column, binding)
            result_type = _type(expression)
            if result_type != template.get("result_type"):
                _fail("V121 derived template result type changed")
            state_dependencies, action_dependencies = _dependencies(expression)
            result.append(
                {
                    "target_column": target_column,
                    "result_type": result_type,
                    "expression": expression,
                    "signature_sha256": template["signature_sha256"],
                    "state_dependencies": state_dependencies,
                    "action_dependencies": action_dependencies,
                    "symbol_binding": [
                        {"symbol_kind": key[0], "symbol_index": key[1], "bound_index": value}
                        for key, value in sorted(binding.items())
                    ],
                }
            )
    return tuple(result)


def synthesize_generic_artifact_factor_candidate_v121(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    factor_library: Mapping[str, Any],
    *,
    support_label_count: int,
    layout_domain: str,
    candidate_domain: str,
    candidate_content_id: Callable[[str, Any], str],
    minimum_factor_assignment_count: int,
) -> PartialFactorCandidateV15:
    if support_label_count <= 0 or not rows or not catalogue:
        _fail("V121 proposal requires nonempty raw evidence")
    layout = discover_generic_layout_v5(rows, catalogue, layout_domain=layout_domain)
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    assignments = []
    ambiguities = []
    for target in range(state_width):
        exact = []
        for assignment in instantiate_normalized_subprograms_v121(
            target, state_width, action_width, factor_library
        ):
            if all(
                row.post[target]
                in _support(assignment["expression"], row.pre, row.action)
                for row in aligned_rows
            ):
                exact.append(assignment)
        if not exact:
            continue
        exact.sort(
            key=lambda row: (
                len(canonical_json_bytes(row["expression"])),
                canonical_json_bytes(row["expression"]),
                row["signature_sha256"],
                canonical_json_bytes(row["symbol_binding"]),
            )
        )
        selected = dict(exact[0])
        selected.pop("symbol_binding")
        assignments.append(selected)
        ambiguities.append(
            {
                "target_column": target,
                "exact_template_binding_count": len(exact),
                "selection": "MIN_CANONICAL_EXPRESSION_BYTES_THEN_BYTES_THEN_SIGNATURE_THEN_BINDING",
            }
        )
    if len(assignments) < minimum_factor_assignment_count:
        _fail("V121 observations did not identify enough reusable assignments")
    payload = {
        "schema": "acfqp.generic_partial_factor_candidate.v15",
        "source_factor_library_id": factor_library["source_factor_library_id"],
        "support_label_count_at_issuance": support_label_count,
        "raw_transition_count_at_issuance": len(rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "layout": layout.to_document(),
        "state_width": state_width,
        "action_field_width": action_width,
        "compiled_factor_assignments": assignments,
        "unknown_residual_target_columns": sorted(
            set(range(state_width)) - {row["target_column"] for row in assignments}
        ),
        "binding_ambiguity_inventory": ambiguities,
        "minimum_factor_assignment_count": minimum_factor_assignment_count,
        "target_slot_inventory_supplied_by_prior": False,
        "target_bindings_derived_from_raw_observations": True,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {**payload, "candidate_id": candidate_content_id(candidate_domain, payload)}
    return PartialFactorCandidateV15(
        document, layout, tuple(assignments), aligned_rows
    )


def exact_generic_artifact_factor_replay_v121(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    aligned_rows, _ = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    mismatch_rows = []
    for row in aligned_rows:
        mismatches = [
            assignment["target_column"]
            for assignment in candidate.assignments
            if row.post[assignment["target_column"]]
            not in _support(assignment["expression"], row.pre, row.action)
        ]
        if mismatches:
            mismatch_rows.append(
                {
                    "transition_index": row.index,
                    "mismatched_target_columns": mismatches,
                }
            )
    return {
        "candidate_id": candidate.public_document["candidate_id"],
        "raw_transition_count": len(rows),
        "factor_assignment_count": len(candidate.assignments),
        "mismatch_count": len(mismatch_rows),
        "mismatch_rows": mismatch_rows,
        "exact": not mismatch_rows,
    }


def generic_artifact_factor_stop_update_v121(
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    candidate_epoch: int,
    invalidated_candidate_count: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    if (
        candidate_epoch < 0
        or invalidated_candidate_count < 0
        or post_issuance_exact_prediction_success_count < 0
        or global_alpha_denominator <= 1
    ):
        _fail("V121 stopping contract changed")
    replay = exact_generic_artifact_factor_replay_v121(
        candidate, rows, catalogue
    )
    successes = post_issuance_exact_prediction_success_count
    numerator = 2 ** (successes + 1) - 1
    denominator = successes + 1
    threshold = global_alpha_denominator * (candidate_epoch + 1) * (
        candidate_epoch + 2
    )
    targets = tuple(row["target_column"] for row in candidate.assignments)
    program_bits = (
        integer_sequence_prefix_bits_v14(candidate.layout.state_canonical_to_raw)
        + integer_sequence_prefix_bits_v14(candidate.layout.action_canonical_to_raw)
        + unsigned_integer_prefix_bits_v14(len(candidate.assignments))
    )
    for assignment in candidate.assignments:
        program_bits += (
            unsigned_integer_prefix_bits_v14(assignment["target_column"])
            + utf8_prefix_bits_v14(assignment["result_type"])
            + utf8_prefix_bits_v14(assignment["signature_sha256"])
            + integer_sequence_prefix_bits_v14(assignment["state_dependencies"])
            + integer_sequence_prefix_bits_v14(assignment["action_dependencies"])
        )
    raw_bits = sum(
        integer_sequence_prefix_bits_v14(row.post[target] for target in targets)
        for row in rows
    )
    branch_bits = sum(
        assignment["result_type"] == "FINITE_INT_SUPPORT"
        for assignment in candidate.assignments
    ) * len(rows)
    change_bits = unsigned_integer_prefix_bits_v14(invalidated_candidate_count)
    total_model_bits = program_bits + branch_bits + change_bits
    threshold_met = numerator >= denominator * threshold
    return {
        "schema": "acfqp.generic_artifact_factor_stop_update.v121",
        "candidate_id": candidate.public_document["candidate_id"],
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "universal_mixture_evalue_numerator": numerator,
        "universal_mixture_evalue_denominator": denominator,
        "evalue_threshold": threshold,
        "universal_mixture_evalue_threshold_met": threshold_met,
        "current_partial_factor_replay": replay,
        "partial_prediction_target_columns": list(targets),
        "raw_partial_outcome_prefix_code_bits": raw_bits,
        "partial_program_prefix_code_bits": program_bits,
        "partial_model_outcome_branch_bits": branch_bits,
        "candidate_change_prefix_code_bits": change_bits,
        "total_partial_two_part_model_code_bits": total_model_bits,
        "partial_two_part_codelength_savings_bits": raw_bits - total_model_bits,
        "generic_symbol_binding_and_opcode_interpretation_used": True,
        "hand_written_normalized_expression_shape_cases": 0,
        "legacy_shape_specific_planner_execution_adapter_present": True,
        "unknown_residual_outputs_transmitted_or_claimed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
        "stopped": replay["exact"] is True
        and threshold_met
        and raw_bits >= total_model_bits,
    }


__all__ = (
    "exact_generic_artifact_factor_replay_v121",
    "generic_artifact_factor_stop_update_v121",
    "instantiate_normalized_subprograms_v121",
    "synthesize_generic_artifact_factor_candidate_v121",
)
