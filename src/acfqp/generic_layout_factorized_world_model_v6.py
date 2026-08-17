"""V50r1 successor excluding terminal self-next dependencies.

V5 remains frozen with the failed V50 predecessor.  This additive successor
keeps its layout factorization and atomic assignments, but independently
re-derives the terminal decision tree from predicates whose NEXT_COLUMN leaf
cannot reference the status column being assigned.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from itertools import combinations
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    derive_atomic_dependency_support_v4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_v5,
    synthesize_layout_factorized_world_model_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


SAFE_TERMINAL_TREE_MAX_DEPTH_V6 = 3
SAFE_TERMINAL_TREE_BEAM_WIDTH_V6 = 32


class GenericLayoutFactorizedWorldModelV6Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericLayoutFactorizedWorldModelV6Error(message)


def _predicate_value(expression: Any, row: FlatRawTransitionV4) -> bool:
    head = expression[0]
    if head in {"E08", "E09"}:
        next_column = expression[1][1]
        state_column = expression[2][1]
        if head == "E08":
            return row.post[next_column] == row.pre[state_column]
        return row.post[next_column] > row.pre[state_column]
    if head == "E11":
        return not _predicate_value(expression[1], row)
    if head == "E10":
        return _predicate_value(expression[1], row) and _predicate_value(
            expression[2], row
        )
    _fail("safe terminal predicate escaped its finite grammar")


def _used_opcodes(expression: Any) -> set[str]:
    result: set[str] = set()
    if type(expression) is list:
        if expression and type(expression[0]) is str and expression[0].startswith("E"):
            result.add(expression[0])
        for item in expression:
            result.update(_used_opcodes(item))
    return result


def _contains_self_next(expression: Any, status_column: int) -> bool:
    if type(expression) is not list:
        return False
    return (
        len(expression) == 2
        and expression[0] == "E02"
        and expression[1] == status_column
    ) or any(_contains_self_next(item, status_column) for item in expression)


def _safe_status_tree(
    status_column: int,
    grouped_rows: Mapping[int, tuple[FlatRawTransitionV4, ...]],
) -> tuple[Any, int, int]:
    observations = tuple(
        (occurrence, row)
        for occurrence, rows in sorted(grouped_rows.items())
        for row in rows
    )
    labels = tuple(
        "A"
        if row.terminal_acceptance_after is None
        else "S"
        if row.terminal_acceptance_after
        else "F"
        for _occurrence, row in observations
    )
    state_width = len(observations[0][1].pre)
    atoms = []
    for next_column in range(state_width):
        if next_column == status_column:
            continue
        for state_column in range(state_width):
            atoms.append(["E08", ["E02", next_column], ["E00", state_column]])
            atoms.append(["E09", ["E02", next_column], ["E00", state_column]])
    signatures: dict[tuple[bool, ...], Any] = {}
    evaluations = 0

    def retain(signature: tuple[bool, ...], expression: Any) -> None:
        if all(signature) or not any(signature):
            return
        incumbent = signatures.get(signature)
        score = (len(canonical_json_bytes(expression)), canonical_json_bytes(expression))
        if incumbent is None or score < (
            len(canonical_json_bytes(incumbent)),
            canonical_json_bytes(incumbent),
        ):
            signatures[signature] = expression

    atomic_rows = []
    for expression in atoms:
        signature = tuple(_predicate_value(expression, row) for _, row in observations)
        evaluations += len(observations)
        retain(signature, expression)
        atomic_rows.append((signature, expression))
    atomic_rows = [
        (signature, expression)
        for signature, expression in signatures.items()
        if expression[:1] in (["E08"], ["E09"])
    ]
    for signature, expression in atomic_rows:
        retain(tuple(not value for value in signature), ["E11", expression])
    for (left_signature, left), (right_signature, right) in combinations(
        atomic_rows, 2
    ):
        retain(
            tuple(
                a and b
                for a, b in zip(left_signature, right_signature, strict=True)
            ),
            ["E10", left, right],
        )
    predicates = list(signatures.items())

    @lru_cache(maxsize=None)
    def solve(indices: tuple[int, ...], depth: int) -> Any | None:
        selected_labels = {labels[index] for index in indices}
        if len(selected_labels) == 1:
            return ["T", next(iter(selected_labels))]
        if depth == 0:
            return None
        ranked = []
        for signature, predicate in predicates:
            truth = tuple(index for index in indices if signature[index])
            falsehood = tuple(index for index in indices if not signature[index])
            if not truth or not falsehood:
                continue
            impurity = 0
            for branch in (truth, falsehood):
                counts = Counter(labels[index] for index in branch)
                impurity += len(branch) - max(counts.values())
            encoded = canonical_json_bytes(predicate)
            ranked.append(
                (
                    impurity,
                    abs(len(truth) - len(falsehood)),
                    len(encoded),
                    encoded,
                    predicate,
                    truth,
                    falsehood,
                )
            )
        for _impurity, _balance, _size, _encoded, predicate, truth, falsehood in sorted(
            ranked
        )[:SAFE_TERMINAL_TREE_BEAM_WIDTH_V6]:
            left = solve(truth, depth - 1)
            if left is None:
                continue
            right = solve(falsehood, depth - 1)
            if right is None:
                continue
            return ["E12", predicate, left, right]
        return None

    expression = solve(tuple(range(len(observations))), SAFE_TERMINAL_TREE_MAX_DEPTH_V6)
    if expression is None:
        _fail("no exact terminal tree remained after self-next exclusion")
    if _contains_self_next(expression, status_column):  # pragma: no cover
        raise AssertionError
    for index, (_occurrence, row) in enumerate(observations):
        current = expression
        while current[0] == "E12":
            current = current[2] if _predicate_value(current[1], row) else current[3]
        if current != ["T", labels[index]]:
            _fail("safe terminal tree residual changed")
    return expression, len(predicates), evaluations


def synthesize_layout_factorized_world_model_v6(
    rows_by_occurrence: Mapping[int, tuple[FlatRawTransitionV4, ...]],
    catalogues: Mapping[int, tuple[FlatRawActionV4, ...]],
    *,
    layout_domain: str,
    program_domain: str,
    support_domain: str,
) -> dict[str, Any]:
    predecessor = synthesize_layout_factorized_world_model_v5(
        rows_by_occurrence,
        catalogues,
        layout_domain=layout_domain,
        program_domain=program_domain,
        support_domain=support_domain,
    )
    ordered = sorted(rows_by_occurrence)
    reference = discover_generic_layout_v5(
        rows_by_occurrence[ordered[0]],
        catalogues[ordered[0]],
        layout_domain=layout_domain,
    )
    grouped: dict[int, tuple[FlatRawTransitionV4, ...]] = {}
    aligned_catalogues = {}
    for canonical_occurrence, occurrence in enumerate(ordered):
        layout = (
            reference
            if occurrence == ordered[0]
            else match_generic_layout_v5(
                rows_by_occurrence[ordered[0]],
                catalogues[ordered[0]],
                reference,
                rows_by_occurrence[occurrence],
                catalogues[occurrence],
                layout_domain=layout_domain,
            )
        )
        rows, catalogue = align_generic_occurrence_v5(
            rows_by_occurrence[occurrence],
            catalogues[occurrence],
            layout,
            canonical_occurrence=canonical_occurrence,
        )
        grouped[canonical_occurrence] = rows
        aligned_catalogues[canonical_occurrence] = catalogue
    program = predecessor["compiled_program"]
    status_columns = {
        row["status_column"] for row in program["occurrence_bindings"]
    }
    if len(status_columns) != 1:
        _fail("safe terminal source status projection changed")
    status_column = next(iter(status_columns))
    expression, predicate_count, evaluations = _safe_status_tree(
        status_column, grouped
    )
    assignments = [
        {**row, "expression": expression}
        if row["target_column"] == status_column
        else row
        for row in program["compiled_assignments"]
    ]
    if sum(row["target_column"] == status_column for row in assignments) != 1:
        _fail("safe terminal assignment cardinality changed")
    candidate_rows = [
        {
            **row,
            "exact_candidate_count": 1,
            "predicate_candidate_count": predicate_count,
            "selected_mdl_size": len(canonical_json_bytes(expression)),
            "selected_expression_sha256": hashlib.sha256(
                canonical_json_bytes(expression)
            ).hexdigest(),
            "self_next_status_candidates_excluded": True,
        }
        if row["target_column"] == status_column
        else row
        for row in program["candidate_evaluations"]
    ]
    expressions = [
        program["legal_expression"],
        program["accept_expression"],
        *[row["expression"] for row in assignments],
    ]
    used_opcodes = sorted(set().union(*(_used_opcodes(row) for row in expressions)))
    payload = {
        **{key: value for key, value in program.items() if key != "program_id"},
        "schema": "acfqp.generic_atomic_expression_world_model.v6",
        "predecessor_program_id": program["program_id"],
        "compiled_assignments": assignments,
        "candidate_evaluations": candidate_rows,
        "atomic_expression_evaluations": program["atomic_expression_evaluations"]
        + evaluations,
        "used_opcode_names": used_opcodes,
        "terminal_next_status_column_candidates_excluded": True,
        "terminal_self_next_dependency_count": 0,
        "status": "GENERIC_ATOMIC_EXPRESSIONS_COMPOSED_WITH_SAFE_TERMINAL_DEPENDENCIES",
    }
    safe_program = {**payload, "program_id": content_id(program_domain, payload)}
    aligned_rows = tuple(
        row for occurrence in sorted(grouped) for row in grouped[occurrence]
    )
    support = derive_atomic_dependency_support_v4(
        safe_program,
        aligned_rows,
        aligned_catalogues,
        support_domain=support_domain,
    )
    return {
        **predecessor,
        "schema": "acfqp.generic_layout_factorized_world_model.v6",
        "predecessor_program_id": program["program_id"],
        "compiled_program": safe_program,
        "dependency_support": support,
        "terminal_next_status_column_candidates_excluded": True,
        "terminal_self_next_dependency_count": 0,
        "status": "LAYOUT_FACTORIZATION_AND_SAFE_WORLD_MODEL_SYNTHESIZED",
    }


__all__ = (
    "GenericLayoutFactorizedWorldModelV6Error",
    "SAFE_TERMINAL_TREE_BEAM_WIDTH_V6",
    "SAFE_TERMINAL_TREE_MAX_DEPTH_V6",
    "synthesize_layout_factorized_world_model_v6",
)
