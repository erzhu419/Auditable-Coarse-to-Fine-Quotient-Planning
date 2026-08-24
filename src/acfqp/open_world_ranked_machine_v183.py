"""Proof-carrying counter programs total over unbounded nonnegative inputs.

V182r2 admitted arbitrary counter programs only after exhaustive execution on
one finite carrier.  V183 instead recognizes a conservative structural subset
of the same instruction language.  Every reachable control-flow cycle must be
guarded by one ``DECJZ`` ranking register, its zero edge must leave the cycle,
and no other instruction in that cycle may write the ranking register.  With
unbounded Python integers and no partial ``MOD`` instruction, this is a finite
termination proof for every finite nonnegative input of the frozen schema.

The proof system is deliberately incomplete: many terminating programs are
rejected.  General program termination remains undecidable.  Synthesis still
has a per-occurrence event cap even though the program language and input
values have no global bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Iterator, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_universal_machine_v182 import (
    ADD,
    CONST,
    DECJZ,
    EQ,
    HALT,
    INC,
    ISZERO,
    JUMP,
    LT,
    MOD,
    READ,
    SUBSAT,
    XOR,
    MachineSynthesisRowV182,
    ProgramV182,
    program_bytes_v182,
)


class OpenWorldRankedMachineV183Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldRankedMachineV183Error(message)


def _register(value: Any, register_count: int, label: str) -> int:
    if type(value) is not int or not 0 <= value < register_count:
        _fail(f"{label} is outside the V183 register file")
    return value


def _successors_and_writer(
    program: ProgramV182,
    pc: int,
    *,
    register_count: int,
    input_width: int,
) -> tuple[tuple[int, ...], int | None]:
    instruction = program[pc]
    if type(instruction) is not tuple or not instruction:
        _fail("V183 instruction encoding changed")
    opcode = instruction[0]
    fallthrough = pc + 1
    if opcode == HALT:
        if len(instruction) != 2:
            _fail("V183 HALT arity changed")
        _register(instruction[1], register_count, "HALT source")
        return (), None
    if opcode == READ:
        if (
            len(instruction) != 3
            or type(instruction[2]) is not int
            or not 0 <= instruction[2] < input_width
        ):
            _fail("V183 READ encoding changed")
        writer = _register(instruction[1], register_count, "READ target")
    elif opcode == CONST:
        if len(instruction) != 3 or type(instruction[2]) is not int or instruction[2] < 0:
            _fail("V183 CONST encoding changed")
        writer = _register(instruction[1], register_count, "CONST target")
    elif opcode == INC:
        if len(instruction) != 2:
            _fail("V183 INC arity changed")
        writer = _register(instruction[1], register_count, "INC target")
    elif opcode == ISZERO:
        if len(instruction) != 3:
            _fail("V183 ISZERO arity changed")
        writer = _register(instruction[1], register_count, "ISZERO target")
        _register(instruction[2], register_count, "ISZERO source")
    elif opcode in {ADD, SUBSAT, XOR, EQ, LT}:
        if len(instruction) != 4:
            _fail("V183 binary arity changed")
        writer = _register(instruction[1], register_count, "binary target")
        _register(instruction[2], register_count, "binary left")
        _register(instruction[3], register_count, "binary right")
    elif opcode == MOD:
        _fail("V183 totality proof rejects partial MOD")
    elif opcode == DECJZ:
        if len(instruction) != 4:
            _fail("V183 DECJZ arity changed")
        _register(instruction[1], register_count, "DECJZ source")
        targets = instruction[2:]
        if any(type(item) is not int or not 0 <= item < len(program) for item in targets):
            _fail("V183 DECJZ target changed")
        return (targets[0], targets[1]), None
    elif opcode == JUMP:
        if len(instruction) != 2 or type(instruction[1]) is not int or not 0 <= instruction[1] < len(program):
            _fail("V183 JUMP target changed")
        return (instruction[1],), None
    else:
        _fail("V183 opcode is outside the proof-carrying subset")
    if fallthrough >= len(program):
        _fail("V183 non-HALT instruction falls off the program")
    return (fallthrough,), writer


def _reachable(edges: Mapping[int, tuple[int, ...]]) -> frozenset[int]:
    pending = [0]
    seen: set[int] = set()
    while pending:
        pc = pending.pop()
        if pc in seen:
            continue
        seen.add(pc)
        pending.extend(edges[pc])
    return frozenset(seen)


def _strong_components(
    edges: Mapping[int, tuple[int, ...]],
) -> tuple[tuple[int, ...], ...]:
    index = 0
    indices: dict[int, int] = {}
    low: dict[int, int] = {}
    stack: list[int] = []
    on_stack: set[int] = set()
    result: list[tuple[int, ...]] = []

    def visit(node: int) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in edges[node]:
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            result.append(tuple(sorted(component)))

    for node in sorted(edges):
        if node not in indices:
            visit(node)
    return tuple(sorted(result, key=lambda row: row[0]))


@dataclass(frozen=True, slots=True)
class RankedLoopProofV183:
    component: tuple[int, ...]
    guard_pc: int
    ranking_register: int
    zero_exit_pc: int
    nonzero_body_pc: int

    def to_document(self) -> dict[str, Any]:
        return {
            "component": list(self.component),
            "guard_pc": self.guard_pc,
            "ranking_register": self.ranking_register,
            "zero_exit_pc": self.zero_exit_pc,
            "nonzero_body_pc": self.nonzero_body_pc,
            "ranking_decrement_per_guarded_iteration": 1,
            "other_writes_to_ranking_register_in_component": 0,
        }


@dataclass(frozen=True, slots=True)
class RankedTerminationCertificateV183:
    program_id: str
    register_count: int
    input_width: int
    reachable_instruction_count: int
    loop_proofs: tuple[RankedLoopProofV183, ...]
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ranked_machine_termination_certificate.v183",
            "program_id": self.program_id,
            "register_count": self.register_count,
            "input_width": self.input_width,
            "reachable_instruction_count": self.reachable_instruction_count,
            "loop_proofs": [row.to_document() for row in self.loop_proofs],
            "all_reachable_control_flow_terminates": True,
            "total_for_all_finite_nonnegative_inputs_of_frozen_width": True,
            "finite_carrier_enumeration_used": False,
            "general_program_termination_decided": False,
            "proof_system_complete_for_all_terminating_programs": False,
            "execution_resource_cap_is_not_semantic_totality": True,
            "certificate_id": self.certificate_id,
        }


def _program_id(program: ProgramV182) -> str:
    payload = {
        "schema": "acfqp.ranked_machine_program.v183",
        "program": [list(row) for row in program],
    }
    return domains.extension_content_id_v183(
        domains.CONSTRUCTION_K7_PROGRAM_V183_DOMAIN,
        payload,
    )


def certify_ranked_termination_v183(
    program: ProgramV182,
    *,
    register_count: int,
    input_width: int,
) -> RankedTerminationCertificateV183 | None:
    if (
        type(program) is not tuple
        or not program
        or type(register_count) is not int
        or register_count < 2
        or type(input_width) is not int
        or input_width < 1
    ):
        _fail("V183 termination proof input changed")
    try:
        facts = tuple(
            _successors_and_writer(
                program,
                pc,
                register_count=register_count,
                input_width=input_width,
            )
            for pc in range(len(program))
        )
    except OpenWorldRankedMachineV183Error:
        return None
    edges = {pc: facts[pc][0] for pc in range(len(program))}
    if _reachable(edges) != frozenset(range(len(program))):
        return None
    components = _strong_components(edges)
    loop_proofs: list[RankedLoopProofV183] = []
    for component in components:
        cyclic = len(component) > 1 or component[0] in edges[component[0]]
        if not cyclic:
            continue
        members = set(component)
        guards = [pc for pc in component if program[pc][0] == DECJZ]
        if len(guards) != 1:
            return None
        guard = guards[0]
        rank = program[guard][1]
        zero_target, nonzero_target = program[guard][2:]
        if zero_target in members or nonzero_target not in members:
            return None
        if any(
            target not in members
            for pc in component
            if pc != guard
            for target in edges[pc]
        ):
            return None
        if any(
            facts[pc][1] == rank
            for pc in component
            if pc != guard
        ):
            return None
        loop_proofs.append(
            RankedLoopProofV183(
                component,
                guard,
                rank,
                zero_target,
                nonzero_target,
            )
        )
    component_by_pc = {
        pc: index for index, component in enumerate(components) for pc in component
    }
    halting_components = {
        component_by_pc[pc] for pc, row in enumerate(program) if row[0] == HALT
    }
    component_edges = {
        index: {
            component_by_pc[target]
            for pc in component
            for target in edges[pc]
            if component_by_pc[target] != index
        }
        for index, component in enumerate(components)
    }
    memo: dict[int, bool] = {}

    def reaches_halt(index: int) -> bool:
        if index in memo:
            return memo[index]
        memo[index] = index in halting_components or (
            bool(component_edges[index])
            and all(reaches_halt(target) for target in component_edges[index])
        )
        return memo[index]

    if not reaches_halt(component_by_pc[0]):
        return None
    program_id = _program_id(program)
    payload = {
        "schema": "acfqp.ranked_machine_termination_certificate.v183",
        "program_id": program_id,
        "register_count": register_count,
        "input_width": input_width,
        "reachable_instruction_count": len(program),
        "loop_proofs": [row.to_document() for row in loop_proofs],
        "all_reachable_control_flow_terminates": True,
        "total_for_all_finite_nonnegative_inputs_of_frozen_width": True,
        "finite_carrier_enumeration_used": False,
        "general_program_termination_decided": False,
        "proof_system_complete_for_all_terminating_programs": False,
        "execution_resource_cap_is_not_semantic_totality": True,
    }
    return RankedTerminationCertificateV183(
        program_id,
        register_count,
        input_width,
        len(program),
        tuple(loop_proofs),
        domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_TERMINATION_CERTIFICATE_V183_DOMAIN,
            payload,
        ),
    )


@dataclass(frozen=True, slots=True)
class RankedMachineExecutionV183:
    halted: bool
    resource_cap_exhausted: bool
    output: int | None
    steps: int
    read_dependencies: tuple[int, ...]


def execute_ranked_program_v183(
    program: ProgramV182,
    *,
    state: Sequence[int],
    action: Sequence[int],
    register_count: int,
    resource_step_cap: int,
) -> RankedMachineExecutionV183:
    certificate = certify_ranked_termination_v183(
        program,
        register_count=register_count,
        input_width=len(state) + len(action),
    )
    if certificate is None:
        _fail("V183 execution requires a ranked-total program")
    if (
        type(resource_step_cap) is not int
        or resource_step_cap <= 0
        or not state
        or not action
        or any(type(value) is not int or value < 0 for value in (*state, *action))
    ):
        _fail("V183 execution input changed")
    inputs = tuple(state) + tuple(action)
    registers = [0] * register_count
    dependencies: set[int] = set()
    pc = 0
    steps = 0
    while steps < resource_step_cap:
        instruction = program[pc]
        opcode = instruction[0]
        steps += 1
        if opcode == HALT:
            return RankedMachineExecutionV183(
                True,
                False,
                registers[instruction[1]],
                steps,
                tuple(sorted(dependencies)),
            )
        if opcode == READ:
            registers[instruction[1]] = inputs[instruction[2]]
            dependencies.add(instruction[2])
            pc += 1
        elif opcode == CONST:
            registers[instruction[1]] = instruction[2]
            pc += 1
        elif opcode == INC:
            registers[instruction[1]] += 1
            pc += 1
        elif opcode == ISZERO:
            registers[instruction[1]] = int(registers[instruction[2]] == 0)
            pc += 1
        elif opcode in {ADD, SUBSAT, XOR, EQ, LT}:
            left, right = registers[instruction[2]], registers[instruction[3]]
            if opcode == ADD:
                value = left + right
            elif opcode == SUBSAT:
                value = max(0, left - right)
            elif opcode == XOR:
                value = left ^ right
            elif opcode == EQ:
                value = int(left == right)
            else:
                value = int(left < right)
            registers[instruction[1]] = value
            pc += 1
        elif opcode == DECJZ:
            if registers[instruction[1]] == 0:
                pc = instruction[2]
            else:
                registers[instruction[1]] -= 1
                pc = instruction[3]
        elif opcode == JUMP:
            pc = instruction[1]
        else:  # certificate excludes all other opcodes
            raise AssertionError(opcode)
    return RankedMachineExecutionV183(
        False,
        True,
        None,
        steps,
        tuple(sorted(dependencies)),
    )


def _atomic_programs(
    *,
    input_width: int,
    register_count: int,
    constants: Sequence[int],
    maximum_loop_increment_repetitions: int,
) -> Iterator[ProgramV182]:
    for constant in constants:
        yield ((CONST, 0, constant), (HALT, 0))
    for source in range(input_width):
        yield ((READ, 0, source), (HALT, 0))
        yield ((READ, 0, source), (INC, 0), (HALT, 0))
        if register_count >= 2:
            yield ((READ, 0, source), (ISZERO, 1, 0), (HALT, 1))
    if register_count >= 3:
        for left in range(input_width):
            for right in range(input_width):
                for opcode in (ADD, SUBSAT, XOR, EQ, LT):
                    yield (
                        (READ, 0, left),
                        (READ, 1, right),
                        (opcode, 2, 0, 1),
                        (HALT, 2),
                    )
        for source in range(input_width):
            for offset in constants:
                for repetitions in range(1, maximum_loop_increment_repetitions + 1):
                    halt_pc = 4 + repetitions
                    yield (
                        (READ, 0, source),
                        (CONST, 1, offset),
                        (DECJZ, 0, halt_pc, 3),
                        *((INC, 1),) * repetitions,
                        (JUMP, 2),
                        (HALT, 1),
                    )


def enumerate_ranked_candidates_v183(
    *,
    input_width: int,
    register_count: int,
    constants: Sequence[int],
    maximum_loop_increment_repetitions: int,
    archive: Iterable[ProgramV182] = (),
) -> Iterator[tuple[ProgramV182, bool]]:
    seen: set[ProgramV182] = set()
    for program, from_archive in (
        *((tuple(row), True) for row in archive),
        *((row, False) for row in _atomic_programs(
            input_width=input_width,
            register_count=register_count,
            constants=tuple(sorted(set(constants))),
            maximum_loop_increment_repetitions=maximum_loop_increment_repetitions,
        )),
    ):
        if program in seen:
            continue
        seen.add(program)
        if certify_ranked_termination_v183(
            program,
            register_count=register_count,
            input_width=input_width,
        ) is not None:
            yield program, from_archive


@dataclass(frozen=True, slots=True)
class RankedSynthesizedProgramV183:
    program: ProgramV182
    termination: RankedTerminationCertificateV183
    residual_values: tuple[int, ...]
    read_dependencies: tuple[tuple[str, int], ...]
    enumeration_events: int
    archive_reference_used: bool

    @property
    def program_id(self) -> str:
        return self.termination.program_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ranked_machine_synthesized_program.v183",
            "program": [list(row) for row in self.program],
            "program_id": self.program_id,
            "termination_certificate": self.termination.to_document(),
            "residual_values": list(self.residual_values),
            "read_dependencies": [list(row) for row in self.read_dependencies],
            "enumeration_events": self.enumeration_events,
            "archive_reference_used": self.archive_reference_used,
            "archive_candidate_revalidated_on_every_current_row": (
                self.archive_reference_used
            ),
            "finite_carrier_enumeration_used": False,
            "general_program_termination_decided": False,
            "proof_language_program_length_unbounded": True,
            "current_occurrence_candidate_set_finite": True,
            "generic_ranked_program_schema_enumerated": True,
            "domain_specific_whole_program_template_used": False,
            "occurrence_search_resource_bounded": True,
        }


def _dependencies(indices: Iterable[int], state_width: int) -> tuple[tuple[str, int], ...]:
    return tuple(
        ("S", index) if index < state_width else ("A", index - state_width)
        for index in sorted(set(indices))
    )


def synthesize_ranked_scalar_program_v183(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    maximum_enumeration_events: int,
    resource_step_cap: int,
    maximum_loop_increment_repetitions: int,
    register_count: int = 3,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> RankedSynthesizedProgramV183:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or type(maximum_enumeration_events) is not int
        or maximum_enumeration_events <= 0
        or type(maximum_residual_support) is not int
        or maximum_residual_support < 1
    ):
        _fail("V183 synthesis rows or resource profile changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if any(len(row.state) != state_width or len(row.action) != action_width for row in rows):
        _fail("V183 synthesis rows cross opaque schemas")
    constants = tuple(sorted({0, 1, *(value for row in rows for value in (*row.state, *row.action, row.target))}))
    targets = tuple(row.target for row in rows)
    best: tuple[tuple[Any, ...], ProgramV182, RankedTerminationCertificateV183, tuple[int, ...], tuple[int, ...], int, bool] | None = None
    events = 0
    semantics: set[tuple[int, ...]] = set()
    for program, from_archive in enumerate_ranked_candidates_v183(
        input_width=state_width + action_width,
        register_count=register_count,
        constants=constants,
        maximum_loop_increment_repetitions=maximum_loop_increment_repetitions,
        archive=archive,
    ):
        events += 1
        if events > maximum_enumeration_events:
            break
        certificate = certify_ranked_termination_v183(
            program,
            register_count=register_count,
            input_width=state_width + action_width,
        )
        if certificate is None:
            raise AssertionError("candidate enumerator admitted an uncertified program")
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
        if any(not item.halted or item.output is None for item in executions):
            continue
        outputs = tuple(int(item.output) for item in executions)
        if outputs in semantics:
            continue
        semantics.add(outputs)
        residuals = tuple(sorted({target - output for output, target in zip(outputs, targets)}))
        if outputs == targets:
            residuals = ()
        elif not (1 <= len(residuals) <= maximum_residual_support):
            continue
        dependencies = tuple(sorted({index for row in executions for index in row.read_dependencies}))
        rank = (
            0 if outputs == targets else 1,
            len(program) + len(residuals),
            len(residuals),
            len(program),
            program_bytes_v182(program),
        )
        candidate = (rank, program, certificate, residuals, dependencies, events, from_archive)
        if best is None or candidate[0] < best[0]:
            best = candidate
            if outputs == targets:
                break
    if best is None:
        _fail("V183 resource cap found no ranked-total supported program")
    _, program, certificate, residuals, dependencies, used_events, from_archive = best
    return RankedSynthesizedProgramV183(
        program,
        certificate,
        residuals,
        _dependencies(dependencies, state_width),
        used_events,
        from_archive,
    )


@dataclass(frozen=True, slots=True)
class RankedCompiledWorldModelV183:
    state_width: int
    action_width: int
    legal_actions: tuple[tuple[int, ...], ...]
    register_count: int
    resource_step_cap: int
    coordinates: tuple[RankedSynthesizedProgramV183, ...]
    terminal_synthesis: RankedSynthesizedProgramV183
    source_observation_ids: tuple[str, ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
    compiled_model_id: str

    def _run(self, program: ProgramV182, state: Sequence[int], action: Sequence[int]) -> int:
        result = execute_ranked_program_v183(
            program,
            state=state,
            action=action,
            register_count=self.register_count,
            resource_step_cap=self.resource_step_cap,
        )
        if not result.halted or result.output is None:
            _fail("V183 execution resource cap exhausted")
        return result.output

    def terminal(self, state: Sequence[int]) -> bool:
        if len(state) != self.state_width or any(type(value) is not int or value < 0 for value in state):
            _fail("V183 state crossed its opaque schema")
        value = self._run(self.terminal_synthesis.program, state, (0,) * self.action_width)
        if value not in {0, 1}:
            _fail("V183 terminal program is not boolean")
        return bool(value)

    def predict_support(self, state: Sequence[int], action: Sequence[int]) -> tuple[tuple[int, ...], ...]:
        if (
            len(state) != self.state_width
            or len(action) != self.action_width
            or any(type(value) is not int or value < 0 for value in (*state, *action))
            or tuple(action) not in self.legal_actions
        ):
            _fail("V183 prediction crossed its opaque schema")
        supports = []
        for coordinate in self.coordinates:
            base = self._run(coordinate.program, state, action)
            residuals = coordinate.residual_values or (0,)
            values = tuple(sorted({base + value for value in residuals if base + value >= 0}))
            if not values:
                _fail("V183 stochastic support became empty")
            supports.append(values)
        return tuple(product(*supports))

    def covers(self, row: RawMachineTransitionV182) -> bool:
        return row.successor in self.predict_support(row.state, row.action) and self.terminal(row.successor) is row.terminal

    def reusable_program_archive(self) -> tuple[ProgramV182, ...]:
        return tuple(dict.fromkeys([*(row.program for row in self.coordinates), self.terminal_synthesis.program]))

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ranked_machine_compiled_world_model.v183",
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
            "all_programs_total_over_unbounded_nonnegative_input_values": True,
            "finite_carrier_enumeration_used": False,
            "general_program_termination_decided": False,
            "proof_system_complete_for_all_terminating_programs": False,
            "resource_cap_failure_is_distinct_from_nontermination": True,
            "named_domain_family_used": False,
            "named_layout_used": False,
            "domain_specific_whole_program_template_used": False,
            "generic_ranked_program_schema_enumerated": True,
            "proof_language_program_length_unbounded": True,
            "current_occurrence_candidate_set_finite": True,
            "occurrence_search_resource_bounded": True,
            "compiled_model_id": self.compiled_model_id,
        }


def compile_ranked_machine_world_model_v183(
    observations: Sequence[RawMachineTransitionV182],
    *,
    maximum_enumeration_events_per_scalar: int,
    resource_step_cap: int,
    maximum_loop_increment_repetitions: int,
    register_count: int = 3,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> RankedCompiledWorldModelV183:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V183 compilation requires at least eight raw transitions")
    state_width = len(observations[0].state)
    action_width = len(observations[0].action)
    if len({row.observation_id for row in observations}) != len(observations) or any(
        len(row.state) != state_width
        or len(row.successor) != state_width
        or len(row.action) != action_width
        for row in observations
    ):
        _fail("V183 observations are duplicated or cross opaque schemas")
    frozen_archive = tuple(archive)
    legal_actions = tuple(sorted({row.action for row in observations}))
    coordinates = tuple(
        synthesize_ranked_scalar_program_v183(
            tuple(MachineSynthesisRowV182(row.state, row.action, row.successor[index]) for row in observations),
            maximum_enumeration_events=maximum_enumeration_events_per_scalar,
            resource_step_cap=resource_step_cap,
            maximum_loop_increment_repetitions=maximum_loop_increment_repetitions,
            register_count=register_count,
            maximum_residual_support=maximum_residual_support,
            archive=frozen_archive,
        )
        for index in range(state_width)
    )
    terminal = synthesize_ranked_scalar_program_v183(
        tuple(MachineSynthesisRowV182(row.successor, (0,) * action_width, int(row.terminal)) for row in observations),
        maximum_enumeration_events=maximum_enumeration_events_per_scalar,
        resource_step_cap=resource_step_cap,
        maximum_loop_increment_repetitions=maximum_loop_increment_repetitions,
        register_count=register_count,
        maximum_residual_support=1,
        archive=frozen_archive,
    )
    if terminal.residual_values:
        _fail("V183 terminal program cannot retain a stochastic residual")
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for index, row in enumerate(coordinates):
        groups.setdefault(row.read_dependencies, []).append(index)
    boundaries = tuple(sorted((tuple(items) for items in groups.values()), key=lambda row: (row[0], len(row))))
    payload = {
        "schema": "acfqp.ranked_machine_compiled_world_model.v183",
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
        "all_programs_total_over_unbounded_nonnegative_input_values": True,
        "finite_carrier_enumeration_used": False,
        "general_program_termination_decided": False,
        "proof_system_complete_for_all_terminating_programs": False,
        "resource_cap_failure_is_distinct_from_nontermination": True,
        "named_domain_family_used": False,
        "named_layout_used": False,
        "domain_specific_whole_program_template_used": False,
        "generic_ranked_program_schema_enumerated": True,
        "proof_language_program_length_unbounded": True,
        "current_occurrence_candidate_set_finite": True,
        "occurrence_search_resource_bounded": True,
    }
    model_id = domains.extension_content_id_v183(
        domains.CONSTRUCTION_K7_COMPILED_MODEL_V183_DOMAIN,
        payload,
    )
    return RankedCompiledWorldModelV183(
        state_width,
        action_width,
        legal_actions,
        register_count,
        resource_step_cap,
        coordinates,
        terminal,
        tuple(row.observation_id for row in observations),
        boundaries,
        model_id,
    )


__all__ = (
    "OpenWorldRankedMachineV183Error",
    "RankedCompiledWorldModelV183",
    "RankedMachineExecutionV183",
    "RankedSynthesizedProgramV183",
    "RankedTerminationCertificateV183",
    "certify_ranked_termination_v183",
    "compile_ranked_machine_world_model_v183",
    "enumerate_ranked_candidates_v183",
    "execute_ranked_program_v183",
    "synthesize_ranked_scalar_program_v183",
)
