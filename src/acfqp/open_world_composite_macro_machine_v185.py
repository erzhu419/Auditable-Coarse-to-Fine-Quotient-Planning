"""Observation-derived reusable composite operators for V185.

V184 fairly enumerates a countably infinite expression language over a fixed,
small typed opcode basis.  V185 does not add an opcode.  It mines repeated
operator trees from programs that were themselves synthesized from raw
transitions, replaces their concrete leaves by anonymous arguments, and keeps
only definitions with positive exact token-MDL gain.  A retained definition is
therefore a reusable composite operator, not a new low-level primitive.

Every target instantiation is re-executed against every current observation.
Failure to find a program inside a finite prefix is resource exhaustion, never
an infeasibility certificate.  This module is a construction substrate; its
documents deliberately keep arbitrary-domain and official gates disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp.open_world_fair_expression_machine_v184 import (
    FairSearchResourceExhaustedV184,
    synthesize_fair_ranked_scalar_program_v184,
)
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_ranked_machine_v183 import (
    RankedTerminationCertificateV183,
    certify_ranked_termination_v183,
    execute_ranked_program_v183,
)
from acfqp.open_world_universal_machine_v182 import (
    ADD,
    CONST,
    EQ,
    HALT,
    INC,
    ISZERO,
    LT,
    MachineSynthesisRowV182,
    ProgramV182,
    READ,
    SUBSAT,
    XOR,
    program_bytes_v182,
)
from acfqp.phase3e_ids import canonical_json_bytes


ExpressionV185 = tuple[Any, ...]
NormalizedMacroV185 = tuple[Any, ...]
_UNARY = frozenset({"INC", "ISZERO"})
_BINARY = frozenset({"ADD", "SUBSAT", "XOR", "EQ", "LT"})
_COMMUTATIVE = frozenset({"ADD", "XOR", "EQ"})
_OPCODE_BY_NAME = {
    "ADD": ADD,
    "SUBSAT": SUBSAT,
    "XOR": XOR,
    "EQ": EQ,
    "LT": LT,
}


class OpenWorldCompositeMacroMachineV185Error(ValueError):
    pass


class CompositeMacroSearchResourceExhaustedV185(
    OpenWorldCompositeMacroMachineV185Error
):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCompositeMacroMachineV185Error(message)


def _expression_from_document(value: Any) -> ExpressionV185:
    if type(value) is not list or not value or type(value[0]) is not str:
        _fail("V185 expression document changed")
    opcode = value[0]
    if opcode in {"INPUT", "CONST", "ARG"}:
        if len(value) != 2 or type(value[1]) is not int or value[1] < 0:
            _fail("V185 expression atom changed")
        return (opcode, value[1])
    expected = 2 if opcode in _UNARY else 3 if opcode in _BINARY else 0
    if len(value) != expected:
        _fail("V185 expression opcode or arity changed")
    return (opcode, *(_expression_from_document(row) for row in value[1:]))


def _expression_document(expression: ExpressionV185) -> list[Any]:
    return [
        expression[0],
        *[
            _expression_document(value) if type(value) is tuple else value
            for value in expression[1:]
        ],
    ]


def _expression_key(expression: ExpressionV185) -> bytes:
    return canonical_json_bytes(_expression_document(expression))


def _tree_size(expression: ExpressionV185) -> int:
    return 1 + sum(
        _tree_size(value) for value in expression[1:] if type(value) is tuple
    )


def _operator_count(expression: ExpressionV185) -> int:
    return int(expression[0] not in {"INPUT", "CONST", "ARG"}) + sum(
        _operator_count(value) for value in expression[1:] if type(value) is tuple
    )


def _subtrees(expression: ExpressionV185) -> Iterable[ExpressionV185]:
    yield expression
    for value in expression[1:]:
        if type(value) is tuple:
            yield from _subtrees(value)


def _normalize_macro(expression: ExpressionV185) -> tuple[NormalizedMacroV185, int]:
    leaves: dict[ExpressionV185, int] = {}

    def visit(node: ExpressionV185) -> NormalizedMacroV185:
        if node[0] in {"INPUT", "CONST"}:
            if node not in leaves:
                leaves[node] = len(leaves)
            return ("ARG", leaves[node])
        return (node[0], *(visit(value) for value in node[1:]))

    return visit(expression), len(leaves)


def _macro_argument_multiplicity(body: NormalizedMacroV185) -> tuple[int, ...]:
    counts: dict[int, int] = {}

    def visit(node: NormalizedMacroV185) -> None:
        if node[0] == "ARG":
            counts[node[1]] = counts.get(node[1], 0) + 1
            return
        for value in node[1:]:
            visit(value)

    visit(body)
    return tuple(counts[index] for index in range(len(counts)))


def _macro_mdl(
    body: NormalizedMacroV185,
    *,
    occurrence_count: int,
    argument_count: int,
) -> tuple[int, int, int]:
    raw_tokens = occurrence_count * _tree_size(body)
    definition_tokens = _tree_size(body) + 1 + argument_count
    invocation_tokens = occurrence_count * (1 + argument_count)
    encoded_tokens = definition_tokens + invocation_tokens
    return raw_tokens, encoded_tokens, raw_tokens - encoded_tokens


@dataclass(frozen=True, slots=True)
class CompositeMacroDefinitionV185:
    body: NormalizedMacroV185
    argument_count: int
    argument_multiplicity: tuple[int, ...]
    occurrence_count: int
    source_program_ids: tuple[str, ...]
    raw_token_count: int
    encoded_token_count: int
    mdl_gain_tokens: int
    macro_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.composite_macro_definition.v185",
            "body": _expression_document(self.body),
            "argument_count": self.argument_count,
            "argument_multiplicity": list(self.argument_multiplicity),
            "occurrence_count": self.occurrence_count,
            "source_program_ids": list(self.source_program_ids),
            "raw_token_count": self.raw_token_count,
            "encoded_token_count": self.encoded_token_count,
            "mdl_gain_tokens": self.mdl_gain_tokens,
            "positive_exact_token_mdl_gain": self.mdl_gain_tokens > 0,
            "leaf_roles_anonymized": True,
            "predeclared_reusable_factor_slot_used": False,
            "new_low_level_primitive_opcode_invented": False,
            "reusable_composite_operator_invented": True,
            "macro_id": self.macro_id,
        }


@dataclass(frozen=True, slots=True)
class CompositeMacroLibraryV185:
    macros: tuple[CompositeMacroDefinitionV185, ...]
    source_model_ids: tuple[str, ...]
    source_observation_ids: tuple[str, ...]
    minimum_occurrences: int
    minimum_operator_count: int
    minimum_mdl_gain_tokens: int
    macro_library_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.composite_macro_library.v185",
            "macros": [row.to_document() for row in self.macros],
            "macro_ids": [row.macro_id for row in self.macros],
            "macro_count": len(self.macros),
            "source_model_ids": list(self.source_model_ids),
            "source_observation_ids": list(self.source_observation_ids),
            "minimum_occurrences": self.minimum_occurrences,
            "minimum_operator_count": self.minimum_operator_count,
            "minimum_mdl_gain_tokens": self.minimum_mdl_gain_tokens,
            "joint_factorable_and_residual_subprogram_discovery": True,
            "predeclared_reusable_factor_slots": [],
            "predeclared_macro_bodies": [],
            "leaf_roles_anonymized": True,
            "new_low_level_primitive_opcode_invented": False,
            "reusable_composite_operator_invented": bool(self.macros),
            "arbitrary_domain_transfer_claimed": False,
            "macro_library_id": self.macro_library_id,
        }


def _validate_source_model_document(document: Mapping[str, Any]) -> None:
    if (
        type(document) is not dict
        or document.get("schema") != "acfqp.fair_ranked_compiled_world_model.v184"
        or type(document.get("compiled_model_id")) is not str
        or len(document["compiled_model_id"]) != 64
        or type(document.get("source_observation_ids")) is not list
        or not document["source_observation_ids"]
        or type(document.get("coordinates")) is not list
        or type(document.get("terminal_synthesis")) is not dict
        or document.get("candidate_language_countably_infinite") is not True
        or document.get("finite_candidate_catalog_used") is not False
        or document.get("new_primitive_opcode_invented") is not False
    ):
        _fail("V185 source model is not a bounded V184 synthesized model")


def discover_composite_macro_library_v185(
    source_model_documents: Sequence[Mapping[str, Any]],
    *,
    minimum_occurrences: int = 3,
    minimum_operator_count: int = 2,
    minimum_mdl_gain_tokens: int = 1,
    maximum_macro_count: int = 32,
) -> CompositeMacroLibraryV185:
    if (
        type(source_model_documents) not in {tuple, list}
        or not source_model_documents
        or type(minimum_occurrences) is not int
        or minimum_occurrences < 2
        or type(minimum_operator_count) is not int
        or minimum_operator_count < 2
        or type(minimum_mdl_gain_tokens) is not int
        or minimum_mdl_gain_tokens < 1
        or type(maximum_macro_count) is not int
        or maximum_macro_count < 1
    ):
        _fail("V185 macro-discovery profile changed")
    counts: dict[NormalizedMacroV185, int] = {}
    programs: dict[NormalizedMacroV185, set[str]] = {}
    model_ids: list[str] = []
    observation_ids: list[str] = []
    for document in source_model_documents:
        _validate_source_model_document(document)
        model_ids.append(document["compiled_model_id"])
        observation_ids.extend(document["source_observation_ids"])
        synthesis_rows = [*document["coordinates"], document["terminal_synthesis"]]
        for row in synthesis_rows:
            if type(row) is not dict or type(row.get("program_id")) is not str:
                _fail("V185 source synthesis row changed")
            expression_document = row.get("expression")
            if expression_document is None:
                continue
            expression = _expression_from_document(expression_document)
            for subtree in _subtrees(expression):
                if _operator_count(subtree) < minimum_operator_count:
                    continue
                normalized, argument_count = _normalize_macro(subtree)
                if argument_count == 0:
                    continue
                counts[normalized] = counts.get(normalized, 0) + 1
                programs.setdefault(normalized, set()).add(row["program_id"])
    definitions: list[CompositeMacroDefinitionV185] = []
    for body, occurrence_count in counts.items():
        argument_count = max(
            value[1] for value in _subtrees(body) if value[0] == "ARG"
        ) + 1
        raw_tokens, encoded_tokens, gain = _macro_mdl(
            body,
            occurrence_count=occurrence_count,
            argument_count=argument_count,
        )
        if occurrence_count < minimum_occurrences or gain < minimum_mdl_gain_tokens:
            continue
        payload = {
            "schema": "acfqp.composite_macro_definition.v185",
            "body": _expression_document(body),
            "argument_count": argument_count,
            "argument_multiplicity": list(_macro_argument_multiplicity(body)),
            "occurrence_count": occurrence_count,
            "source_program_ids": sorted(programs[body]),
            "raw_token_count": raw_tokens,
            "encoded_token_count": encoded_tokens,
            "mdl_gain_tokens": gain,
            "positive_exact_token_mdl_gain": True,
            "leaf_roles_anonymized": True,
            "predeclared_reusable_factor_slot_used": False,
            "new_low_level_primitive_opcode_invented": False,
            "reusable_composite_operator_invented": True,
        }
        definitions.append(
            CompositeMacroDefinitionV185(
                body,
                argument_count,
                _macro_argument_multiplicity(body),
                occurrence_count,
                tuple(sorted(programs[body])),
                raw_tokens,
                encoded_tokens,
                gain,
                domains.extension_content_id_v185(
                    domains.CONSTRUCTION_K7_MACRO_DEFINITION_V185_DOMAIN,
                    payload,
                ),
            )
        )
    definitions.sort(
        key=lambda row: (-row.mdl_gain_tokens, _expression_key(row.body))
    )
    frozen = tuple(definitions[:maximum_macro_count])
    payload = {
        "schema": "acfqp.composite_macro_library.v185",
        "macros": [row.to_document() for row in frozen],
        "macro_ids": [row.macro_id for row in frozen],
        "macro_count": len(frozen),
        "source_model_ids": model_ids,
        "source_observation_ids": observation_ids,
        "minimum_occurrences": minimum_occurrences,
        "minimum_operator_count": minimum_operator_count,
        "minimum_mdl_gain_tokens": minimum_mdl_gain_tokens,
        "joint_factorable_and_residual_subprogram_discovery": True,
        "predeclared_reusable_factor_slots": [],
        "predeclared_macro_bodies": [],
        "leaf_roles_anonymized": True,
        "new_low_level_primitive_opcode_invented": False,
        "reusable_composite_operator_invented": bool(frozen),
        "arbitrary_domain_transfer_claimed": False,
    }
    return CompositeMacroLibraryV185(
        frozen,
        tuple(model_ids),
        tuple(observation_ids),
        minimum_occurrences,
        minimum_operator_count,
        minimum_mdl_gain_tokens,
        domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_MACRO_LIBRARY_V185_DOMAIN,
            payload,
        ),
    )


def _instantiate_macro(
    body: NormalizedMacroV185,
    arguments: Sequence[ExpressionV185],
) -> ExpressionV185:
    if body[0] == "ARG":
        return arguments[body[1]]
    return (body[0], *(_instantiate_macro(value, arguments) for value in body[1:]))


def _compile_expression(
    expression: ExpressionV185,
    *,
    input_width: int,
    register_count: int,
) -> ProgramV182 | None:
    instructions: list[tuple[int, ...]] = []

    def emit(node: ExpressionV185, target: int) -> bool:
        if target >= register_count:
            return False
        opcode = node[0]
        if opcode == "INPUT":
            if node[1] >= input_width:
                return False
            instructions.append((READ, target, node[1]))
            return True
        if opcode == "CONST":
            instructions.append((CONST, target, node[1]))
            return True
        if opcode in _UNARY:
            if not emit(node[1], target):
                return False
            instructions.append((INC, target) if opcode == "INC" else (ISZERO, target, target))
            return True
        if opcode in _BINARY:
            if not emit(node[1], target) or not emit(node[2], target + 1):
                return False
            instructions.append((_OPCODE_BY_NAME[opcode], target, target, target + 1))
            return True
        return False

    if not emit(expression, 0):
        return None
    instructions.append((HALT, 0))
    return tuple(instructions)


def _read_dependencies(expression: ExpressionV185) -> tuple[int, ...]:
    result: set[int] = set()

    def visit(node: ExpressionV185) -> None:
        if node[0] == "INPUT":
            result.add(node[1])
        for value in node[1:]:
            if type(value) is tuple:
                visit(value)

    visit(expression)
    return tuple(sorted(result))


def _dependency_document(
    indices: Iterable[int], state_width: int
) -> tuple[tuple[str, int], ...]:
    return tuple(
        ("S", index) if index < state_width else ("A", index - state_width)
        for index in sorted(set(indices))
    )


@dataclass(frozen=True, slots=True)
class CompositeMacroSynthesizedProgramV185:
    program: ProgramV182
    expression: ExpressionV185 | None
    termination: RankedTerminationCertificateV183
    residual_values: tuple[int, ...]
    read_dependencies: tuple[tuple[str, int], ...]
    candidate_evaluations: int
    selected_macro_id: str | None
    fair_fallback_used: bool
    program_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.composite_macro_synthesized_program.v185",
            "program": [list(row) for row in self.program],
            "expression": (
                _expression_document(self.expression)
                if self.expression is not None
                else None
            ),
            "termination_certificate": self.termination.to_document(),
            "residual_values": list(self.residual_values),
            "read_dependencies": [list(row) for row in self.read_dependencies],
            "candidate_evaluations": self.candidate_evaluations,
            "selected_macro_id": self.selected_macro_id,
            "macro_candidate_selected": self.selected_macro_id is not None,
            "fair_fallback_used": self.fair_fallback_used,
            "target_rows_revalidated_exactly": True,
            "new_low_level_primitive_opcode_invented": False,
            "reusable_composite_operator_used": self.selected_macro_id is not None,
            "resource_cap_exhaustion_is_not_infeasibility": True,
            "program_id": self.program_id,
        }


def synthesize_composite_macro_scalar_program_v185(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    macro_library: CompositeMacroLibraryV185 | None,
    maximum_macro_candidate_evaluations: int,
    maximum_fair_enumeration_events: int,
    resource_step_cap: int,
    register_count: int = 6,
    maximum_residual_support: int = 3,
) -> CompositeMacroSynthesizedProgramV185:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or (
            macro_library is not None
            and type(macro_library) is not CompositeMacroLibraryV185
        )
        or type(maximum_macro_candidate_evaluations) is not int
        or maximum_macro_candidate_evaluations < 0
        or type(maximum_fair_enumeration_events) is not int
        or maximum_fair_enumeration_events < 1
    ):
        _fail("V185 scalar synthesis contract changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if any(
        len(row.state) != state_width or len(row.action) != action_width
        for row in rows
    ):
        _fail("V185 scalar rows crossed opaque schemas")
    input_width = state_width + action_width
    constants = tuple(
        sorted(
            {
                0,
                1,
                *(
                    value
                    for row in rows
                    for value in (*row.state, *row.action, row.target)
                ),
            }
        )
    )
    atoms: tuple[ExpressionV185, ...] = tuple(
        [("INPUT", index) for index in range(input_width)]
        + [("CONST", value) for value in constants]
    )
    targets = tuple(row.target for row in rows)
    events = 0
    best: tuple[
        tuple[Any, ...],
        ProgramV182,
        ExpressionV185,
        RankedTerminationCertificateV183,
        tuple[int, ...],
        tuple[int, ...],
        str,
    ] | None = None
    seen_programs: set[ProgramV182] = set()
    if macro_library is not None:
        for macro in macro_library.macros:
            for arguments in product(atoms, repeat=macro.argument_count):
                if events >= maximum_macro_candidate_evaluations:
                    break
                expression = _instantiate_macro(macro.body, arguments)
                program = _compile_expression(
                    expression,
                    input_width=input_width,
                    register_count=register_count,
                )
                if program is None or program in seen_programs:
                    continue
                seen_programs.add(program)
                events += 1
                certificate = certify_ranked_termination_v183(
                    program,
                    register_count=register_count,
                    input_width=input_width,
                )
                if certificate is None:
                    raise AssertionError("V185 macro compiler produced an uncertified program")
                executions = tuple(
                    execute_ranked_program_v183(
                        program,
                        state=row.state,
                        action=row.action,
                        register_count=register_count,
                        resource_step_cap=resource_step_cap,
                    )
                    for row in rows
                )
                if any(not row.halted or row.output is None for row in executions):
                    continue
                outputs = tuple(int(row.output) for row in executions)
                residuals = () if outputs == targets else tuple(
                    sorted(
                        {
                            target - output
                            for target, output in zip(targets, outputs, strict=True)
                        }
                    )
                )
                if residuals and not 1 <= len(residuals) <= maximum_residual_support:
                    continue
                dependencies = _read_dependencies(expression)
                rank = (
                    int(bool(residuals)),
                    len(program) + len(residuals),
                    len(residuals),
                    program_bytes_v182(program),
                )
                current = (
                    rank,
                    program,
                    expression,
                    certificate,
                    residuals,
                    dependencies,
                    macro.macro_id,
                )
                if best is None or current[0] < best[0]:
                    best = current
                    if not residuals:
                        break
            if best is not None and not best[4]:
                break
    if best is not None:
        _, program, expression, certificate, residuals, dependencies, macro_id = best
        payload = {
            "schema": "acfqp.composite_macro_synthesized_program.v185",
            "program": [list(row) for row in program],
            "expression": _expression_document(expression),
            "termination_certificate": certificate.to_document(),
            "residual_values": list(residuals),
            "read_dependencies": [
                list(row) for row in _dependency_document(dependencies, state_width)
            ],
            "candidate_evaluations": events,
            "selected_macro_id": macro_id,
            "macro_candidate_selected": True,
            "fair_fallback_used": False,
            "target_rows_revalidated_exactly": True,
            "new_low_level_primitive_opcode_invented": False,
            "reusable_composite_operator_used": True,
            "resource_cap_exhaustion_is_not_infeasibility": True,
        }
        return CompositeMacroSynthesizedProgramV185(
            program,
            expression,
            certificate,
            residuals,
            _dependency_document(dependencies, state_width),
            events,
            macro_id,
            False,
            domains.extension_content_id_v185(
                domains.CONSTRUCTION_K7_SYNTHESIZED_PROGRAM_V185_DOMAIN,
                payload,
            ),
        )
    try:
        fallback = synthesize_fair_ranked_scalar_program_v184(
            rows,
            maximum_enumeration_events=maximum_fair_enumeration_events,
            resource_step_cap=resource_step_cap,
            register_count=register_count,
            maximum_residual_support=maximum_residual_support,
        )
    except FairSearchResourceExhaustedV184 as error:
        raise CompositeMacroSearchResourceExhaustedV185(str(error)) from error
    payload = {
        "schema": "acfqp.composite_macro_synthesized_program.v185",
        "program": [list(row) for row in fallback.program],
        "expression": (
            _expression_document(fallback.expression)
            if fallback.expression is not None
            else None
        ),
        "termination_certificate": fallback.termination.to_document(),
        "residual_values": list(fallback.residual_values),
        "read_dependencies": [list(row) for row in fallback.read_dependencies],
        "candidate_evaluations": events + fallback.enumeration_events,
        "selected_macro_id": None,
        "macro_candidate_selected": False,
        "fair_fallback_used": True,
        "target_rows_revalidated_exactly": True,
        "new_low_level_primitive_opcode_invented": False,
        "reusable_composite_operator_used": False,
        "resource_cap_exhaustion_is_not_infeasibility": True,
    }
    return CompositeMacroSynthesizedProgramV185(
        fallback.program,
        fallback.expression,
        fallback.termination,
        fallback.residual_values,
        fallback.read_dependencies,
        events + fallback.enumeration_events,
        None,
        True,
        domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_SYNTHESIZED_PROGRAM_V185_DOMAIN,
            payload,
        ),
    )


__all__ = (
    "CompositeMacroDefinitionV185",
    "CompositeMacroLibraryV185",
    "CompositeMacroSearchResourceExhaustedV185",
    "CompositeMacroSynthesizedProgramV185",
    "discover_composite_macro_library_v185",
    "synthesize_composite_macro_scalar_program_v185",
)
