"""Resource-bounded synthesis over an unbounded counter-machine language.

V181 enumerates a finite typed expression grammar.  V182 instead registers a
small, domain-agnostic counter-machine instruction set with jumps and exact
integer registers.  Program descriptions have no language-level length bound;
each synthesis occurrence supplies a finite search/event/step budget.  The
``DECJZ`` core is sufficient for arbitrary counter-machine composition, while
straight-line arithmetic instructions are conservative search accelerators.

The module receives only opaque integer state/action rows and target values.
It contains no domain-family switch, layout table, named transition primitive,
or whole-program template.  A finite occurrence is not a universal discovery
claim: programs outside its frozen resource budget remain unsearched.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Any, Iterable, Iterator, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182 as domains


InstructionV182 = tuple[int, ...]
ProgramV182 = tuple[InstructionV182, ...]

HALT = 0
READ = 1
CONST = 2
INC = 3
ISZERO = 4
ADD = 5
SUBSAT = 6
MOD = 7
XOR = 8
EQ = 9
LT = 10
DECJZ = 11
JUMP = 12

OPCODE_NAMES = (
    "HALT",
    "READ",
    "CONST",
    "INC",
    "ISZERO",
    "ADD",
    "SUBSAT",
    "MOD",
    "XOR",
    "EQ",
    "LT",
    "DECJZ",
    "JUMP",
)


class OpenWorldUniversalMachineV182Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldUniversalMachineV182Error(message)


@dataclass(frozen=True, slots=True)
class MachineExecutionV182:
    halted: bool
    output: int | None
    steps: int
    read_dependencies: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MachineSynthesisRowV182:
    state: tuple[int, ...]
    action: tuple[int, ...]
    target: int

    def __post_init__(self) -> None:
        if (
            type(self.state) is not tuple
            or not self.state
            or type(self.action) is not tuple
            or not self.action
            or any(type(value) is not int or value < 0 for value in self.state)
            or any(type(value) is not int or value < 0 for value in self.action)
            or type(self.target) is not int
            or self.target < 0
        ):
            _fail("V182 synthesis row is not one opaque nonnegative integer row")


@dataclass(frozen=True, slots=True)
class SynthesizedMachineProgramV182:
    program: ProgramV182
    program_id: str
    instruction_count: int
    enumeration_events: int
    exact_on_all_rows: bool
    residual_values: tuple[int, ...]
    read_dependencies: tuple[tuple[str, int], ...]
    maximum_execution_steps: int
    archive_reference_used: bool

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_universal_machine_program.v182",
            "program": [list(row) for row in self.program],
            "program_id": self.program_id,
            "instruction_count": self.instruction_count,
            "enumeration_events": self.enumeration_events,
            "exact_on_all_rows": self.exact_on_all_rows,
            "residual_values": list(self.residual_values),
            "read_dependencies": [list(row) for row in self.read_dependencies],
            "maximum_execution_steps": self.maximum_execution_steps,
            "archive_reference_used": self.archive_reference_used,
            "archive_mdl_discount_used": False,
            "archive_reference_revalidated_on_all_current_rows": (
                self.archive_reference_used
            ),
            "domain_specific_primitive_used": False,
            "whole_program_template_used": False,
            "named_layout_used": False,
            "language_program_length_unbounded": True,
            "occurrence_search_resource_bounded": True,
        }


def program_bytes_v182(program: ProgramV182) -> bytes:
    _validate_program(program)
    return json.dumps(program, separators=(",", ":"), ensure_ascii=True).encode()


def _register(value: Any, register_count: int, label: str) -> int:
    if type(value) is not int or not 0 <= value < register_count:
        _fail(f"{label} is outside the V182 register file")
    return value


def _validate_program(program: ProgramV182) -> None:
    if type(program) is not tuple or not program:
        _fail("V182 program must be one nonempty instruction tuple")
    for instruction in program:
        if (
            type(instruction) is not tuple
            or not instruction
            or any(type(value) is not int for value in instruction)
            or not 0 <= instruction[0] < len(OPCODE_NAMES)
        ):
            _fail("V182 instruction encoding changed")


def execute_program_v182(
    program: ProgramV182,
    *,
    state: Sequence[int],
    action: Sequence[int],
    register_count: int,
    maximum_steps: int,
    maximum_register_value: int = 1_000_000,
) -> MachineExecutionV182:
    _validate_program(program)
    if (
        type(register_count) is not int
        or register_count < 2
        or type(maximum_steps) is not int
        or maximum_steps <= 0
        or type(maximum_register_value) is not int
        or maximum_register_value <= 0
        or any(type(value) is not int or value < 0 for value in (*state, *action))
    ):
        _fail("V182 machine execution profile changed")
    inputs = tuple(state) + tuple(action)
    registers = [0] * register_count
    dependencies: set[int] = set()
    pc = 0
    steps = 0
    while 0 <= pc < len(program) and steps < maximum_steps:
        instruction = program[pc]
        opcode = instruction[0]
        steps += 1
        if opcode == HALT:
            if len(instruction) != 2:
                _fail("HALT arity changed")
            source = _register(instruction[1], register_count, "HALT source")
            return MachineExecutionV182(
                True,
                registers[source],
                steps,
                tuple(sorted(dependencies)),
            )
        if opcode == READ:
            if len(instruction) != 3:
                _fail("READ arity changed")
            target = _register(instruction[1], register_count, "READ target")
            source = instruction[2]
            if not 0 <= source < len(inputs):
                _fail("READ source is outside the opaque input vector")
            registers[target] = inputs[source]
            dependencies.add(source)
            pc += 1
        elif opcode == CONST:
            if len(instruction) != 3 or instruction[2] < 0:
                _fail("CONST encoding changed")
            registers[_register(instruction[1], register_count, "CONST target")] = (
                instruction[2]
            )
            pc += 1
        elif opcode == INC:
            if len(instruction) != 2:
                _fail("INC arity changed")
            target = _register(instruction[1], register_count, "INC target")
            registers[target] += 1
            pc += 1
        elif opcode == ISZERO:
            if len(instruction) != 3:
                _fail("ISZERO arity changed")
            target = _register(instruction[1], register_count, "ISZERO target")
            source = _register(instruction[2], register_count, "ISZERO source")
            registers[target] = int(registers[source] == 0)
            pc += 1
        elif opcode in {ADD, SUBSAT, MOD, XOR, EQ, LT}:
            if len(instruction) != 4:
                _fail("binary instruction arity changed")
            target = _register(instruction[1], register_count, "binary target")
            left = registers[
                _register(instruction[2], register_count, "binary left")
            ]
            right = registers[
                _register(instruction[3], register_count, "binary right")
            ]
            if opcode == ADD:
                value = left + right
            elif opcode == SUBSAT:
                value = max(0, left - right)
            elif opcode == MOD:
                if right == 0:
                    return MachineExecutionV182(
                        False, None, steps, tuple(sorted(dependencies))
                    )
                value = left % right
            elif opcode == XOR:
                value = left ^ right
            elif opcode == EQ:
                value = int(left == right)
            else:
                value = int(left < right)
            registers[target] = value
            pc += 1
        elif opcode == DECJZ:
            if len(instruction) != 4:
                _fail("DECJZ arity changed")
            source = _register(instruction[1], register_count, "DECJZ source")
            zero_target, nonzero_target = instruction[2:]
            if not (
                0 <= zero_target < len(program)
                and 0 <= nonzero_target < len(program)
            ):
                _fail("DECJZ target is outside the program")
            if registers[source] == 0:
                pc = zero_target
            else:
                registers[source] -= 1
                pc = nonzero_target
        elif opcode == JUMP:
            if len(instruction) != 2 or not 0 <= instruction[1] < len(program):
                _fail("JUMP target is outside the program")
            pc = instruction[1]
        else:  # pragma: no cover - opcode range validated above
            raise AssertionError(opcode)
        if any(value > maximum_register_value for value in registers):
            return MachineExecutionV182(
                False, None, steps, tuple(sorted(dependencies))
            )
    return MachineExecutionV182(False, None, steps, tuple(sorted(dependencies)))


def _instruction_variants(
    *,
    program_length: int,
    pc: int,
    register_count: int,
    input_width: int,
    constants: Sequence[int],
) -> tuple[InstructionV182, ...]:
    if pc == program_length - 1:
        return tuple((HALT, register) for register in range(register_count))
    rows: list[InstructionV182] = []
    rows.extend(
        (READ, register, source)
        for register in range(register_count)
        for source in range(input_width)
    )
    rows.extend(
        (CONST, register, value)
        for register in range(register_count)
        for value in constants
    )
    rows.extend((INC, register) for register in range(register_count))
    rows.extend(
        (ISZERO, target, source)
        for target in range(register_count)
        for source in range(register_count)
    )
    for opcode in (ADD, SUBSAT, MOD, XOR, EQ, LT):
        rows.extend(
            (opcode, target, left, right)
            for target in range(register_count)
            for left in range(register_count)
            for right in range(register_count)
        )
    rows.extend(
        (DECJZ, register, zero_target, nonzero_target)
        for register in range(register_count)
        for zero_target in range(program_length)
        for nonzero_target in range(program_length)
    )
    rows.extend((JUMP, target) for target in range(program_length))
    return tuple(rows)


def enumerate_programs_v182(
    *,
    maximum_instruction_count: int,
    register_count: int,
    input_width: int,
    constants: Sequence[int],
) -> Iterator[ProgramV182]:
    if (
        type(maximum_instruction_count) is not int
        or maximum_instruction_count < 1
        or type(register_count) is not int
        or register_count < 2
        or type(input_width) is not int
        or input_width < 1
        or type(constants) not in {tuple, list}
        or any(type(value) is not int or value < 0 for value in constants)
    ):
        _fail("V182 enumeration profile changed")
    frozen_constants = tuple(sorted(set(constants)))
    for length in range(1, maximum_instruction_count + 1):
        variants = tuple(
            _instruction_variants(
                program_length=length,
                pc=pc,
                register_count=register_count,
                input_width=input_width,
                constants=frozen_constants,
            )
            for pc in range(length)
        )
        yield from product(*variants)


def _program_id(program: ProgramV182) -> str:
    payload = {
        "schema": "acfqp.open_world_universal_machine_program_identity.v182",
        "program": [list(row) for row in program],
    }
    return domains.extension_content_id_v182(
        domains.CONSTRUCTION_K7_MACHINE_PROGRAM_V182_DOMAIN,
        payload,
    )


def _dependencies(
    input_indices: Iterable[int], state_width: int
) -> tuple[tuple[str, int], ...]:
    return tuple(
        ("S", index) if index < state_width else ("A", index - state_width)
        for index in sorted(set(input_indices))
    )


def synthesize_scalar_program_v182(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    maximum_enumeration_events: int,
    maximum_instruction_count: int,
    maximum_execution_steps: int,
    register_count: int = 2,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> SynthesizedMachineProgramV182:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or type(maximum_enumeration_events) is not int
        or maximum_enumeration_events <= 0
        or type(maximum_residual_support) is not int
        or maximum_residual_support < 1
    ):
        _fail("V182 synthesis profile or rows changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if any(
        len(row.state) != state_width or len(row.action) != action_width
        for row in rows
    ):
        _fail("V182 rows cross opaque input schemas")
    constants = tuple(
        sorted(
            {
                0,
                1,
                *(value for row in rows for value in (*row.state, *row.action)),
                *(row.target for row in rows),
            }
        )
    )
    targets = tuple(row.target for row in rows)
    frozen_archive = frozenset(tuple(program) for program in archive)
    for program in frozen_archive:
        _validate_program(program)
    best_residual: tuple[tuple[Any, ...], ProgramV182, tuple[int, ...], tuple[int, ...]] | None = None
    seen_semantics: set[tuple[int, ...]] = set()
    events = 0
    for program in enumerate_programs_v182(
        maximum_instruction_count=maximum_instruction_count,
        register_count=register_count,
        input_width=state_width + action_width,
        constants=constants,
    ):
        events += 1
        if events > maximum_enumeration_events:
            break
        executions = tuple(
            execute_program_v182(
                program,
                state=row.state,
                action=row.action,
                register_count=register_count,
                maximum_steps=maximum_execution_steps,
            )
            for row in rows
        )
        if any(not item.halted or item.output is None for item in executions):
            continue
        outputs = tuple(int(item.output) for item in executions)
        if outputs in seen_semantics:
            continue
        seen_semantics.add(outputs)
        dependencies = tuple(
            sorted({index for item in executions for index in item.read_dependencies})
        )
        if outputs == targets:
            return SynthesizedMachineProgramV182(
                program,
                _program_id(program),
                len(program),
                events,
                True,
                (),
                _dependencies(dependencies, state_width),
                maximum_execution_steps,
                program in frozen_archive,
            )
        residuals = tuple(
            sorted({target - output for output, target in zip(outputs, targets)})
        )
        if 1 <= len(residuals) <= maximum_residual_support:
            rank = (
                len(program) + len(residuals),
                len(residuals),
                len(program),
                program_bytes_v182(program),
            )
            candidate = (rank, program, residuals, dependencies)
            if best_residual is None or candidate[0] < best_residual[0]:
                best_residual = candidate
    if best_residual is None:
        _fail("V182 occurrence search resource cap found no supported program")
    _, program, residuals, dependencies = best_residual
    return SynthesizedMachineProgramV182(
        program,
        _program_id(program),
        len(program),
        events,
        False,
        residuals,
        _dependencies(dependencies, state_width),
        maximum_execution_steps,
        program in frozen_archive,
    )


__all__ = (
    "ADD",
    "CONST",
    "DECJZ",
    "EQ",
    "HALT",
    "INC",
    "ISZERO",
    "JUMP",
    "LT",
    "MOD",
    "MachineExecutionV182",
    "MachineSynthesisRowV182",
    "OpenWorldUniversalMachineV182Error",
    "ProgramV182",
    "READ",
    "SUBSAT",
    "SynthesizedMachineProgramV182",
    "XOR",
    "enumerate_programs_v182",
    "execute_program_v182",
    "program_bytes_v182",
    "synthesize_scalar_program_v182",
)
