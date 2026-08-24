"""Compile opaque transition observations into a reusable V181 world model.

The compiler delegates every coordinate and terminal predicate to the same
generic expression enumerator.  It derives factor boundaries solely from the
minimal expression dependencies.  The receding planner consumes only the
compiled model and an opaque action catalogue; raw observations are not part
of the planning API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v181 as domains
from acfqp.open_world_transition_oracle_v181 import RawTransitionObservationV181
from acfqp.open_world_universal_synthesizer_v181 import (
    ExpressionV181,
    SynthesisRowV181,
    SynthesizedExpressionV181,
    evaluate_expression_v181,
    expression_bytes_v181,
    expression_dependencies_v181,
    synthesize_expression_v181,
)
from acfqp.phase3e_ids import canonical_json_bytes


class OpenWorldCompiledModelV181Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCompiledModelV181Error(message)


def _expression_document(expression: ExpressionV181) -> Any:
    return [
        _expression_document(item) if type(item) is tuple else item
        for item in expression
    ]


def _expression_tuple(document: Any) -> ExpressionV181:
    if type(document) is not list:
        _fail("compiled expression document changed")
    return tuple(
        _expression_tuple(item) if type(item) is list else item for item in document
    )


def _subexpressions(expression: ExpressionV181) -> set[ExpressionV181]:
    result = {expression}
    for item in expression[1:]:
        if type(item) is tuple:
            result.update(_subexpressions(item))
    return result


@dataclass(frozen=True, slots=True)
class CompiledCoordinateV181:
    coordinate_index: int
    expression: ExpressionV181
    exact_on_source: bool
    residual_values: tuple[int, ...]
    residual_modulus: int | None
    dependencies: tuple[tuple[str, int], ...]
    token_length: int
    enumeration_events: int
    archive_reference_used: bool

    def to_document(self) -> dict[str, Any]:
        return {
            "coordinate_index": self.coordinate_index,
            "expression": _expression_document(self.expression),
            "exact_on_source": self.exact_on_source,
            "residual_values": list(self.residual_values),
            "residual_modulus": self.residual_modulus,
            "dependencies": [list(row) for row in self.dependencies],
            "token_length": self.token_length,
            "enumeration_events": self.enumeration_events,
            "archive_reference_used": self.archive_reference_used,
        }


@dataclass(frozen=True, slots=True)
class CompiledWorldModelV181:
    state_width: int
    action_width: int
    coordinates: tuple[CompiledCoordinateV181, ...]
    terminal_expression: ExpressionV181
    terminal_token_length: int
    terminal_enumeration_events: int
    terminal_dependencies: tuple[tuple[str, int], ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
    source_observation_ids: tuple[str, ...]
    source_label_count: int
    total_enumeration_events: int
    archive_reference_count: int
    compiled_model_id: str

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_compiled_program.v181",
            "state_width": self.state_width,
            "action_width": self.action_width,
            "coordinates": [row.to_document() for row in self.coordinates],
            "terminal_expression": _expression_document(self.terminal_expression),
            "terminal_token_length": self.terminal_token_length,
            "terminal_enumeration_events": self.terminal_enumeration_events,
            "terminal_dependencies": [list(row) for row in self.terminal_dependencies],
            "factor_boundaries": [list(row) for row in self.factor_boundaries],
            "source_observation_ids": list(self.source_observation_ids),
            "source_label_count": self.source_label_count,
            "total_enumeration_events": self.total_enumeration_events,
            "archive_reference_count": self.archive_reference_count,
            "finite_candidate_program_catalog_used": False,
            "named_domain_family_used": False,
            "whole_program_template_used": False,
            "factor_boundaries_derived_from_minimal_dependencies": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "compiled_model_id": self.compiled_model_id}

    def terminal(self, state: Sequence[int]) -> bool:
        value = evaluate_expression_v181(
            self.terminal_expression,
            state,
            (0,) * self.action_width,
        )
        if type(value) is not bool:
            _fail("compiled terminal expression stopped being boolean")
        return value

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        if len(state) != self.state_width or len(action) != self.action_width:
            _fail("compiled model query crosses opaque widths")
        coordinate_values = []
        for coordinate in self.coordinates:
            base = evaluate_expression_v181(coordinate.expression, state, action)
            if type(base) is not int:
                _fail("compiled transition coordinate became non-integer")
            if coordinate.exact_on_source:
                values = (base,)
            else:
                modulus = coordinate.residual_modulus
                if type(modulus) is not int or modulus <= 0:
                    _fail("partial coordinate lacks one residual modulus")
                values = tuple(
                    sorted({(base + residual) % modulus for residual in coordinate.residual_values})
                )
            coordinate_values.append(values)
        support = tuple(tuple(row) for row in product(*coordinate_values))
        if not support or len(support) > 128:
            _fail("compiled support cardinality exceeds the registered bound")
        return support

    def reusable_subprogram_archive(self) -> tuple[ExpressionV181, ...]:
        expressions = set()
        for row in self.coordinates:
            expressions.update(_subexpressions(row.expression))
        expressions.update(_subexpressions(self.terminal_expression))
        return tuple(sorted(expressions, key=expression_bytes_v181))


def _factor_boundaries(
    coordinates: Sequence[CompiledCoordinateV181],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[str, int], ...], list[int]] = {}
    for row in coordinates:
        groups.setdefault(row.dependencies, []).append(row.coordinate_index)
    return tuple(
        sorted(
            (tuple(values) for values in groups.values()),
            key=lambda row: (row[0], len(row)),
        )
    )


def compile_world_model_v181(
    observations: Sequence[RawTransitionObservationV181],
    *,
    maximum_enumeration_events_per_expression: int,
    archive: Iterable[ExpressionV181] = (),
) -> CompiledWorldModelV181:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawTransitionObservationV181 for row in observations)
    ):
        _fail("compiled model requires at least eight raw oracle observations")
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
        _fail("raw observations are duplicated or cross opaque schemas")
    frozen_archive = tuple(archive)
    coordinates = []
    for coordinate_index in range(state_width):
        result = synthesize_expression_v181(
            tuple(
                SynthesisRowV181(row.state, row.action, row.successor[coordinate_index])
                for row in observations
            ),
            maximum_enumeration_events=maximum_enumeration_events_per_expression,
            maximum_token_length=11,
            maximum_residual_support=3,
            archive=frozen_archive,
        )
        coordinates.append(
            CompiledCoordinateV181(
                coordinate_index,
                result.expression,
                result.exact_on_all_rows,
                result.residual_values,
                (
                    max(
                        max(row.state[coordinate_index], row.successor[coordinate_index])
                        for row in observations
                    )
                    + 1
                    if not result.exact_on_all_rows
                    else None
                ),
                result.dependencies,
                result.token_length,
                result.enumeration_events,
                result.archive_reference_used,
            )
        )
    terminal_result = synthesize_expression_v181(
        tuple(
            SynthesisRowV181(
                row.successor,
                (0,) * action_width,
                row.terminal,
            )
            for row in observations
        ),
        maximum_enumeration_events=maximum_enumeration_events_per_expression,
        maximum_token_length=11,
        archive=frozen_archive,
    )
    if not terminal_result.exact_on_all_rows:
        _fail("terminal program cannot use a statistical residual")
    coordinate_tuple = tuple(coordinates)
    payload = {
        "schema": "acfqp.open_world_compiled_program.v181",
        "state_width": state_width,
        "action_width": action_width,
        "coordinates": [row.to_document() for row in coordinate_tuple],
        "terminal_expression": _expression_document(terminal_result.expression),
        "terminal_token_length": terminal_result.token_length,
        "terminal_enumeration_events": terminal_result.enumeration_events,
        "terminal_dependencies": [list(row) for row in terminal_result.dependencies],
        "factor_boundaries": [list(row) for row in _factor_boundaries(coordinate_tuple)],
        "source_observation_ids": [row.observation_id for row in observations],
        "source_label_count": len(observations),
        "total_enumeration_events": sum(row.enumeration_events for row in coordinate_tuple)
        + terminal_result.enumeration_events,
        "archive_reference_count": sum(row.archive_reference_used for row in coordinate_tuple)
        + int(terminal_result.archive_reference_used),
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "whole_program_template_used": False,
        "factor_boundaries_derived_from_minimal_dependencies": True,
    }
    model_id = domains.extension_content_id_v181(
        domains.CONSTRUCTION_K7_COMPILED_PROGRAM_V181_DOMAIN,
        payload,
    )
    return CompiledWorldModelV181(
        state_width,
        action_width,
        coordinate_tuple,
        terminal_result.expression,
        terminal_result.token_length,
        terminal_result.enumeration_events,
        terminal_result.dependencies,
        _factor_boundaries(coordinate_tuple),
        tuple(row.observation_id for row in observations),
        len(observations),
        payload["total_enumeration_events"],
        payload["archive_reference_count"],
        model_id,
    )


@dataclass(frozen=True, slots=True)
class AbstractPlanCertificateV181:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    planning_compute_events: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_abstract_plan_certificate.v181",
            "compiled_model_id": self.compiled_model_id,
            "state": list(self.state),
            "horizon": self.horizon,
            "certified": self.certified,
            "selected_action": (
                list(self.selected_action) if self.selected_action is not None else None
            ),
            "planning_compute_events": self.planning_compute_events,
            "certificate_failure_requires_local_ground_distinction": not self.certified,
            "certificate_id": self.certificate_id,
        }


def certify_receding_action_v181(
    model: CompiledWorldModelV181,
    *,
    state: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    horizon: int,
) -> AbstractPlanCertificateV181:
    if (
        type(model) is not CompiledWorldModelV181
        or len(state) != model.state_width
        or type(horizon) is not int
        or horizon <= 0
        or type(legal_actions) not in {tuple, list}
        or not legal_actions
    ):
        _fail("abstract planner input changed")
    actions = tuple(tuple(row) for row in legal_actions)
    if any(
        len(row) != model.action_width or any(type(value) is not int for value in row)
        for row in actions
    ):
        _fail("abstract planner action catalogue crosses opaque schema")
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
        "schema": "acfqp.open_world_abstract_plan_certificate.v181",
        "compiled_model_id": model.compiled_model_id,
        "state": list(state),
        "horizon": horizon,
        "certified": certified,
        "selected_action": list(action) if action is not None else None,
        "planning_compute_events": events,
        "certificate_failure_requires_local_ground_distinction": not certified,
    }
    certificate_id = domains.extension_content_id_v181(
        domains.CONSTRUCTION_K7_CERTIFICATE_V181_DOMAIN,
        payload,
    )
    return AbstractPlanCertificateV181(
        model.compiled_model_id,
        tuple(state),
        horizon,
        certified,
        action,
        events,
        certificate_id,
    )


__all__ = (
    "AbstractPlanCertificateV181",
    "CompiledCoordinateV181",
    "CompiledWorldModelV181",
    "OpenWorldCompiledModelV181Error",
    "certify_receding_action_v181",
    "compile_world_model_v181",
)
