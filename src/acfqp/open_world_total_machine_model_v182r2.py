"""Compile only counter-machine programs total on a registered finite carrier.

The frozen V182r1 compiler required halting only on observed synthesis rows.
That admitted a branch program which diverged on a later confirmation row.
V182r2 is additive: every candidate must halt over the Cartesian product of
the public state moduli and legal action vectors before it can be selected.
The check is exhaustive for this registered finite carrier, not a claim of
termination over arbitrary integers or arbitrary future schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182 as domains_v182
from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_universal_machine_v182 import (
    MachineSynthesisRowV182,
    ProgramV182,
    SynthesizedMachineProgramV182,
    enumerate_programs_v182,
    execute_program_v182,
    program_bytes_v182,
)


class OpenWorldTotalMachineModelV182R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldTotalMachineModelV182R2Error(message)


def _program_id(program: ProgramV182) -> str:
    payload = {
        "schema": "acfqp.open_world_universal_machine_program_identity.v182",
        "program": [list(row) for row in program],
    }
    return domains_v182.extension_content_id_v182(
        domains_v182.CONSTRUCTION_K7_MACHINE_PROGRAM_V182_DOMAIN,
        payload,
    )


def _dependencies(
    input_indices: Iterable[int], state_width: int
) -> tuple[tuple[str, int], ...]:
    return tuple(
        ("S", index) if index < state_width else ("A", index - state_width)
        for index in sorted(set(input_indices))
    )


def _state_carrier(state_moduli: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    if (
        type(state_moduli) not in {tuple, list}
        or not state_moduli
        or any(type(value) is not int or value < 2 for value in state_moduli)
    ):
        _fail("V182r2 state carrier changed")
    return tuple(product(*(range(value) for value in state_moduli)))


def _actions(
    legal_actions: Sequence[Sequence[int]], action_width: int
) -> tuple[tuple[int, ...], ...]:
    if type(legal_actions) not in {tuple, list} or not legal_actions:
        _fail("V182r2 legal action carrier is empty")
    frozen = tuple(tuple(row) for row in legal_actions)
    if (
        len(set(frozen)) != len(frozen)
        or any(
            len(row) != action_width
            or any(type(value) is not int or value < 0 for value in row)
            for row in frozen
        )
    ):
        _fail("V182r2 legal action carrier changed")
    return frozen


@dataclass(frozen=True, slots=True)
class TotalityCertificateV182R2:
    program_id: str
    state_moduli: tuple[int, ...]
    legal_actions: tuple[tuple[int, ...], ...]
    input_count: int
    maximum_execution_steps: int
    maximum_observed_steps: int
    total_on_full_registered_finite_carrier: bool
    totality_certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_machine_totality_certificate.v182r2",
            "program_id": self.program_id,
            "state_moduli": list(self.state_moduli),
            "legal_actions": [list(row) for row in self.legal_actions],
            "input_count": self.input_count,
            "maximum_execution_steps": self.maximum_execution_steps,
            "maximum_observed_steps": self.maximum_observed_steps,
            "total_on_full_registered_finite_carrier": (
                self.total_on_full_registered_finite_carrier
            ),
            "total_over_unbounded_integer_inputs_claimed": False,
            "total_over_unregistered_schemas_claimed": False,
            "totality_certificate_id": self.totality_certificate_id,
        }


def certify_program_totality_v182r2(
    program: ProgramV182,
    *,
    state_moduli: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    register_count: int,
    maximum_execution_steps: int,
) -> TotalityCertificateV182R2 | None:
    states = _state_carrier(state_moduli)
    if not states:
        _fail("V182r2 state carrier unexpectedly empty")
    actions = _actions(legal_actions, len(tuple(legal_actions)[0]))
    maximum_observed_steps = 0
    for state in states:
        for action in actions:
            execution = execute_program_v182(
                program,
                state=state,
                action=action,
                register_count=register_count,
                maximum_steps=maximum_execution_steps,
            )
            maximum_observed_steps = max(maximum_observed_steps, execution.steps)
            if not execution.halted or execution.output is None:
                return None
    program_id = _program_id(program)
    payload = {
        "schema": "acfqp.open_world_machine_totality_certificate.v182r2",
        "program_id": program_id,
        "state_moduli": list(state_moduli),
        "legal_actions": [list(row) for row in actions],
        "input_count": len(states) * len(actions),
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_observed_steps": maximum_observed_steps,
        "total_on_full_registered_finite_carrier": True,
        "total_over_unbounded_integer_inputs_claimed": False,
        "total_over_unregistered_schemas_claimed": False,
    }
    certificate_id = domains.extension_content_id_v182r2(
        domains.CONSTRUCTION_K7_TOTALITY_CERTIFICATE_V182R2_DOMAIN,
        payload,
    )
    return TotalityCertificateV182R2(
        program_id,
        tuple(state_moduli),
        actions,
        len(states) * len(actions),
        maximum_execution_steps,
        maximum_observed_steps,
        True,
        certificate_id,
    )


@dataclass(frozen=True, slots=True)
class TotalSynthesizedMachineProgramV182R2:
    synthesis: SynthesizedMachineProgramV182
    totality: TotalityCertificateV182R2

    def to_document(self) -> dict[str, Any]:
        return {
            "synthesis": self.synthesis.to_document(),
            "totality": self.totality.to_document(),
        }


def synthesize_total_scalar_program_v182r2(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    state_moduli: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    maximum_enumeration_events: int,
    maximum_instruction_count: int,
    maximum_execution_steps: int,
    register_count: int = 2,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> TotalSynthesizedMachineProgramV182R2:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or type(maximum_enumeration_events) is not int
        or maximum_enumeration_events <= 0
        or type(maximum_residual_support) is not int
        or maximum_residual_support < 1
    ):
        _fail("V182r2 synthesis profile or rows changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if len(tuple(state_moduli)) != state_width or any(
        len(row.state) != state_width or len(row.action) != action_width
        for row in rows
    ):
        _fail("V182r2 synthesis rows cross the registered carrier")
    actions = _actions(legal_actions, action_width)
    states = _state_carrier(state_moduli)
    if any(
        row.state not in states or row.action not in actions
        for row in rows
    ):
        _fail("V182r2 synthesis row is outside the registered carrier")
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
    best_residual: tuple[
        tuple[Any, ...],
        ProgramV182,
        tuple[int, ...],
        tuple[int, ...],
        TotalityCertificateV182R2,
    ] | None = None
    seen_total_semantics: set[tuple[int, ...]] = set()
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
        if outputs in seen_total_semantics:
            continue
        totality = certify_program_totality_v182r2(
            program,
            state_moduli=state_moduli,
            legal_actions=actions,
            register_count=register_count,
            maximum_execution_steps=maximum_execution_steps,
        )
        if totality is None:
            continue
        seen_total_semantics.add(outputs)
        dependencies = tuple(
            sorted({index for item in executions for index in item.read_dependencies})
        )
        if outputs == targets:
            synthesis = SynthesizedMachineProgramV182(
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
            return TotalSynthesizedMachineProgramV182R2(synthesis, totality)
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
            candidate = (
                rank,
                program,
                residuals,
                dependencies,
                totality,
            )
            if best_residual is None or candidate[0] < best_residual[0]:
                best_residual = candidate
    if best_residual is None:
        _fail("V182r2 resource cap found no total supported program")
    _, program, residuals, dependencies, totality = best_residual
    synthesis = SynthesizedMachineProgramV182(
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
    return TotalSynthesizedMachineProgramV182R2(synthesis, totality)


@dataclass(frozen=True, slots=True)
class TotalCompiledMachineCoordinateV182R2:
    coordinate_index: int
    synthesis: TotalSynthesizedMachineProgramV182R2

    def to_document(self) -> dict[str, Any]:
        return {
            "coordinate_index": self.coordinate_index,
            "synthesis": self.synthesis.to_document(),
        }


@dataclass(frozen=True, slots=True)
class TotalCompiledMachineWorldModelV182R2:
    state_moduli: tuple[int, ...]
    legal_actions: tuple[tuple[int, ...], ...]
    register_count: int
    maximum_execution_steps: int
    coordinates: tuple[TotalCompiledMachineCoordinateV182R2, ...]
    terminal_synthesis: TotalSynthesizedMachineProgramV182R2
    source_observation_ids: tuple[str, ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
    compiled_model_id: str

    @property
    def state_width(self) -> int:
        return len(self.state_moduli)

    @property
    def action_width(self) -> int:
        return len(self.legal_actions[0])

    def _validate_state(self, state: Sequence[int]) -> tuple[int, ...]:
        frozen = tuple(state)
        if (
            len(frozen) != self.state_width
            or any(
                type(value) is not int or not 0 <= value < modulus
                for value, modulus in zip(frozen, self.state_moduli, strict=True)
            )
        ):
            _fail("V182r2 state left the registered finite carrier")
        return frozen

    def _run(
        self, program: ProgramV182, state: Sequence[int], action: Sequence[int]
    ) -> int:
        execution = execute_program_v182(
            program,
            state=state,
            action=action,
            register_count=self.register_count,
            maximum_steps=self.maximum_execution_steps,
        )
        if not execution.halted or execution.output is None:
            _fail("V182r2 admitted a non-total compiled program")
        return execution.output

    def terminal(self, state: Sequence[int]) -> bool:
        frozen = self._validate_state(state)
        output = self._run(
            self.terminal_synthesis.synthesis.program,
            frozen,
            (0,) * self.action_width,
        )
        if output not in {0, 1}:
            _fail("V182r2 terminal program is not boolean on its carrier")
        return bool(output)

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        frozen_state = self._validate_state(state)
        frozen_action = tuple(action)
        if frozen_action not in self.legal_actions:
            _fail("V182r2 action left the registered legal carrier")
        supports = []
        for index, coordinate in enumerate(self.coordinates):
            base = self._run(
                coordinate.synthesis.synthesis.program,
                frozen_state,
                frozen_action,
            )
            residuals = coordinate.synthesis.synthesis.residual_values or (0,)
            raw_values = tuple(base + residual for residual in residuals)
            if any(
                not 0 <= value < self.state_moduli[index]
                for value in raw_values
            ):
                _fail("V182r2 coordinate support left the finite carrier")
            values = tuple(sorted(set(raw_values)))
            supports.append(values)
        return tuple(product(*supports))

    def covers(self, row: RawMachineTransitionV182) -> bool:
        try:
            return (
                row.successor in self.predict_support(row.state, row.action)
                and self.terminal(row.successor) is row.terminal
            )
        except OpenWorldTotalMachineModelV182R2Error:
            return False

    def reusable_program_archive(self) -> tuple[ProgramV182, ...]:
        return tuple(
            dict.fromkeys(
                [
                    *(row.synthesis.synthesis.program for row in self.coordinates),
                    self.terminal_synthesis.synthesis.program,
                ]
            )
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_total_machine_compiled_model.v182r2",
            "state_moduli": list(self.state_moduli),
            "state_width": self.state_width,
            "legal_actions": [list(row) for row in self.legal_actions],
            "action_width": self.action_width,
            "register_count": self.register_count,
            "maximum_execution_steps": self.maximum_execution_steps,
            "coordinates": [row.to_document() for row in self.coordinates],
            "terminal_synthesis": self.terminal_synthesis.to_document(),
            "source_observation_ids": list(self.source_observation_ids),
            "source_label_count": len(self.source_observation_ids),
            "factor_boundaries": [list(row) for row in self.factor_boundaries],
            "all_programs_total_on_full_registered_finite_carrier": True,
            "support_closed_on_full_registered_finite_carrier": True,
            "finite_carrier_totality_not_unbounded_totality": True,
            "factor_boundaries_derived_from_machine_read_dependencies": True,
            "layout_names_supplied": False,
            "domain_family_supplied": False,
            "whole_program_template_used": False,
            "finite_candidate_program_catalog_used": False,
            "language_program_length_unbounded": True,
            "occurrence_search_resource_bounded": True,
            "compiled_model_id": self.compiled_model_id,
        }


def _factor_boundaries(
    coordinates: Sequence[TotalCompiledMachineCoordinateV182R2],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for row in coordinates:
        groups.setdefault(
            row.synthesis.synthesis.read_dependencies, []
        ).append(row.coordinate_index)
    return tuple(
        sorted(
            (tuple(indices) for indices in groups.values()),
            key=lambda indices: (indices[0], len(indices)),
        )
    )


def compile_total_machine_world_model_v182r2(
    observations: Sequence[RawMachineTransitionV182],
    *,
    state_moduli: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    maximum_enumeration_events_per_scalar: int,
    maximum_instruction_count: int,
    maximum_execution_steps: int,
    register_count: int = 2,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> TotalCompiledMachineWorldModelV182R2:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V182r2 compilation requires at least eight raw transitions")
    state_moduli_frozen = tuple(state_moduli)
    state_width = len(state_moduli_frozen)
    action_width = len(observations[0].action)
    actions = _actions(legal_actions, action_width)
    if (
        len({row.observation_id for row in observations}) != len(observations)
        or any(
            len(row.state) != state_width
            or len(row.successor) != state_width
            or len(row.action) != action_width
            or row.action not in actions
            or any(
                not 0 <= value < modulus
                for value, modulus in zip(row.state, state_moduli_frozen, strict=True)
            )
            or any(
                not 0 <= value < modulus
                for value, modulus in zip(
                    row.successor, state_moduli_frozen, strict=True
                )
            )
            for row in observations
        )
    ):
        _fail("V182r2 observations cross or leave the registered carrier")
    frozen_archive = tuple(archive)
    coordinates = tuple(
        TotalCompiledMachineCoordinateV182R2(
            index,
            synthesize_total_scalar_program_v182r2(
                tuple(
                    MachineSynthesisRowV182(
                        row.state, row.action, row.successor[index]
                    )
                    for row in observations
                ),
                state_moduli=state_moduli_frozen,
                legal_actions=actions,
                maximum_enumeration_events=maximum_enumeration_events_per_scalar,
                maximum_instruction_count=maximum_instruction_count,
                maximum_execution_steps=maximum_execution_steps,
                register_count=register_count,
                maximum_residual_support=maximum_residual_support,
                archive=frozen_archive,
            ),
        )
        for index in range(state_width)
    )
    terminal = synthesize_total_scalar_program_v182r2(
        tuple(
            MachineSynthesisRowV182(
                row.successor,
                (0,) * action_width,
                int(row.terminal),
            )
            for row in observations
        ),
        state_moduli=state_moduli_frozen,
        legal_actions=((0,) * action_width,),
        maximum_enumeration_events=maximum_enumeration_events_per_scalar,
        maximum_instruction_count=maximum_instruction_count,
        maximum_execution_steps=maximum_execution_steps,
        register_count=register_count,
        maximum_residual_support=1,
        archive=frozen_archive,
    )
    if not terminal.synthesis.exact_on_all_rows:
        _fail("V182r2 terminal program cannot retain a stochastic residual")
    boundaries = _factor_boundaries(coordinates)
    partial = {
        "schema": "acfqp.open_world_total_machine_compiled_model.v182r2",
        "state_moduli": list(state_moduli_frozen),
        "state_width": state_width,
        "legal_actions": [list(row) for row in actions],
        "action_width": action_width,
        "register_count": register_count,
        "maximum_execution_steps": maximum_execution_steps,
        "coordinates": [row.to_document() for row in coordinates],
        "terminal_synthesis": terminal.to_document(),
        "source_observation_ids": [row.observation_id for row in observations],
        "source_label_count": len(observations),
        "factor_boundaries": [list(row) for row in boundaries],
        "all_programs_total_on_full_registered_finite_carrier": True,
        "support_closed_on_full_registered_finite_carrier": True,
        "finite_carrier_totality_not_unbounded_totality": True,
        "factor_boundaries_derived_from_machine_read_dependencies": True,
        "layout_names_supplied": False,
        "domain_family_supplied": False,
        "whole_program_template_used": False,
        "finite_candidate_program_catalog_used": False,
        "language_program_length_unbounded": True,
        "occurrence_search_resource_bounded": True,
    }
    model_id = domains.extension_content_id_v182r2(
        domains.CONSTRUCTION_K7_TOTAL_COMPILED_MODEL_V182R2_DOMAIN,
        partial,
    )
    model = TotalCompiledMachineWorldModelV182R2(
        state_moduli_frozen,
        actions,
        register_count,
        maximum_execution_steps,
        coordinates,
        terminal,
        tuple(row.observation_id for row in observations),
        boundaries,
        model_id,
    )
    for state in _state_carrier(state_moduli_frozen):
        model.terminal(state)
        for action in actions:
            model.predict_support(state, action)
    return model


__all__ = (
    "OpenWorldTotalMachineModelV182R2Error",
    "TotalCompiledMachineCoordinateV182R2",
    "TotalCompiledMachineWorldModelV182R2",
    "TotalSynthesizedMachineProgramV182R2",
    "TotalityCertificateV182R2",
    "certify_program_totality_v182r2",
    "compile_total_machine_world_model_v182r2",
    "synthesize_total_scalar_program_v182r2",
)
