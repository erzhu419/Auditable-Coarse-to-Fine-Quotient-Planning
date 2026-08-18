"""Exact prefix-codelength and universal-evidence stopping successor.

V11's structural ``units`` mixed observation counts with token counts.  This
module replaces that margin with an explicit two-part prefix code measured only
in bits.  The fixed acquisition policy makes query identities side information;
the raw code transmits each observed successor, successor-legality vector, and
terminal trit.  The model code transmits a complete anonymous executable
program plus one branch bit for each finite-support assignment and transition.

The prior arm may replace an assignment whose exact signature is in the frozen
factor library with a prefix-coded library index and dependency binding.  The
no-prior arm transmits that assignment's expression.  Statistical stopping is
the same parameter-free uniform-mixture e-process and telescoping epoch alpha
allocation introduced in V13, but it is now a separate gate: no conversion from
e-value bits to description units exists.
"""

from __future__ import annotations

from math import ceil, log2
from typing import Any, Mapping

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
)


def _unsigned_gamma_bits(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("unsigned prefix-code value changed")
    return 2 * (value + 1).bit_length() - 1


def _signed_gamma_bits(value: int) -> int:
    if type(value) is not int:
        raise ValueError("signed prefix-code value changed")
    zigzag = 2 * value if value >= 0 else -2 * value - 1
    return _unsigned_gamma_bits(zigzag)


def _integer_sequence_bits(values: Any) -> int:
    sequence = tuple(values)
    return _unsigned_gamma_bits(len(sequence)) + sum(
        _signed_gamma_bits(value) for value in sequence
    )


def _utf8_bits(value: str) -> int:
    raw = value.encode("utf-8")
    return _unsigned_gamma_bits(len(raw)) + 8 * len(raw)


def _ast_bits(value: Any) -> int:
    if type(value) is int:
        return 2 + _signed_gamma_bits(value)
    if type(value) is str:
        return 2 + _utf8_bits(value)
    if type(value) is list:
        return 2 + _unsigned_gamma_bits(len(value)) + sum(
            _ast_bits(item) for item in value
        )
    raise ValueError("anonymous program AST left the registered typed grammar")


def _binding_bits(binding: Mapping[str, Any]) -> int:
    constants = binding["constants"]
    relations = binding["relations"]
    status = binding["terminal_tokens"]
    return (
        _unsigned_gamma_bits(len(constants))
        + sum(_utf8_bits(key) + _signed_gamma_bits(constants[key]) for key in sorted(constants))
        + _unsigned_gamma_bits(len(relations))
        + sum(
            _utf8_bits(key)
            + _unsigned_gamma_bits(len(relations[key]))
            + sum(
                _signed_gamma_bits(left) + _signed_gamma_bits(right)
                for left, right in relations[key]
            )
            for key in sorted(relations)
        )
        + _unsigned_gamma_bits(len(status))
        + sum(_utf8_bits(key) + _signed_gamma_bits(status[key]) for key in sorted(status))
    )


def _dependency_binding_bits(classification: Mapping[str, Any]) -> int:
    return sum(
        _integer_sequence_bits(classification[key])
        for key in (
            "state_dependencies",
            "action_dependencies",
            "next_dependencies",
            "constant_dependencies",
        )
    ) + _unsigned_gamma_bits(len(classification["relation_dependencies"])) + sum(
        _utf8_bits(value) for value in classification["relation_dependencies"]
    )


def _program_description_bits(
    candidate: MDLAdaptiveJointCandidateV11,
    *,
    factor_prior_enabled: bool,
    factor_library: Mapping[str, Any],
) -> tuple[int, int]:
    program = candidate.program
    classifications = {
        row["target_column"]: row
        for row in candidate._base.public_document["assignment_classifications"]
    }
    signatures = tuple(
        row["signature_sha256"] for row in factor_library["cross_schema_subprograms"]
    )
    signature_index = {signature: index for index, signature in enumerate(signatures)}
    library_index_bits = max(1, ceil(log2(max(2, len(signatures)))))
    state_layout = tuple(candidate.layout.state_canonical_to_raw)
    action_layout = tuple(candidate.layout.action_canonical_to_raw)
    bits = (
        _unsigned_gamma_bits(len(state_layout))
        + _integer_sequence_bits(state_layout)
        + _unsigned_gamma_bits(len(action_layout))
        + _integer_sequence_bits(action_layout)
        + _ast_bits(program["legal_expression"])
        + _ast_bits(program["accept_expression"])
        + _unsigned_gamma_bits(len(program["compiled_assignments"]))
    )
    reusable_references = 0
    for assignment in program["compiled_assignments"]:
        target = assignment["target_column"]
        classification = classifications[target]
        bits += _unsigned_gamma_bits(target)
        bits += _utf8_bits(assignment["result_type"])
        signature = classification["signature_sha256"]
        if (
            factor_prior_enabled
            and classification["classification"] == "FACTORABLE_REUSABLE"
            and signature in signature_index
        ):
            bits += 1 + library_index_bits + _dependency_binding_bits(classification)
            reusable_references += 1
        else:
            bits += 1 + _ast_bits(assignment["expression"])
    bindings = program["occurrence_bindings"]
    bits += _unsigned_gamma_bits(len(bindings)) + sum(
        _binding_bits(binding) for binding in bindings
    )
    return bits, reusable_references


def _raw_outcome_bits(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return sum(
        _integer_sequence_bits(row.post)
        + _integer_sequence_bits(row.legal_after)
        + 2
        for row in rows
    )


def _model_outcome_bits(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
) -> int:
    finite_support_outputs = sum(
        row["result_type"] == "FINITE_INT_SUPPORT"
        for row in candidate.program["compiled_assignments"]
    )
    return finite_support_outputs * len(rows)


def bit_codelength_universal_stop_update_v14(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    factor_prior_enabled: bool,
    factor_library: Mapping[str, Any],
    invalidated_candidate_count: int,
    candidate_program_disagreement_count: int,
    candidate_epoch: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    if (
        invalidated_candidate_count < 0
        or candidate_program_disagreement_count < 0
        or candidate_epoch < 0
        or post_issuance_exact_prediction_success_count < 0
        or global_alpha_denominator <= 1
    ):
        raise ValueError("V14 bit-codelength stopping contract changed")
    replay = exact_candidate_replay_v11(candidate, rows, catalogue)
    replay_disagreements = sum(
        replay[key]
        for key in (
            "legality_mismatch_count",
            "support_mismatch_count",
            "terminal_mismatch_count",
            "evaluation_failure_count",
        )
    )
    program_bits, reusable_references = _program_description_bits(
        candidate,
        factor_prior_enabled=factor_prior_enabled,
        factor_library=factor_library,
    )
    raw_bits = _raw_outcome_bits(rows)
    model_outcome_bits = _model_outcome_bits(candidate, rows)
    change_count = invalidated_candidate_count + candidate_program_disagreement_count
    candidate_change_bits = _unsigned_gamma_bits(change_count)
    total_model_bits = program_bits + model_outcome_bits + candidate_change_bits
    savings_bits = raw_bits - total_model_bits
    successes = post_issuance_exact_prediction_success_count
    evalue_numerator = 2 ** (successes + 1) - 1
    evalue_denominator = successes + 1
    epoch_weight_denominator = (candidate_epoch + 1) * (candidate_epoch + 2)
    evalue_threshold = global_alpha_denominator * epoch_weight_denominator
    threshold_met = evalue_numerator >= evalue_denominator * evalue_threshold
    stopped = replay_disagreements == 0 and threshold_met and savings_bits >= 0
    return {
        "schema": "acfqp.generic_bit_codelength_universal_stop_update.v14",
        "candidate_id": candidate.public_document["candidate_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "factor_library_id": factor_library["factor_library_id"],
        "factor_library_reference_count": reusable_references,
        "raw_outcome_prefix_code_bits": raw_bits,
        "model_program_prefix_code_bits": program_bits,
        "model_outcome_branch_bits": model_outcome_bits,
        "candidate_change_prefix_code_bits": candidate_change_bits,
        "total_two_part_model_code_bits": total_model_bits,
        "two_part_codelength_savings_bits": savings_bits,
        "current_candidate_replay_disagreement_count": replay_disagreements,
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "universal_mixture_evalue_numerator": evalue_numerator,
        "universal_mixture_evalue_denominator": evalue_denominator,
        "global_alpha": {"numerator": 1, "denominator": global_alpha_denominator},
        "epoch_alpha_spending_weight": {
            "numerator": 1,
            "denominator": epoch_weight_denominator,
        },
        "evalue_threshold": evalue_threshold,
        "universal_mixture_evalue_threshold_met": threshold_met,
        "heuristic_mdl_information_units_consumed": False,
        "factor_signature_credit_units_consumed": False,
        "invalidated_candidate_penalty_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "betting_fraction_selected": False,
        "epoch_spending_base_selected": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "anytime_valid_for_registered_predictive_null": True,
        "distribution_free_global_dynamics_confidence_claimed": False,
        "stopped": stopped,
        "only_switched_variable": "FACTOR_LIBRARY_REFERENCE_CODE_AVAILABLE",
    }


def ast_prefix_bits_v14(value: Any) -> int:
    return _ast_bits(value)


def integer_sequence_prefix_bits_v14(values: Any) -> int:
    return _integer_sequence_bits(values)


def unsigned_integer_prefix_bits_v14(value: int) -> int:
    return _unsigned_gamma_bits(value)


def utf8_prefix_bits_v14(value: str) -> int:
    return _utf8_bits(value)


__all__ = (
    "ast_prefix_bits_v14",
    "bit_codelength_universal_stop_update_v14",
    "integer_sequence_prefix_bits_v14",
    "unsigned_integer_prefix_bits_v14",
    "utf8_prefix_bits_v14",
)
