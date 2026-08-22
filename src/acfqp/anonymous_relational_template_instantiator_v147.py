"""Bind V146 alpha-normalized K/R templates to observation-derived bindings."""

from __future__ import annotations

import copy
import hashlib
from itertools import product
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v147 as domains
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


BANK_ID = "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5"
BANK_BYTE_COUNT = 4_033
BANK_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
VERIFICATION_ID = "7531dcc153b64ba8c23ae70fce84650b0be0550acaf3db915b106adf2bd6e63b"
VERIFICATION_BYTE_COUNT = 1_028
VERIFICATION_SHA256 = "891b48ce7d035ea8e56f68a3e3dc6a8838cbd62dfabf7af6a86a5d81f14a7e80"


class AnonymousRelationalTemplateInstantiatorV147Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AnonymousRelationalTemplateInstantiatorV147Error(message)


def _symbols(expression: Any) -> tuple[tuple[str, int], ...]:
    result: set[tuple[str, int]] = set()

    def visit(value: Any) -> None:
        if type(value) is not list or not value:
            return
        if (
            len(value) == 2
            and value[0] in {"S", "A", "K", "R"}
            and type(value[1]) is int
        ):
            result.add((value[0], value[1]))
            return
        for item in value[1:]:
            visit(item)

    visit(expression)
    return tuple(sorted(result))


def _bind(
    expression: Any,
    *,
    target: int,
    assignment: Mapping[tuple[str, int], Any],
) -> Any:
    if type(expression) is not list or not expression:
        return expression
    if expression == ["S", "SELF"]:
        return ["E00", target]
    if len(expression) == 2 and expression[0] in {"S", "A", "K", "R"}:
        key = (expression[0], expression[1])
        if key not in assignment:
            _fail("V147 anonymous symbol lacks a binding")
        value = assignment[key]
        if expression[0] == "S":
            return ["E00", value]
        if expression[0] == "A":
            return ["E01", value]
        if expression[0] == "K":
            return ["E03", value]
        return value
    return [expression[0], *(_bind(item, target=target, assignment=assignment) for item in expression[1:])]


def _exact(
    expression: Any,
    result_type: str,
    target: int,
    rows: tuple[Any, ...],
    binding: Mapping[str, Any],
) -> tuple[bool, int]:
    checks = 0
    for row in rows:
        try:
            value = atomic._evaluate(  # noqa: SLF001
                expression,
                state=row.pre,
                next_values={},
                action=row.action,
                binding=binding,
            )
        except Exception:
            return False, checks
        checks += 1
        if result_type == "INT":
            if type(value) is not int or value != row.post[target]:
                return False, checks
        elif result_type == "FINITE_INT_SUPPORT":
            if not hasattr(value, "values") or row.post[target] not in value.values:
                return False, checks
        else:
            return False, checks
    return True, checks


def instantiate_anonymous_relational_templates_v147(
    bank_raw: bytes,
    verification_raw: bytes,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    layout: Any,
) -> dict[str, Any]:
    bank = loads_canonical_json(bank_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(bank) != bank_raw
        or len(bank_raw) != BANK_BYTE_COUNT
        or hashlib.sha256(bank_raw).hexdigest() != BANK_SHA256
        or bank.get("bank_id") != BANK_ID
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != VERIFICATION_SHA256
        or verification.get("verification_id") != VERIFICATION_ID
        or verification.get("bank_id") != BANK_ID
        or verification.get(
            "producer_free_constant_relation_and_coordinate_alpha_normalization"
        )
        is not True
        or type(rows) is not tuple
        or not rows
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V147 frozen bank, verification, or observation inventory changed")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    binding = atomic._derive_binding(aligned_rows, aligned_catalogue)  # noqa: SLF001
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    domains_by_kind = {
        "S": tuple(range(state_width)),
        "A": tuple(range(action_width)),
        "K": tuple(sorted(binding["constants"])),
        "R": tuple(sorted(binding["relations"])),
    }
    exact_rows = []
    evaluations = 0
    for template in bank["selected_subprograms"]:
        normalized = template["normalized_expression"]
        symbols = _symbols(normalized)
        choices = [domains_by_kind[kind] for kind, _index in symbols]
        if any(not choice for choice in choices):
            continue
        for values in product(*choices):
            assignment = dict(zip(symbols, values, strict=True))
            for target in range(state_width):
                expression = _bind(normalized, target=target, assignment=assignment)
                exact, checks = _exact(
                    expression,
                    template["result_type"],
                    target,
                    aligned_rows,
                    binding,
                )
                evaluations += checks
                if exact:
                    exact_rows.append(
                        {
                            "template_signature_sha256": template[
                                "signature_sha256"
                            ],
                            "target_column": target,
                            "result_type": template["result_type"],
                            "bound_expression": expression,
                            "symbol_binding": [
                                {
                                    "symbol_kind": kind,
                                    "normalized_index": index,
                                    "bound_token": assignment[(kind, index)],
                                }
                                for kind, index in symbols
                            ],
                            "dependency_tokens": [
                                list(token)
                                for token in sorted(
                                    atomic._dependency_tokens(expression)  # noqa: SLF001
                                )
                            ],
                        }
                    )
    unique = {
        canonical_json_bytes(row): row for row in exact_rows
    }
    exact_rows = [unique[key] for key in sorted(unique)]
    relational = [
        row
        for row in exact_rows
        if any(token[0] == "E04" for token in row["dependency_tokens"])
    ]
    if not relational:
        _fail("V147 found no exact anonymous finite-relation instantiation")
    payload = {
        "schema": "acfqp.anonymous_relational_template_instantiation.v147",
        "bank_id": BANK_ID,
        "bank_verification_id": VERIFICATION_ID,
        "layout_id": layout.layout_id,
        "source_raw_transition_count": len(rows),
        "source_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "bank_selected_template_count": len(bank["selected_subprograms"]),
        "bank_selected_relational_template_count": sum(
            row.get("relation_symbol_count", 0) > 0
            for row in bank["selected_subprograms"]
        ),
        "observation_derived_binding": copy.deepcopy(binding),
        "exact_instantiations": exact_rows,
        "exact_instantiation_count": len(exact_rows),
        "exact_relational_instantiation_count": len(relational),
        "template_binding_evaluation_events": evaluations,
        "constant_and_relation_symbol_names_supplied_by_bank": False,
        "target_coordinate_roles_supplied_by_bank": False,
        "binding_derived_from_raw_observations": True,
        "exact_rows_are_program_proposals_not_planning_authority": True,
        "new_target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "instantiation_id": domains.extension_content_id_v147(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_INSTANTIATION_V147_DOMAIN,
            payload,
        ),
    }


__all__ = ("instantiate_anonymous_relational_templates_v147",)
