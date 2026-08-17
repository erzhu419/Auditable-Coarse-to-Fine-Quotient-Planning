"""Adaptive full-program synthesis with one anonymous factor-prior switch.

The first candidate is synthesized jointly from raw transitions: layout,
every output assignment, legality, terminal behavior, and the subsequent
factorable/residual classification.  No scaffold or target-slot list is an
input.  Both experimental arms use this same candidate, exact replay
likelihood, evidence-block multiplier, threshold, and query order.  The only
switch is the initial weight granted to already registered anonymous factor
signatures.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    execute_generic_atomic_support_v4,
    is_accepting_state_v4,
    legal_action_keys_v4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    align_generic_occurrence_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericAdaptiveJointFactorResidualSynthesizerV10Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAdaptiveJointFactorResidualSynthesizerV10Error(message)


def _layout(document: Mapping[str, Any]) -> DiscoveredLayoutV5:
    return DiscoveredLayoutV5(
        tuple(document["state_canonical_to_raw"]),
        tuple(document["action_canonical_to_raw"]),
        tuple(document["state_structural_colors"]),
        tuple(document["action_structural_colors"]),
        document["schema_signature"],
        document["refinement_rounds"],
        document["relation_evaluations"],
        document["layout_id"],
        document["reference_layout_id"],
        document["graph_edit_score"],
        document["cross_occurrence_value_overlap"],
    )


def _grouped_supports(
    rows: tuple[FlatRawTransitionV4, ...],
) -> dict[tuple[tuple[int, ...], int], set[tuple[int, ...]]]:
    grouped: dict[tuple[tuple[int, ...], int], set[tuple[int, ...]]] = {}
    for row in rows:
        grouped.setdefault((row.pre, row.action.key), set()).add(row.post)
    return grouped


@dataclass(frozen=True, slots=True)
class AdaptiveJointCandidateV10:
    public_document: Mapping[str, Any]
    model: Mapping[str, Any]
    program: Mapping[str, Any]
    layout: DiscoveredLayoutV5
    issuance_rows: tuple[FlatRawTransitionV4, ...]


def synthesize_adaptive_joint_candidate_v10(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    factor_library: Mapping[str, Any],
    *,
    support_label_count: int,
    generic_domains: Mapping[str, str],
    candidate_domain: str,
    candidate_content_id: Callable[[str, Any], str],
    minimum_reusable_factor_count: int,
) -> AdaptiveJointCandidateV10:
    if support_label_count <= 0 or not rows or not catalogue:
        _fail("adaptive joint synthesis requires nonempty raw evidence")
    if set(generic_domains) != {"layout", "program", "support", "model"}:
        _fail("adaptive joint generic-domain inventory changed")
    model = synthesize_joint_factor_residual_world_model_v9(
        {0: rows},
        {0: catalogue},
        factor_library,
        layout_domain=generic_domains["layout"],
        program_domain=generic_domains["program"],
        support_domain=generic_domains["support"],
        factor_domain=generic_domains["model"],
        result_domain=generic_domains["model"],
        minimum_reusable_factor_count=minimum_reusable_factor_count,
    )
    if model["transfer_admitted"] is not True:
        _fail("adaptive candidate did not meet the anonymous reuse threshold")
    if model["residual_schema_bound_count"] < 1:
        _fail("adaptive candidate omitted the schema-bound residual")
    program = model["target_world_model"]["compiled_program"]
    layouts = model["target_world_model"]["layout_factorization_documents"]
    if len(layouts) != 1 or layouts[0]["occurrence"] != 0:
        _fail("adaptive candidate layout cardinality changed")
    layout = _layout(layouts[0])
    classifications = [
        {
            key: row[key]
            for key in (
                "target_column",
                "result_type",
                "classification",
                "signature_sha256",
                "state_dependencies",
                "action_dependencies",
                "next_dependencies",
                "constant_dependencies",
                "relation_dependencies",
                "used_opcodes",
            )
        }
        for row in model["assignment_classifications"]
    ]
    payload = {
        "schema": "acfqp.generic_adaptive_joint_candidate.v10",
        "support_label_count_at_issuance": support_label_count,
        "raw_transition_count_at_issuance": len(rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "factor_library_id": factor_library.get("factor_library_id"),
        "joint_model_id": model["joint_model_id"],
        "program_id": program["program_id"],
        "layout": layout.to_document(),
        "assignment_classifications": classifications,
        "factorable_reusable_count": model["factorable_reusable_count"],
        "factorable_novel_count": model["factorable_novel_count"],
        "residual_schema_bound_count": model["residual_schema_bound_count"],
        "complete_program_synthesized_before_classification": True,
        "shared_residual_scaffold_consumed": False,
        "predeclared_reusable_factor_slots_consumed": False,
        "caller_selected_target_columns": [],
        "semantic_names_used": False,
    }
    document = {
        **payload,
        "candidate_id": candidate_content_id(candidate_domain, payload),
    }
    return AdaptiveJointCandidateV10(document, model, program, layout, rows)


def exact_candidate_replay_v10(
    candidate: AdaptiveJointCandidateV10,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    binding = candidate.program["occurrence_bindings"][0]
    grouped = _grouped_supports(aligned_rows)
    by_pair = {
        (row.pre, row.action.key): row for row in aligned_rows
    }
    legality_mismatches = 0
    support_mismatches = 0
    terminal_mismatches = 0
    evaluation_failures = 0
    for pair, actual_support in grouped.items():
        row = by_pair[pair]
        try:
            if (
                legal_action_keys_v4(
                    candidate.program, row.pre, aligned_catalogue, binding
                )
                != row.legal_before
            ):
                legality_mismatches += 1
            predicted = set(
                execute_generic_atomic_support_v4(
                    candidate.program, row.pre, row.action, binding
                )
            )
            if predicted != actual_support:
                support_mismatches += 1
        except Exception:
            evaluation_failures += 1
    for row in aligned_rows:
        if row.terminal_acceptance_after is None:
            continue
        try:
            if is_accepting_state_v4(
                candidate.program, row.post, binding
            ) is not row.terminal_acceptance_after:
                terminal_mismatches += 1
        except Exception:
            evaluation_failures += 1
    exact = not any(
        (
            legality_mismatches,
            support_mismatches,
            terminal_mismatches,
            evaluation_failures,
        )
    )
    return {
        "exact": exact,
        "legality_mismatch_count": legality_mismatches,
        "support_mismatch_count": support_mismatches,
        "terminal_mismatch_count": terminal_mismatches,
        "evaluation_failure_count": evaluation_failures,
        "evaluated_state_action_count": len(grouped),
    }


def adaptive_stop_update_v10(
    candidate: AdaptiveJointCandidateV10,
    *,
    factor_prior_enabled: bool,
    confirming_support_labels: int,
    confirmation_block_size: int,
    factor_prior_weight: int,
    exact_likelihood_block_weight: int,
    stopping_weight: int,
    minimum_reusable_factor_count: int,
) -> dict[str, Any]:
    if (
        confirming_support_labels < 0
        or confirmation_block_size <= 0
        or factor_prior_weight <= 1
        or exact_likelihood_block_weight <= 1
        or stopping_weight <= 1
    ):
        _fail("adaptive stopping contract changed")
    reusable = candidate.public_document["factorable_reusable_count"]
    prior_multiplier = (
        factor_prior_weight
        if factor_prior_enabled and reusable >= minimum_reusable_factor_count
        else 1
    )
    complete_blocks = confirming_support_labels // confirmation_block_size
    likelihood_multiplier = exact_likelihood_block_weight**complete_blocks
    weight = prior_multiplier * likelihood_multiplier
    return {
        "schema": "acfqp.generic_adaptive_joint_stop_update.v10",
        "candidate_id": candidate.public_document["candidate_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "factor_prior_multiplier": prior_multiplier,
        "confirming_support_labels": confirming_support_labels,
        "confirmation_block_size": confirmation_block_size,
        "complete_exact_likelihood_blocks": complete_blocks,
        "exact_likelihood_block_weight": exact_likelihood_block_weight,
        "posterior_weight": weight,
        "stopping_weight": stopping_weight,
        "stopped": weight >= stopping_weight,
        "same_formula_in_both_arms": True,
        "only_switched_variable": "ANONYMOUS_FACTOR_SIGNATURE_INITIAL_WEIGHT",
    }


__all__ = (
    "AdaptiveJointCandidateV10",
    "GenericAdaptiveJointFactorResidualSynthesizerV10Error",
    "adaptive_stop_update_v10",
    "exact_candidate_replay_v10",
    "synthesize_adaptive_joint_candidate_v10",
)
