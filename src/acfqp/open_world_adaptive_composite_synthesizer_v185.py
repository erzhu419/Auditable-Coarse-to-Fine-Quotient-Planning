"""Matched macro-prior/no-prior semantic synthesis for the V185 campaign.

The two target arms execute this exact implementation.  The sole treatment
switch is whether an observation-derived ``CompositeMacroLibraryV185`` is
present.  Without a selected macro, both arms use the same fair-by-tree-size
semantic expression search.  Semantic duplicates are collapsed only on all
currently acquired rows and therefore never become transfer authority.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import Any, Iterable, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp.open_world_composite_macro_machine_v185 import (
    CompositeMacroCompiledWorldModelV185,
    CompositeMacroLibraryV185,
    CompositeMacroSearchResourceExhaustedV185,
    CompositeMacroSynthesizedProgramV185,
)
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_ranked_machine_v183 import (
    RankedTerminationCertificateV183,
    certify_ranked_termination_v183,
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
_UNARY = ("INC", "ISZERO")
_BINARY = ("ADD", "SUBSAT", "XOR", "EQ", "LT")
_COMMUTATIVE = frozenset({"ADD", "XOR", "EQ"})
_OPCODE_BY_NAME = {"ADD": ADD, "SUBSAT": SUBSAT, "XOR": XOR, "EQ": EQ, "LT": LT}


class OpenWorldAdaptiveCompositeSynthesizerV185Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldAdaptiveCompositeSynthesizerV185Error(message)


def _document(expression: ExpressionV185) -> list[Any]:
    return [
        expression[0],
        *[_document(value) if type(value) is tuple else value for value in expression[1:]],
    ]


@lru_cache(maxsize=None)
def _key(expression: ExpressionV185) -> bytes:
    return canonical_json_bytes(_document(expression))


def _from_document(value: Any) -> ExpressionV185:
    if type(value) is not list or not value or type(value[0]) is not str:
        _fail("V185 adaptive expression document changed")
    if value[0] in {"INPUT", "CONST", "ARG"}:
        if len(value) != 2 or type(value[1]) is not int or value[1] < 0:
            _fail("V185 adaptive expression atom changed")
        return value[0], value[1]
    expected = 2 if value[0] in _UNARY else 3 if value[0] in _BINARY else 0
    if len(value) != expected:
        _fail("V185 adaptive expression opcode changed")
    return value[0], *(_from_document(row) for row in value[1:])


def _instantiate(
    body: ExpressionV185, arguments: Sequence[ExpressionV185]
) -> ExpressionV185:
    if body[0] == "ARG":
        return arguments[body[1]]
    return body[0], *(_instantiate(value, arguments) for value in body[1:])


def _evaluate(
    expression: ExpressionV185,
    inputs: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    opcode = expression[0]
    if opcode == "INPUT":
        return tuple(row[expression[1]] for row in inputs)
    if opcode == "CONST":
        return (expression[1],) * len(inputs)
    if opcode in _UNARY:
        child = _evaluate(expression[1], inputs)
        if opcode == "INC":
            return tuple(value + 1 for value in child)
        return tuple(int(value == 0) for value in child)
    left = _evaluate(expression[1], inputs)
    right = _evaluate(expression[2], inputs)
    if opcode == "ADD":
        return tuple(a + b for a, b in zip(left, right, strict=True))
    if opcode == "SUBSAT":
        return tuple(max(a - b, 0) for a, b in zip(left, right, strict=True))
    if opcode == "XOR":
        return tuple(a ^ b for a, b in zip(left, right, strict=True))
    if opcode == "EQ":
        return tuple(int(a == b) for a, b in zip(left, right, strict=True))
    if opcode == "LT":
        return tuple(int(a < b) for a, b in zip(left, right, strict=True))
    _fail("V185 adaptive expression escaped its opcode basis")


def _apply_unary(opcode: str, child: tuple[int, ...]) -> tuple[int, ...]:
    if opcode == "INC":
        return tuple(value + 1 for value in child)
    if opcode == "ISZERO":
        return tuple(int(value == 0) for value in child)
    _fail("V185 adaptive unary opcode changed")


def _apply_binary(
    opcode: str, left: tuple[int, ...], right: tuple[int, ...]
) -> tuple[int, ...]:
    if opcode == "ADD":
        return tuple(a + b for a, b in zip(left, right, strict=True))
    if opcode == "SUBSAT":
        return tuple(max(a - b, 0) for a, b in zip(left, right, strict=True))
    if opcode == "XOR":
        return tuple(a ^ b for a, b in zip(left, right, strict=True))
    if opcode == "EQ":
        return tuple(int(a == b) for a, b in zip(left, right, strict=True))
    if opcode == "LT":
        return tuple(int(a < b) for a, b in zip(left, right, strict=True))
    _fail("V185 adaptive binary opcode changed")


def _compile(
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


def _dependencies(expression: ExpressionV185) -> tuple[int, ...]:
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


def _residuals(
    targets: tuple[int, ...], outputs: tuple[int, ...]
) -> tuple[int, ...]:
    if targets == outputs:
        return ()
    return tuple(
        sorted(
            {target - output for target, output in zip(targets, outputs, strict=True)}
        )
    )


def _rank(
    program: ProgramV182, residuals: tuple[int, ...], expression: ExpressionV185
) -> tuple[Any, ...]:
    return (
        int(bool(residuals)),
        len(program) + len(residuals),
        len(residuals),
        program_bytes_v182(program),
        _key(expression),
    )


def _make_result(
    *,
    expression: ExpressionV185,
    program: ProgramV182,
    certificate: RankedTerminationCertificateV183,
    residual_values: tuple[int, ...],
    state_width: int,
    candidate_evaluations: int,
    selected_macro_id: str | None,
    fair_fallback_used: bool,
) -> CompositeMacroSynthesizedProgramV185:
    dependencies = _dependency_document(_dependencies(expression), state_width)
    payload = {
        "schema": "acfqp.composite_macro_synthesized_program.v185",
        "program": [list(row) for row in program],
        "expression": _document(expression),
        "termination_certificate": certificate.to_document(),
        "residual_values": list(residual_values),
        "read_dependencies": [list(row) for row in dependencies],
        "candidate_evaluations": candidate_evaluations,
        "selected_macro_id": selected_macro_id,
        "macro_candidate_selected": selected_macro_id is not None,
        "fair_fallback_used": fair_fallback_used,
        "target_rows_revalidated_exactly": True,
        "new_low_level_primitive_opcode_invented": False,
        "reusable_composite_operator_used": selected_macro_id is not None,
        "resource_cap_exhaustion_is_not_infeasibility": True,
    }
    return CompositeMacroSynthesizedProgramV185(
        program,
        expression,
        certificate,
        residual_values,
        dependencies,
        candidate_evaluations,
        selected_macro_id,
        fair_fallback_used,
        domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_SYNTHESIZED_PROGRAM_V185_DOMAIN,
            payload,
        ),
    )


def synthesize_adaptive_composite_scalar_v185(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    macro_library: CompositeMacroLibraryV185 | None,
    maximum_macro_candidate_evaluations: int,
    maximum_fair_candidate_evaluations: int,
    resource_step_cap: int,
    register_count: int,
    maximum_residual_support: int,
) -> CompositeMacroSynthesizedProgramV185:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or (
            macro_library is not None
            and type(macro_library) is not CompositeMacroLibraryV185
        )
        or maximum_macro_candidate_evaluations < 0
        or maximum_fair_candidate_evaluations < 1
        or maximum_residual_support < 1
    ):
        _fail("V185 adaptive scalar synthesis contract changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if any(
        len(row.state) != state_width or len(row.action) != action_width
        for row in rows
    ):
        _fail("V185 adaptive rows crossed opaque schemas")
    inputs = tuple((*row.state, *row.action) for row in rows)
    targets = tuple(row.target for row in rows)
    input_width = state_width + action_width
    constants = tuple(
        sorted({0, 1, *(value for row in rows for value in (*row.state, *row.action, row.target))})
    )
    atoms: tuple[ExpressionV185, ...] = tuple(
        [("INPUT", index) for index in range(input_width)]
        + [("CONST", value) for value in constants]
    )
    events = 0
    best: tuple[
        tuple[Any, ...], ExpressionV185, ProgramV182, RankedTerminationCertificateV183, tuple[int, ...], str | None
    ] | None = None

    def consider(
        expression: ExpressionV185,
        macro_id: str | None,
        outputs: tuple[int, ...] | None = None,
    ) -> bool:
        nonlocal events, best
        events += 1
        if outputs is None:
            outputs = _evaluate(expression, inputs)
        residual_values = _residuals(targets, outputs)
        if residual_values and not 1 <= len(residual_values) <= maximum_residual_support:
            return False
        program = _compile(expression, input_width=input_width, register_count=register_count)
        if program is None:
            return False
        certificate = certify_ranked_termination_v183(
            program,
            register_count=register_count,
            input_width=input_width,
        )
        if certificate is None:
            raise AssertionError("V185 adaptive compiler produced an uncertified program")
        current = (
            _rank(program, residual_values, expression),
            expression,
            program,
            certificate,
            residual_values,
            macro_id,
        )
        if best is None or current[0] < best[0]:
            best = current
        return not residual_values

    if macro_library is not None:
        for macro in macro_library.macros:
            body = _from_document(macro.to_document()["body"])
            for arguments in product(atoms, repeat=macro.argument_count):
                if events >= maximum_macro_candidate_evaluations:
                    break
                if consider(_instantiate(body, arguments), macro.macro_id):
                    break
            if best is not None and best[5] is not None:
                # A supported stochastic residual is also an admissible exact
                # support model after every current row has been checked.
                break
        if best is not None and best[5] is not None:
            _, expression, program, certificate, residual_values, macro_id = best
            return _make_result(
                expression=expression,
                program=program,
                certificate=certificate,
                residual_values=residual_values,
                state_width=state_width,
                candidate_evaluations=events,
                selected_macro_id=macro_id,
                fair_fallback_used=False,
            )

    semantic_seen: set[tuple[int, ...]] = set()
    by_size: dict[int, tuple[tuple[ExpressionV185, tuple[int, ...]], ...]] = {}
    first_rows = []
    for atom in atoms:
        outputs = _evaluate(atom, inputs)
        if outputs in semantic_seen:
            continue
        semantic_seen.add(outputs)
        first_rows.append((atom, outputs))
    by_size[1] = tuple(sorted(first_rows, key=lambda row: _key(row[0])))
    size = 1
    while events < maximum_fair_candidate_evaluations:
        current_rows = by_size[size]
        for expression, outputs in current_rows:
            if events >= maximum_fair_candidate_evaluations:
                break
            if consider(expression, None, outputs):
                _, selected, program, certificate, residual_values, _ = best
                return _make_result(
                    expression=selected,
                    program=program,
                    certificate=certificate,
                    residual_values=residual_values,
                    state_width=state_width,
                    candidate_evaluations=events,
                    selected_macro_id=None,
                    fair_fallback_used=True,
                )
        next_size = size + 1
        generated: dict[tuple[int, ...], ExpressionV185] = {}
        for opcode in _UNARY:
            for child, child_outputs in by_size[size]:
                expression = (opcode, child)
                outputs = _apply_unary(opcode, child_outputs)
                if outputs not in semantic_seen:
                    previous = generated.get(outputs)
                    if previous is None or _key(expression) < _key(previous):
                        generated[outputs] = expression
        for left_size in range(1, next_size - 1):
            right_size = next_size - 1 - left_size
            if right_size not in by_size:
                continue
            for opcode in _BINARY:
                for left, left_outputs in by_size[left_size]:
                    for right, right_outputs in by_size[right_size]:
                        if opcode in _COMMUTATIVE and _key(left) > _key(right):
                            continue
                        expression = (opcode, left, right)
                        outputs = _apply_binary(opcode, left_outputs, right_outputs)
                        if outputs in semantic_seen:
                            continue
                        previous = generated.get(outputs)
                        if previous is None or _key(expression) < _key(previous):
                            generated[outputs] = expression
        rows_for_size = tuple(
            sorted(
                ((expression, outputs) for outputs, expression in generated.items()),
                key=lambda row: _key(row[0]),
            )
        )
        if not rows_for_size:
            break
        semantic_seen.update(outputs for _expression, outputs in rows_for_size)
        by_size[next_size] = rows_for_size
        size = next_size
    if best is None:
        raise CompositeMacroSearchResourceExhaustedV185(
            "V185 finite semantic prefix found no supported ranked-total program"
        )
    _, expression, program, certificate, residual_values, _ = best
    return _make_result(
        expression=expression,
        program=program,
        certificate=certificate,
        residual_values=residual_values,
        state_width=state_width,
        candidate_evaluations=events,
        selected_macro_id=None,
        fair_fallback_used=True,
    )


def _factor_boundaries(
    rows: Sequence[CompositeMacroSynthesizedProgramV185],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(row.read_dependencies, []).append(index)
    return tuple(sorted((tuple(value) for value in groups.values()), key=lambda value: (value[0], len(value))))


def compile_adaptive_composite_world_model_v185(
    observations: Sequence[RawMachineTransitionV182],
    *,
    macro_library: CompositeMacroLibraryV185 | None,
    maximum_macro_candidate_evaluations_per_scalar: int,
    maximum_fair_candidate_evaluations_per_scalar: int,
    resource_step_cap: int,
    register_count: int,
    maximum_residual_support: int,
) -> CompositeMacroCompiledWorldModelV185:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V185 adaptive model requires eight raw transitions")
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
        _fail("V185 adaptive observations crossed schemas or identities")
    coordinates = tuple(
        synthesize_adaptive_composite_scalar_v185(
            tuple(MachineSynthesisRowV182(row.state, row.action, row.successor[index]) for row in observations),
            macro_library=macro_library,
            maximum_macro_candidate_evaluations=maximum_macro_candidate_evaluations_per_scalar,
            maximum_fair_candidate_evaluations=maximum_fair_candidate_evaluations_per_scalar,
            resource_step_cap=resource_step_cap,
            register_count=register_count,
            maximum_residual_support=maximum_residual_support,
        )
        for index in range(state_width)
    )
    terminal = synthesize_adaptive_composite_scalar_v185(
        tuple(MachineSynthesisRowV182(row.successor, (0,) * action_width, int(row.terminal)) for row in observations),
        macro_library=macro_library,
        maximum_macro_candidate_evaluations=maximum_macro_candidate_evaluations_per_scalar,
        maximum_fair_candidate_evaluations=maximum_fair_candidate_evaluations_per_scalar,
        resource_step_cap=resource_step_cap,
        register_count=register_count,
        maximum_residual_support=1,
    )
    if terminal.residual_values:
        _fail("V185 adaptive terminal retained a residual support")
    legal_actions = tuple(sorted({row.action for row in observations}))
    boundaries = _factor_boundaries(coordinates)
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
        "macro_library_id": macro_library.macro_library_id if macro_library else None,
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
        macro_library.macro_library_id if macro_library else None,
        domains.extension_content_id_v185(domains.CONSTRUCTION_K7_COMPILED_MODEL_V185_DOMAIN, payload),
    )


__all__ = (
    "compile_adaptive_composite_world_model_v185",
    "synthesize_adaptive_composite_scalar_v185",
)
