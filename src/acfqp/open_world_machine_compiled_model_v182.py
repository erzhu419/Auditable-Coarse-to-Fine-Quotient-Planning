"""Compile opaque raw transitions into one V182 counter-machine world model."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182 as domains
from acfqp.open_world_universal_machine_v182 import (
    MachineSynthesisRowV182,
    ProgramV182,
    SynthesizedMachineProgramV182,
    execute_program_v182,
    synthesize_scalar_program_v182,
)


class OpenWorldMachineCompiledModelV182Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldMachineCompiledModelV182Error(message)


@dataclass(frozen=True, slots=True)
class RawMachineTransitionV182:
    occurrence_index: int
    query_index: int
    state: tuple[int, ...]
    action: tuple[int, ...]
    successor: tuple[int, ...]
    terminal: bool
    observation_id: str

    @classmethod
    def observe(
        cls,
        *,
        occurrence_index: int,
        query_index: int,
        state: Sequence[int],
        action: Sequence[int],
        successor: Sequence[int],
        terminal: bool,
    ) -> "RawMachineTransitionV182":
        if (
            type(occurrence_index) is not int
            or occurrence_index < 0
            or type(query_index) is not int
            or query_index < 0
            or type(state) not in {tuple, list}
            or not state
            or type(action) not in {tuple, list}
            or not action
            or type(successor) not in {tuple, list}
            or len(successor) != len(state)
            or any(type(value) is not int or value < 0 for value in (*state, *action, *successor))
            or type(terminal) is not bool
        ):
            _fail("V182 raw transition changed")
        payload = {
            "schema": "acfqp.open_world_machine_raw_transition.v182",
            "occurrence_index": occurrence_index,
            "query_index": query_index,
            "state": list(state),
            "action": list(action),
            "successor": list(successor),
            "terminal": terminal,
        }
        return cls(
            occurrence_index,
            query_index,
            tuple(state),
            tuple(action),
            tuple(successor),
            terminal,
            domains.extension_content_id_v182(
                domains.CONSTRUCTION_K7_RAW_OBSERVATION_V182_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_machine_raw_transition.v182",
            "occurrence_index": self.occurrence_index,
            "query_index": self.query_index,
            "state": list(self.state),
            "action": list(self.action),
            "successor": list(self.successor),
            "terminal": self.terminal,
            "observation_id": self.observation_id,
        }


@dataclass(frozen=True, slots=True)
class CompiledMachineCoordinateV182:
    coordinate_index: int
    synthesis: SynthesizedMachineProgramV182

    def to_document(self) -> dict[str, Any]:
        return {
            "coordinate_index": self.coordinate_index,
            "synthesis": self.synthesis.to_document(),
        }


@dataclass(frozen=True, slots=True)
class CompiledMachineWorldModelV182:
    state_width: int
    action_width: int
    register_count: int
    maximum_execution_steps: int
    coordinates: tuple[CompiledMachineCoordinateV182, ...]
    terminal_synthesis: SynthesizedMachineProgramV182
    source_observation_ids: tuple[str, ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
    compiled_model_id: str

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
            _fail("compiled V182 program did not halt within its frozen budget")
        return execution.output

    def terminal(self, state: Sequence[int]) -> bool:
        if len(state) != self.state_width:
            _fail("V182 terminal state width changed")
        output = self._run(
            self.terminal_synthesis.program,
            state,
            (0,) * self.action_width,
        )
        if output not in {0, 1}:
            _fail("compiled V182 terminal program did not return one boolean bit")
        return bool(output)

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        if len(state) != self.state_width or len(action) != self.action_width:
            _fail("V182 compiled prediction crossed its opaque schema")
        supports = []
        for coordinate in self.coordinates:
            base = self._run(coordinate.synthesis.program, state, action)
            residuals = coordinate.synthesis.residual_values or (0,)
            values = tuple(sorted({base + residual for residual in residuals if base + residual >= 0}))
            if not values:
                _fail("V182 coordinate support became empty")
            supports.append(values)
        return tuple(product(*supports))

    def covers(self, row: RawMachineTransitionV182) -> bool:
        return (
            row.successor in self.predict_support(row.state, row.action)
            and self.terminal(row.successor) is row.terminal
        )

    def reusable_program_archive(self) -> tuple[ProgramV182, ...]:
        return tuple(
            dict.fromkeys(
                [
                    *(row.synthesis.program for row in self.coordinates),
                    self.terminal_synthesis.program,
                ]
            )
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_machine_compiled_model.v182",
            "state_width": self.state_width,
            "action_width": self.action_width,
            "register_count": self.register_count,
            "maximum_execution_steps": self.maximum_execution_steps,
            "coordinates": [row.to_document() for row in self.coordinates],
            "terminal_synthesis": self.terminal_synthesis.to_document(),
            "source_observation_ids": list(self.source_observation_ids),
            "source_label_count": len(self.source_observation_ids),
            "factor_boundaries": [list(row) for row in self.factor_boundaries],
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
    coordinates: Sequence[CompiledMachineCoordinateV182],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for row in coordinates:
        groups.setdefault(row.synthesis.read_dependencies, []).append(
            row.coordinate_index
        )
    return tuple(
        sorted(
            (tuple(indices) for indices in groups.values()),
            key=lambda indices: (indices[0], len(indices)),
        )
    )


def compile_machine_world_model_v182(
    observations: Sequence[RawMachineTransitionV182],
    *,
    maximum_enumeration_events_per_scalar: int,
    maximum_instruction_count: int,
    maximum_execution_steps: int,
    register_count: int = 2,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> CompiledMachineWorldModelV182:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V182 model compilation requires at least eight raw transitions")
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
        _fail("V182 model rows are duplicated or cross opaque schemas")
    frozen_archive = tuple(archive)
    coordinates = tuple(
        CompiledMachineCoordinateV182(
            index,
            synthesize_scalar_program_v182(
                tuple(
                    MachineSynthesisRowV182(row.state, row.action, row.successor[index])
                    for row in observations
                ),
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
    terminal = synthesize_scalar_program_v182(
        tuple(
            MachineSynthesisRowV182(
                row.successor,
                (0,) * action_width,
                int(row.terminal),
            )
            for row in observations
        ),
        maximum_enumeration_events=maximum_enumeration_events_per_scalar,
        maximum_instruction_count=maximum_instruction_count,
        maximum_execution_steps=maximum_execution_steps,
        register_count=register_count,
        maximum_residual_support=1,
        archive=frozen_archive,
    )
    if not terminal.exact_on_all_rows:
        _fail("V182 terminal program cannot retain a stochastic residual")
    boundaries = _factor_boundaries(coordinates)
    payload = {
        "schema": "acfqp.open_world_machine_compiled_model.v182",
        "state_width": state_width,
        "action_width": action_width,
        "register_count": register_count,
        "maximum_execution_steps": maximum_execution_steps,
        "coordinates": [row.to_document() for row in coordinates],
        "terminal_synthesis": terminal.to_document(),
        "source_observation_ids": [row.observation_id for row in observations],
        "source_label_count": len(observations),
        "factor_boundaries": [list(row) for row in boundaries],
        "factor_boundaries_derived_from_machine_read_dependencies": True,
        "layout_names_supplied": False,
        "domain_family_supplied": False,
        "whole_program_template_used": False,
        "finite_candidate_program_catalog_used": False,
        "language_program_length_unbounded": True,
        "occurrence_search_resource_bounded": True,
    }
    model_id = domains.extension_content_id_v182(
        domains.CONSTRUCTION_K7_COMPILED_MODEL_V182_DOMAIN,
        payload,
    )
    return CompiledMachineWorldModelV182(
        state_width,
        action_width,
        register_count,
        maximum_execution_steps,
        coordinates,
        terminal,
        tuple(row.observation_id for row in observations),
        boundaries,
        model_id,
    )


__all__ = (
    "CompiledMachineCoordinateV182",
    "CompiledMachineWorldModelV182",
    "OpenWorldMachineCompiledModelV182Error",
    "RawMachineTransitionV182",
    "compile_machine_world_model_v182",
)
