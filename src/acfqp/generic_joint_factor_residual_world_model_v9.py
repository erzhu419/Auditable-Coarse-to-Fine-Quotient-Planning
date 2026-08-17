"""Joint anonymous discovery of reusable factors and schema-bound residuals.

The only reusable input is an anonymous signature library.  The target program
is synthesized in full from raw transitions before any assignment is compared
with that library.  No target scaffold, target program, selected target column,
or reusable-slot inventory is accepted by this API.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_cross_schema_factor_library_v7 import (
    discover_factor_boundaries_v7,
)
from acfqp.generic_layout_factorized_world_model_v6 import (
    synthesize_layout_factorized_world_model_v6,
)
from acfqp.phase3e_ids import content_id


class GenericJointFactorResidualWorldModelV9Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericJointFactorResidualWorldModelV9Error(message)


def synthesize_joint_factor_residual_world_model_v9(
    rows_by_occurrence: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    factor_library: Mapping[str, Any],
    *,
    layout_domain: str,
    program_domain: str,
    support_domain: str,
    factor_domain: str,
    result_domain: str,
    minimum_reusable_factor_count: int,
) -> dict[str, Any]:
    """Synthesize a complete program, then classify every inferred output.

    Classification is a consequence of each compiled expression's anonymous
    dependency graph.  Library membership is checked only after exact target
    synthesis and therefore cannot nominate target slots or supply residual
    expressions.
    """

    if minimum_reusable_factor_count <= 0:
        _fail("minimum reusable-factor count must be positive")
    if not rows_by_occurrence or set(rows_by_occurrence) != set(catalogues):
        _fail("joint synthesis occurrence inventory changed")
    library_rows = factor_library.get("cross_schema_subprograms")
    if type(library_rows) is not list or not library_rows:
        _fail("joint synthesis requires a nonempty anonymous factor library")
    if any(
        type(row) is not dict
        or type(row.get("signature_sha256")) is not str
        or len(row["signature_sha256"]) != 64
        for row in library_rows
    ):
        _fail("anonymous factor-library signature inventory changed")

    target_model = synthesize_layout_factorized_world_model_v6(
        rows_by_occurrence,
        catalogues,
        layout_domain=layout_domain,
        program_domain=program_domain,
        support_domain=support_domain,
    )
    program = target_model["compiled_program"]
    boundary = discover_factor_boundaries_v7(
        program, factor_domain=factor_domain
    )
    source_signatures = {
        row["signature_sha256"]: row for row in library_rows
    }
    classifications = []
    for factor in sorted(boundary["factors"], key=lambda row: row["target_column"]):
        transferable = factor["transferable_without_schema_specific_binding"]
        source = source_signatures.get(factor["signature_sha256"])
        if not transferable:
            classification = "RESIDUAL_SCHEMA_BOUND"
        elif source is None:
            classification = "FACTORABLE_NOVEL"
        else:
            classification = "FACTORABLE_REUSABLE"
        classifications.append(
            {
                "target_column": factor["target_column"],
                "result_type": factor["result_type"],
                "classification": classification,
                "signature_sha256": factor["signature_sha256"],
                "normalized_expression": factor["normalized_expression"],
                "state_dependencies": factor["state_dependencies"],
                "action_dependencies": factor["action_dependencies"],
                "next_dependencies": factor["next_dependencies"],
                "constant_dependencies": factor["constant_dependencies"],
                "relation_dependencies": factor["relation_dependencies"],
                "used_opcodes": factor["used_opcodes"],
                "source_schema_pairs": []
                if source is None
                else source["source_schema_pairs"],
                "classification_derived_after_full_target_synthesis": True,
            }
        )
    reusable_count = sum(
        row["classification"] == "FACTORABLE_REUSABLE"
        for row in classifications
    )
    residual_count = sum(
        row["classification"] == "RESIDUAL_SCHEMA_BOUND"
        for row in classifications
    )
    if residual_count == 0:
        _fail("joint synthesis did not expose a schema-bound residual")
    transfer_admitted = reusable_count >= minimum_reusable_factor_count
    payload = {
        "schema": "acfqp.generic_joint_factor_residual_world_model.v9",
        "factor_library_id": factor_library.get("factor_library_id"),
        "compiled_target_program_id": program["program_id"],
        "target_factor_boundary_id": boundary["factor_boundary_id"],
        "complete_target_program_synthesized_from_raw_observations": True,
        "v51_target_program_consumed": False,
        "shared_residual_scaffold_consumed": False,
        "predeclared_reusable_factor_slots_consumed": False,
        "caller_selected_target_columns": [],
        "assignment_classifications": classifications,
        "factorable_reusable_count": reusable_count,
        "factorable_novel_count": sum(
            row["classification"] == "FACTORABLE_NOVEL"
            for row in classifications
        ),
        "residual_schema_bound_count": residual_count,
        "minimum_reusable_factor_count": minimum_reusable_factor_count,
        "transfer_admitted": transfer_admitted,
        "selection_order": "FULL_EXACT_RAW_SYNTHESIS_THEN_DEPENDENCY_CLASSIFICATION_THEN_SIGNATURE_MATCH",
        "semantic_names_used": False,
        "status": (
            "JOINT_FACTOR_RESIDUAL_PROGRAM_DISCOVERED_AND_TRANSFER_ADMITTED"
            if transfer_admitted
            else "JOINT_PROGRAM_DISCOVERED_STRICT_OOD_NO_TRANSFER"
        ),
    }
    result = {**payload, "joint_model_id": content_id(result_domain, payload)}
    return {
        **result,
        "target_world_model": target_model,
        "target_factor_boundaries": boundary,
    }


__all__ = (
    "GenericJointFactorResidualWorldModelV9Error",
    "synthesize_joint_factor_residual_world_model_v9",
)
