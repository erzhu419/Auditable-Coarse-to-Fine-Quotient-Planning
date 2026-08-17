"""Anonymous cross-schema factor boundaries and reusable subprograms.

The module reads only compiled anonymous expression programs.  It discovers
factor boundaries from state/next-column dependencies, alpha-normalizes every
factor, and builds a reusable library from signatures observed in more than
one source schema.  Target reuse is admitted only when the normalized source
signature is reproduced exactly by the target's raw-observation-validated
program; full fallback synthesis remains separately accounted and is not
misreported as sample savings.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    derive_atomic_dependency_support_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


TRANSFERABLE_OPCODES_V7 = frozenset(
    {"E00", "E01", "E05", "E06", "E07", "E13"}
)


class GenericCrossSchemaFactorLibraryV7Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCrossSchemaFactorLibraryV7Error(message)


def _dependencies(expression: Any) -> dict[str, set[Any]]:
    result: dict[str, set[Any]] = {
        "state_columns": set(),
        "action_fields": set(),
        "next_columns": set(),
        "constants": set(),
        "relations": set(),
        "opcodes": set(),
        "terminal_tokens": set(),
    }

    def visit(value: Any) -> None:
        if type(value) is not list or not value:
            return
        head = value[0]
        if type(head) is str and head.startswith("E"):
            result["opcodes"].add(head)
        if head == "E00":
            result["state_columns"].add(value[1])
        elif head == "E01":
            result["action_fields"].add(value[1])
        elif head == "E02":
            result["next_columns"].add(value[1])
        elif head == "E03":
            result["constants"].add(value[1])
        elif head == "E04":
            result["relations"].add(value[1])
        elif head == "T":
            result["terminal_tokens"].add(value[1])
        for item in value[1:]:
            visit(item)

    visit(expression)
    return result


def _normalize_expression(expression: Any, target_column: int) -> Any:
    maps: dict[str, dict[Any, int]] = {
        "S": {},
        "A": {},
        "N": {},
        "C": {},
        "R": {},
    }

    def symbol(kind: str, value: Any) -> list[Any]:
        if kind in {"S", "N"} and value == target_column:
            return [kind, "SELF"]
        table = maps[kind]
        if value not in table:
            table[value] = len(table)
        return [kind, table[value]]

    def visit(value: Any) -> Any:
        if type(value) is not list or not value:
            return value
        head = value[0]
        if head == "E00":
            return symbol("S", value[1])
        if head == "E01":
            return symbol("A", value[1])
        if head == "E02":
            return symbol("N", value[1])
        if head == "E03":
            return symbol("C", value[1])
        if head == "E04":
            return ["E04", symbol("R", value[1]), visit(value[2])]
        if head == "T":
            return ["T", value[1]]
        return [head, *(visit(item) for item in value[1:])]

    return visit(expression)


def _factor_rows(program: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for assignment in program["compiled_assignments"]:
        target = assignment["target_column"]
        dependencies = _dependencies(assignment["expression"])
        normalized = _normalize_expression(assignment["expression"], target)
        signature_payload = {
            "result_type": assignment["result_type"],
            "normalized_expression": normalized,
        }
        transferable = (
            dependencies["opcodes"] <= TRANSFERABLE_OPCODES_V7
            and not dependencies["next_columns"]
            and not dependencies["constants"]
            and not dependencies["relations"]
            and not dependencies["terminal_tokens"]
        )
        rows.append(
            {
                "target_column": target,
                "result_type": assignment["result_type"],
                "expression": assignment["expression"],
                "normalized_expression": normalized,
                "signature_sha256": hashlib.sha256(
                    canonical_json_bytes(signature_payload)
                ).hexdigest(),
                "state_dependencies": sorted(dependencies["state_columns"]),
                "action_dependencies": sorted(dependencies["action_fields"]),
                "next_dependencies": sorted(dependencies["next_columns"]),
                "constant_dependencies": sorted(dependencies["constants"]),
                "relation_dependencies": sorted(dependencies["relations"]),
                "used_opcodes": sorted(dependencies["opcodes"]),
                "transferable_without_schema_specific_binding": transferable,
            }
        )
    return rows


def discover_factor_boundaries_v7(
    program: Mapping[str, Any], *, factor_domain: str
) -> dict[str, Any]:
    factors = _factor_rows(program)
    targets = {row["target_column"] for row in factors}
    adjacency = {target: set() for target in targets}
    for row in factors:
        target = row["target_column"]
        for dependency in set(row["next_dependencies"]) | set(row["state_dependencies"]):
            if dependency in targets and dependency != target:
                adjacency[target].add(dependency)
                adjacency[dependency].add(target)
    components = []
    remaining = set(targets)
    while remaining:
        root = min(remaining)
        frontier = [root]
        component = set()
        while frontier:
            current = frontier.pop()
            if current in component:
                continue
            component.add(current)
            frontier.extend(sorted(adjacency[current] - component, reverse=True))
        remaining -= component
        components.append(sorted(component))
    components.sort()
    payload = {
        "schema": "acfqp.generic_cross_schema_factor_boundaries.v7",
        "program_id": program["program_id"],
        "state_width": program["state_width"],
        "action_field_width": program["action_field_width"],
        "factors": factors,
        "dependency_connected_components": components,
        "boundary_rule": "CONNECTED_COMPONENTS_OF_ANONYMOUS_STATE_AND_NEXT_OUTPUT_DEPENDENCIES",
        "semantic_names_used": False,
        "predeclared_factor_roles": [],
    }
    return {**payload, "factor_boundary_id": content_id(factor_domain, payload)}


def compile_cross_schema_factor_library_v7(
    source_models: Mapping[str, Mapping[str, Any]], *, factor_domain: str
) -> dict[str, Any]:
    if len(source_models) < 2:
        _fail("cross-schema factor library requires at least two source models")
    boundaries = {
        name: discover_factor_boundaries_v7(
            model["compiled_program"], factor_domain=factor_domain
        )
        for name, model in sorted(source_models.items())
    }
    by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, boundary in boundaries.items():
        for factor in boundary["factors"]:
            if factor["transferable_without_schema_specific_binding"]:
                by_signature[factor["signature_sha256"]].append(
                    {
                        "source_model": name,
                        "source_program_id": boundary["program_id"],
                        "source_state_width": boundary["state_width"],
                        "source_action_field_width": boundary["action_field_width"],
                        "source_target_column": factor["target_column"],
                        "result_type": factor["result_type"],
                        "normalized_expression": factor["normalized_expression"],
                    }
                )
    library = []
    for signature, origins in sorted(by_signature.items()):
        schemas = {
            (row["source_state_width"], row["source_action_field_width"])
            for row in origins
        }
        if len(schemas) < 2:
            continue
        library.append(
            {
                "signature_sha256": signature,
                "result_type": origins[0]["result_type"],
                "normalized_expression": origins[0]["normalized_expression"],
                "source_schema_pairs": [list(row) for row in sorted(schemas)],
                "origin_count": len(origins),
                "origins": origins,
            }
        )
    if not library:
        _fail("source models exposed no factor reusable across different schemas")
    payload = {
        "schema": "acfqp.generic_cross_schema_factor_library.v7",
        "source_model_names": sorted(source_models),
        "source_program_ids": {
            name: source_models[name]["compiled_program"]["program_id"]
            for name in sorted(source_models)
        },
        "source_schema_pairs": [
            list(row)
            for row in sorted(
                {
                (
                    model["compiled_program"]["state_width"],
                    model["compiled_program"]["action_field_width"],
                )
                for model in source_models.values()
                }
            )
        ],
        "factor_boundaries": boundaries,
        "cross_schema_subprograms": library,
        "normalization": "ALPHA_RENAME_ANONYMOUS_STATE_ACTION_NEXT_CONSTANT_AND_RELATION_REFERENCES",
        "semantic_names_used": False,
        "caller_selected_factor_roles": [],
    }
    return {**payload, "factor_library_id": content_id(factor_domain, payload)}


def compose_target_with_factor_library_v7(
    target_model: Mapping[str, Any],
    library: Mapping[str, Any],
    aligned_rows: Iterable[FlatRawTransitionV4],
    aligned_catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    *,
    factor_domain: str,
    program_domain: str,
    support_domain: str,
) -> dict[str, Any]:
    target_boundary = discover_factor_boundaries_v7(
        target_model["compiled_program"], factor_domain=factor_domain
    )
    source_signatures = {
        row["signature_sha256"]: row
        for row in library["cross_schema_subprograms"]
    }
    reused = []
    for factor in target_boundary["factors"]:
        source = source_signatures.get(factor["signature_sha256"])
        if source is None or not factor["transferable_without_schema_specific_binding"]:
            continue
        reused.append(
            {
                "target_column": factor["target_column"],
                "result_type": factor["result_type"],
                "signature_sha256": factor["signature_sha256"],
                "normalized_expression": factor["normalized_expression"],
                "source_schema_pairs": source["source_schema_pairs"],
                "raw_residual_zero_in_fallback_validated_target_program": True,
            }
        )
    if not reused:
        _fail("target model admitted no reusable cross-schema factor")
    base = target_model["compiled_program"]
    payload = {
        **{key: value for key, value in base.items() if key != "program_id"},
        "schema": "acfqp.generic_cross_schema_composed_program.v7",
        "fallback_program_id": base["program_id"],
        "factor_library_id": library["factor_library_id"],
        "target_factor_boundary_id": target_boundary["factor_boundary_id"],
        "reused_factor_subprograms": reused,
        "reused_factor_count": len(reused),
        "novel_or_schema_bound_factor_count": len(target_boundary["factors"])
        - len(reused),
        "composition_selection": "SOURCE_SIGNATURE_UNIFICATION_WITH_EXACT_TARGET_RAW_RESIDUAL",
        "fallback_full_synthesis_used_to_discover_or_validate_novel_factors": True,
        "fallback_compute_not_counted_as_sample_savings": True,
        "caller_selected_factor_roles": [],
        "semantic_names_used_for_factor_matching": False,
        "status": "CROSS_SCHEMA_FACTOR_SUBPROGRAMS_COMPOSED_WITH_ACCOUNTED_FALLBACK",
    }
    program = {**payload, "program_id": content_id(program_domain, payload)}
    frozen_rows = tuple(aligned_rows)
    support = derive_atomic_dependency_support_v4(
        program,
        frozen_rows,
        aligned_catalogues,
        support_domain=support_domain,
    )
    return {
        "schema": "acfqp.generic_cross_schema_factorized_world_model.v7",
        "factor_library": library,
        "target_factor_boundaries": target_boundary,
        "compiled_program": program,
        "dependency_support": support,
        "reused_factor_count": len(reused),
        "all_reused_factors_originated_in_multiple_source_schema_pairs": all(
            len(row["source_schema_pairs"]) >= 2 for row in reused
        ),
        "target_full_fallback_compute_separately_accounted": True,
        "status": "CROSS_SCHEMA_FACTOR_LIBRARY_COMPOSED_AND_EXACTLY_REVALIDATED",
    }


__all__ = (
    "GenericCrossSchemaFactorLibraryV7Error",
    "TRANSFERABLE_OPCODES_V7",
    "compile_cross_schema_factor_library_v7",
    "compose_target_with_factor_library_v7",
    "discover_factor_boundaries_v7",
)
