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
        or document.get("schema")
        not in {
            "acfqp.fair_ranked_compiled_world_model.v184",
            "acfqp.composite_macro_compiled_world_model.v185",
        }
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


@dataclass(frozen=True, slots=True)
class CompositeMacroCompiledWorldModelV185:
    state_width: int
    action_width: int
    legal_actions: tuple[tuple[int, ...], ...]
    register_count: int
    resource_step_cap: int
    coordinates: tuple[CompositeMacroSynthesizedProgramV185, ...]
    terminal_synthesis: CompositeMacroSynthesizedProgramV185
    source_observation_ids: tuple[str, ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
    macro_library_id: str | None
    compiled_model_id: str

    def _run(
        self, program: ProgramV182, state: Sequence[int], action: Sequence[int]
    ) -> int:
        result = execute_ranked_program_v183(
            program,
            state=state,
            action=action,
            register_count=self.register_count,
            resource_step_cap=self.resource_step_cap,
        )
        if not result.halted or result.output is None:
            _fail("V185 compiled model crossed its execution resource cap")
        return int(result.output)

    def terminal(self, state: Sequence[int]) -> bool:
        if len(state) != self.state_width:
            _fail("V185 terminal input crossed its opaque width")
        result = self._run(
            self.terminal_synthesis.program,
            state,
            (0,) * self.action_width,
        )
        if result not in {0, 1}:
            _fail("V185 terminal program is not boolean")
        return bool(result)

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        if (
            len(state) != self.state_width
            or len(action) != self.action_width
            or tuple(action) not in self.legal_actions
        ):
            _fail("V185 prediction crossed its opaque schema")
        supports = []
        for synthesis in self.coordinates:
            base = self._run(synthesis.program, state, action)
            residuals = synthesis.residual_values or (0,)
            values = tuple(
                sorted({base + value for value in residuals if base + value >= 0})
            )
            if not values:
                _fail("V185 synthesized stochastic support is empty")
            supports.append(values)
        return tuple(product(*supports))

    def covers(self, row: RawMachineTransitionV182) -> bool:
        return (
            row.successor in self.predict_support(row.state, row.action)
            and self.terminal(row.successor) is row.terminal
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.composite_macro_compiled_world_model.v185",
            "state_width": self.state_width,
            "action_width": self.action_width,
            "legal_actions": [list(row) for row in self.legal_actions],
            "register_count": self.register_count,
            "resource_step_cap": self.resource_step_cap,
            "coordinates": [row.to_document() for row in self.coordinates],
            "terminal_synthesis": self.terminal_synthesis.to_document(),
            "source_observation_ids": list(self.source_observation_ids),
            "source_label_count": len(self.source_observation_ids),
            "factor_boundaries": [list(row) for row in self.factor_boundaries],
            "factor_boundaries_derived_from_read_dependencies": True,
            "macro_library_id": self.macro_library_id,
            "macro_prior_present": self.macro_library_id is not None,
            "same_scalar_synthesizer_with_only_macro_prior_toggle": True,
            "layout_supplied": False,
            "domain_family_supplied": False,
            "predeclared_reusable_factor_slots": [],
            "candidate_language_countably_infinite": True,
            "actual_search_prefix_finite": True,
            "base_typed_opcode_set_finite": True,
            "new_low_level_primitive_opcode_invented": False,
            "arbitrary_domain_transfer_claimed": False,
            "compiled_model_id": self.compiled_model_id,
        }


def _factor_boundaries_v185(
    rows: Sequence[CompositeMacroSynthesizedProgramV185],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(row.read_dependencies, []).append(index)
    return tuple(
        sorted(
            (tuple(indices) for indices in groups.values()),
            key=lambda value: (value[0], len(value)),
        )
    )


def compile_composite_macro_world_model_v185(
    observations: Sequence[RawMachineTransitionV182],
    *,
    macro_library: CompositeMacroLibraryV185 | None,
    maximum_macro_candidate_evaluations_per_scalar: int,
    maximum_fair_enumeration_events_per_scalar: int,
    resource_step_cap: int,
    register_count: int = 6,
    maximum_residual_support: int = 3,
) -> CompositeMacroCompiledWorldModelV185:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V185 compilation requires at least eight raw transitions")
    state_width = len(observations[0].state)
    action_width = len(observations[0].action)
    if (
        len({row.observation_id for row in observations}) != len(observations)
        or any(
            len(row.state) != state_width
            or len(row.successor) != state_width
            or len(row.action) != action_width
            for row in observations
        )
    ):
        _fail("V185 observations are duplicated or cross opaque schemas")
    coordinates = tuple(
        synthesize_composite_macro_scalar_program_v185(
            tuple(
                MachineSynthesisRowV182(row.state, row.action, row.successor[index])
                for row in observations
            ),
            macro_library=macro_library,
            maximum_macro_candidate_evaluations=(
                maximum_macro_candidate_evaluations_per_scalar
            ),
            maximum_fair_enumeration_events=(
                maximum_fair_enumeration_events_per_scalar
            ),
            resource_step_cap=resource_step_cap,
            register_count=register_count,
            maximum_residual_support=maximum_residual_support,
        )
        for index in range(state_width)
    )
    terminal = synthesize_composite_macro_scalar_program_v185(
        tuple(
            MachineSynthesisRowV182(
                row.successor,
                (0,) * action_width,
                int(row.terminal),
            )
            for row in observations
        ),
        macro_library=macro_library,
        maximum_macro_candidate_evaluations=(
            maximum_macro_candidate_evaluations_per_scalar
        ),
        maximum_fair_enumeration_events=maximum_fair_enumeration_events_per_scalar,
        resource_step_cap=resource_step_cap,
        register_count=register_count,
        maximum_residual_support=1,
    )
    if terminal.residual_values:
        _fail("V185 terminal program cannot retain a residual support")
    legal_actions = tuple(sorted({row.action for row in observations}))
    boundaries = _factor_boundaries_v185(coordinates)
    payload = {
        "schema": "acfqp.composite_macro_compiled_world_model.v185",
        "state_width": state_width,
        "action_width": action_width,
        "legal_actions": [list(row) for row in legal_actions],
        "register_count": register_count,
        "resource_step_cap": resource_step_cap,
        "coordinates": [row.to_document() for row in coordinates],
        "terminal_synthesis": terminal.to_document(),
        "source_observation_ids": [row.observation_id for row in observations],
        "source_label_count": len(observations),
        "factor_boundaries": [list(row) for row in boundaries],
        "factor_boundaries_derived_from_read_dependencies": True,
        "macro_library_id": (
            macro_library.macro_library_id if macro_library is not None else None
        ),
        "macro_prior_present": macro_library is not None,
        "same_scalar_synthesizer_with_only_macro_prior_toggle": True,
        "layout_supplied": False,
        "domain_family_supplied": False,
        "predeclared_reusable_factor_slots": [],
        "candidate_language_countably_infinite": True,
        "actual_search_prefix_finite": True,
        "base_typed_opcode_set_finite": True,
        "new_low_level_primitive_opcode_invented": False,
        "arbitrary_domain_transfer_claimed": False,
    }
    return CompositeMacroCompiledWorldModelV185(
        state_width,
        action_width,
        legal_actions,
        register_count,
        resource_step_cap,
        coordinates,
        terminal,
        tuple(row.observation_id for row in observations),
        boundaries,
        macro_library.macro_library_id if macro_library is not None else None,
        domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_COMPILED_MODEL_V185_DOMAIN,
            payload,
        ),
    )


@dataclass(frozen=True, slots=True)
class CompositeMacroPlanCertificateV185:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    terminal_distance_rank: int | None
    selected_successor_rank_upper_bound: int | None
    failure_reason: str | None
    planning_compute_events: int
    persistent_cache_hit_count: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.composite_macro_plan_certificate.v185",
            "compiled_model_id": self.compiled_model_id,
            "state": list(self.state),
            "horizon": self.horizon,
            "certified": self.certified,
            "selected_action": (
                list(self.selected_action) if self.selected_action is not None else None
            ),
            "terminal_distance_rank": self.terminal_distance_rank,
            "selected_successor_rank_upper_bound": self.selected_successor_rank_upper_bound,
            "strict_rank_decrease_proved": (
                self.certified
                and self.terminal_distance_rank is not None
                and self.selected_successor_rank_upper_bound is not None
                and self.selected_successor_rank_upper_bound
                < self.terminal_distance_rank
            ),
            "failure_reason": self.failure_reason,
            "planning_compute_events": self.planning_compute_events,
            "persistent_cache_hit_count": self.persistent_cache_hit_count,
            "ground_transition_argument_present": False,
            "local_ground_distinction_permitted": (
                not self.certified and self.failure_reason == "NO_HORIZON_CERTIFICATE"
            ),
            "compute_cap_failure_is_not_a_ground_label_request": False,
            "certificate_id": self.certificate_id,
        }


class CompositeMacroPlannerSessionV185:
    def __init__(
        self, model: CompositeMacroCompiledWorldModelV185, *, horizon: int
    ) -> None:
        if (
            type(model) is not CompositeMacroCompiledWorldModelV185
            or type(horizon) is not int
            or horizon <= 2
        ):
            _fail("V185 planner requires one compiled model and H>2")
        self._model = model
        self._horizon = horizon
        self._memo: dict[
            tuple[tuple[int, ...], int],
            tuple[int | None, tuple[int, ...] | None, int | None],
        ] = {}

    def certify(self, state: Sequence[int]) -> CompositeMacroPlanCertificateV185:
        frozen_state = tuple(state)
        events = 0
        cache_hits = 0

        def minimum_rank(
            current: tuple[int, ...], limit: int
        ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
            nonlocal events, cache_hits
            events += 1
            if self._model.terminal(current):
                return 0, None, None
            if limit == 0:
                return None, None, None
            key = (current, limit)
            if key in self._memo:
                cache_hits += 1
                return self._memo[key]
            candidates: list[tuple[int, tuple[int, ...], int]] = []
            for action in self._model.legal_actions:
                support = self._model.predict_support(current, action)
                ranks = [minimum_rank(successor, limit - 1)[0] for successor in support]
                if any(rank is None for rank in ranks):
                    continue
                upper = max(int(rank) for rank in ranks)
                candidates.append((upper + 1, action, upper))
            self._memo[key] = min(candidates) if candidates else (None, None, None)
            return self._memo[key]

        rank, action, upper = minimum_rank(frozen_state, self._horizon)
        certified = rank is not None and rank > 0 and action is not None
        reason = None if certified else "NO_HORIZON_CERTIFICATE"
        payload = {
            "schema": "acfqp.composite_macro_plan_certificate.v185",
            "compiled_model_id": self._model.compiled_model_id,
            "state": list(frozen_state),
            "horizon": self._horizon,
            "certified": certified,
            "selected_action": list(action) if action is not None else None,
            "terminal_distance_rank": rank,
            "selected_successor_rank_upper_bound": upper,
            "strict_rank_decrease_proved": certified,
            "failure_reason": reason,
            "planning_compute_events": events,
            "persistent_cache_hit_count": cache_hits,
            "ground_transition_argument_present": False,
            "local_ground_distinction_permitted": not certified,
            "compute_cap_failure_is_not_a_ground_label_request": False,
        }
        return CompositeMacroPlanCertificateV185(
            self._model.compiled_model_id,
            frozen_state,
            self._horizon,
            certified,
            action,
            rank,
            upper,
            reason,
            events,
            cache_hits,
            domains.extension_content_id_v185(
                domains.CONSTRUCTION_K7_PLAN_CERTIFICATE_V185_DOMAIN,
                payload,
            ),
        )


__all__ = (
    "CompositeMacroCompiledWorldModelV185",
    "CompositeMacroDefinitionV185",
    "CompositeMacroLibraryV185",
    "CompositeMacroPlanCertificateV185",
    "CompositeMacroPlannerSessionV185",
    "CompositeMacroSearchResourceExhaustedV185",
    "CompositeMacroSynthesizedProgramV185",
    "compile_composite_macro_world_model_v185",
    "discover_composite_macro_library_v185",
    "synthesize_composite_macro_scalar_program_v185",
)
