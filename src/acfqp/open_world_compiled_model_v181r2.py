"""Compile V181r2 cyclic-residual expressions into an opaque world model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp.open_world_compiled_model_v181 import (
    CompiledCoordinateV181,
    CompiledWorldModelV181,
)
from acfqp.open_world_transition_oracle_v181 import RawTransitionObservationV181
from acfqp.open_world_universal_synthesizer_v181 import (
    ExpressionV181,
    SynthesisRowV181,
    expression_bytes_v181,
)
from acfqp.open_world_universal_synthesizer_v181r2 import (
    synthesize_expression_v181r2,
)
from acfqp.phase3e_ids import canonical_json_bytes


class OpenWorldCompiledModelV181R2Error(ValueError):
    pass


def _expression_document(expression: ExpressionV181) -> Any:
    return [
        _expression_document(item) if type(item) is tuple else item
        for item in expression
    ]


def _factor_boundaries(
    coordinates: Sequence[CompiledCoordinateV181],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for row in coordinates:
        groups.setdefault(row.dependencies, []).append(row.coordinate_index)
    return tuple(
        sorted((tuple(values) for values in groups.values()), key=lambda row: (row[0], len(row)))
    )


@dataclass(frozen=True, slots=True)
class CompiledWorldModelV181R2:
    _runtime: CompiledWorldModelV181
    compiled_model_id: str
    source_observation_ids: tuple[str, ...]
    source_label_count: int
    total_enumeration_events: int
    archive_reference_count: int

    @property
    def state_width(self) -> int:
        return self._runtime.state_width

    @property
    def action_width(self) -> int:
        return self._runtime.action_width

    @property
    def coordinates(self) -> tuple[CompiledCoordinateV181, ...]:
        return self._runtime.coordinates

    @property
    def terminal_expression(self) -> ExpressionV181:
        return self._runtime.terminal_expression

    @property
    def terminal_dependencies(self) -> tuple[tuple[str, int], ...]:
        return self._runtime.terminal_dependencies

    @property
    def factor_boundaries(self) -> tuple[tuple[int, ...], ...]:
        return self._runtime.factor_boundaries

    def terminal(self, state: Sequence[int]) -> bool:
        return self._runtime.terminal(state)

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        return self._runtime.predict_support(state, action)

    def reusable_subprogram_archive(self) -> tuple[ExpressionV181, ...]:
        return self._runtime.reusable_subprogram_archive()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_compiled_program.v181r2",
            "state_width": self.state_width,
            "action_width": self.action_width,
            "coordinates": [row.to_document() for row in self.coordinates],
            "terminal_expression": _expression_document(self.terminal_expression),
            "terminal_token_length": self._runtime.terminal_token_length,
            "terminal_enumeration_events": self._runtime.terminal_enumeration_events,
            "terminal_dependencies": [list(row) for row in self.terminal_dependencies],
            "factor_boundaries": [list(row) for row in self.factor_boundaries],
            "source_observation_ids": list(self.source_observation_ids),
            "source_label_count": self.source_label_count,
            "total_enumeration_events": self.total_enumeration_events,
            "archive_reference_count": self.archive_reference_count,
            "cyclic_residual_carrier_derived_from_observed_coordinate": True,
            "signed_wraparound_residual_inflation_used": False,
            "finite_candidate_program_catalog_used": False,
            "named_domain_family_used": False,
            "whole_program_template_used": False,
            "factor_boundaries_derived_from_minimal_dependencies": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "compiled_model_id": self.compiled_model_id}


def compile_world_model_v181r2(
    observations: Sequence[RawTransitionObservationV181],
    *,
    maximum_enumeration_events_per_expression: int,
    archive: Iterable[ExpressionV181] = (),
) -> CompiledWorldModelV181R2:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawTransitionObservationV181 for row in observations)
    ):
        raise OpenWorldCompiledModelV181R2Error(
            "compiled model requires at least eight raw observations"
        )
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
        raise OpenWorldCompiledModelV181R2Error(
            "observations are duplicated or cross opaque schemas"
        )
    frozen_archive = tuple(archive)
    coordinates: list[CompiledCoordinateV181] = []
    for coordinate_index in range(state_width):
        synthesis_rows = tuple(
            SynthesisRowV181(row.state, row.action, row.successor[coordinate_index])
            for row in observations
        )
        by_input: dict[tuple[tuple[int, ...], tuple[int, ...]], set[int]] = {}
        for row in synthesis_rows:
            by_input.setdefault((row.state, row.action), set()).add(int(row.target))
        stochastic = any(len(values) > 1 for values in by_input.values())
        observed_modulus = max(
            max(row.state[coordinate_index], row.successor[coordinate_index])
            for row in observations
        ) + 1
        result = synthesize_expression_v181r2(
            synthesis_rows,
            maximum_enumeration_events=maximum_enumeration_events_per_expression,
            maximum_token_length=11,
            maximum_residual_support=3,
            residual_modulus=observed_modulus if stochastic else None,
            archive=frozen_archive,
        )
        coordinates.append(
            CompiledCoordinateV181(
                coordinate_index,
                result.expression,
                result.exact_on_all_rows,
                result.residual_values,
                result.residual_modulus,
                result.dependencies,
                result.token_length,
                result.enumeration_events,
                result.archive_reference_used,
            )
        )
    terminal_result = synthesize_expression_v181r2(
        tuple(
            SynthesisRowV181(row.successor, (0,) * action_width, row.terminal)
            for row in observations
        ),
        maximum_enumeration_events=maximum_enumeration_events_per_expression,
        maximum_token_length=11,
        archive=frozen_archive,
    )
    if not terminal_result.exact_on_all_rows:
        raise OpenWorldCompiledModelV181R2Error(
            "terminal expression cannot use a stochastic residual"
        )
    coordinate_tuple = tuple(coordinates)
    boundaries = _factor_boundaries(coordinate_tuple)
    payload = {
        "schema": "acfqp.open_world_compiled_program.v181r2",
        "state_width": state_width,
        "action_width": action_width,
        "coordinates": [row.to_document() for row in coordinate_tuple],
        "terminal_expression": _expression_document(terminal_result.expression),
        "terminal_token_length": terminal_result.token_length,
        "terminal_enumeration_events": terminal_result.enumeration_events,
        "terminal_dependencies": [list(row) for row in terminal_result.dependencies],
        "factor_boundaries": [list(row) for row in boundaries],
        "source_observation_ids": [row.observation_id for row in observations],
        "source_label_count": len(observations),
        "total_enumeration_events": sum(row.enumeration_events for row in coordinate_tuple)
        + terminal_result.enumeration_events,
        "archive_reference_count": sum(row.archive_reference_used for row in coordinate_tuple)
        + int(terminal_result.archive_reference_used),
        "cyclic_residual_carrier_derived_from_observed_coordinate": True,
        "signed_wraparound_residual_inflation_used": False,
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "whole_program_template_used": False,
        "factor_boundaries_derived_from_minimal_dependencies": True,
    }
    model_id = domains.extension_content_id_v181r2(
        domains.CONSTRUCTION_K7_COMPILED_PROGRAM_V181R2_DOMAIN, payload
    )
    runtime = CompiledWorldModelV181(
        state_width,
        action_width,
        coordinate_tuple,
        terminal_result.expression,
        terminal_result.token_length,
        terminal_result.enumeration_events,
        terminal_result.dependencies,
        boundaries,
        tuple(row.observation_id for row in observations),
        len(observations),
        payload["total_enumeration_events"],
        payload["archive_reference_count"],
        model_id,
    )
    return CompiledWorldModelV181R2(
        runtime,
        model_id,
        tuple(row.observation_id for row in observations),
        len(observations),
        payload["total_enumeration_events"],
        payload["archive_reference_count"],
    )


@dataclass(frozen=True, slots=True)
class AbstractPlanCertificateV181R2:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    planning_compute_events: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_abstract_plan_certificate.v181r2",
            "compiled_model_id": self.compiled_model_id,
            "state": list(self.state),
            "horizon": self.horizon,
            "certified": self.certified,
            "selected_action": list(self.selected_action) if self.selected_action else None,
            "planning_compute_events": self.planning_compute_events,
            "certificate_failure_requires_local_ground_distinction": not self.certified,
            "certificate_id": self.certificate_id,
        }


def certify_receding_action_v181r2(
    model: CompiledWorldModelV181R2,
    *,
    state: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    horizon: int,
) -> AbstractPlanCertificateV181R2:
    if (
        type(model) is not CompiledWorldModelV181R2
        or len(state) != model.state_width
        or type(horizon) is not int
        or horizon <= 0
        or type(legal_actions) not in {tuple, list}
        or not legal_actions
    ):
        raise OpenWorldCompiledModelV181R2Error("planner input changed")
    actions = tuple(tuple(row) for row in legal_actions)
    if any(len(row) != model.action_width for row in actions):
        raise OpenWorldCompiledModelV181R2Error("planner action width changed")
    memo: dict[tuple[tuple[int, ...], int], tuple[bool, tuple[int, ...] | None]] = {}
    events = 0

    def winning(current: tuple[int, ...], remaining: int):
        nonlocal events
        events += 1
        if model.terminal(current):
            return True, None
        if remaining == 0:
            return False, None
        key = (current, remaining)
        if key in memo:
            return memo[key]
        for action in actions:
            support = model.predict_support(current, action)
            if all(
                model.terminal(successor)
                or winning(successor, remaining - 1)[0]
                for successor in support
            ):
                memo[key] = (True, action)
                return memo[key]
        memo[key] = (False, None)
        return memo[key]

    certified, action = winning(tuple(state), horizon)
    payload = {
        "schema": "acfqp.open_world_abstract_plan_certificate.v181r2",
        "compiled_model_id": model.compiled_model_id,
        "state": list(state),
        "horizon": horizon,
        "certified": certified,
        "selected_action": list(action) if action is not None else None,
        "planning_compute_events": events,
        "certificate_failure_requires_local_ground_distinction": not certified,
    }
    certificate_id = domains.extension_content_id_v181r2(
        domains.CONSTRUCTION_K7_CERTIFICATE_V181R2_DOMAIN, payload
    )
    return AbstractPlanCertificateV181R2(
        model.compiled_model_id,
        tuple(state),
        horizon,
        certified,
        action,
        events,
        certificate_id,
    )


__all__ = (
    "AbstractPlanCertificateV181R2",
    "CompiledWorldModelV181R2",
    "OpenWorldCompiledModelV181R2Error",
    "certify_receding_action_v181r2",
    "compile_world_model_v181r2",
)
