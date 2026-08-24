"""Fair synthesis over an unbounded compositional expression language.

V183 used a finite collection of hand-written program shapes per occurrence.
V184 keeps a small typed machine instruction basis but removes that catalogue:
expressions are enumerated fairly by increasing tree size, compiled into the
counter machine, and admitted only after the V183 structural totality checker
returns a certificate.  The language is countably infinite; any actual run
inspects only a finite prefix under an explicit resource cap.  Exhausting that
cap is not an impossibility or nontermination result.

This is automatic subprogram composition, not invention of new primitive
opcodes and not a decision procedure for arbitrary programs.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Iterator, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v184 as domains
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_ranked_machine_v183 import (
    OpenWorldRankedMachineV183Error,
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


ExpressionV184 = tuple[Any, ...]
_UNARY = ("INC", "ISZERO")
_BINARY = ("ADD", "SUBSAT", "XOR", "EQ", "LT")
_COMMUTATIVE = frozenset({"ADD", "XOR", "EQ"})
_OPCODE_BY_NAME = {
    "ADD": ADD,
    "SUBSAT": SUBSAT,
    "XOR": XOR,
    "EQ": EQ,
    "LT": LT,
}


class OpenWorldFairExpressionMachineV184Error(ValueError):
    pass


class FairSearchResourceExhaustedV184(OpenWorldFairExpressionMachineV184Error):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldFairExpressionMachineV184Error(message)


def _expression_document(expression: ExpressionV184) -> list[Any]:
    return [
        expression[0],
        *[
            _expression_document(value) if type(value) is tuple else value
            for value in expression[1:]
        ],
    ]


def _expression_key(expression: ExpressionV184) -> bytes:
    return canonical_json_bytes(_expression_document(expression))


def _expressions_of_size(
    size: int,
    *,
    input_width: int,
    constants: tuple[int, ...],
    cache: dict[int, tuple[ExpressionV184, ...]],
) -> tuple[ExpressionV184, ...]:
    if size in cache:
        return cache[size]
    rows: list[ExpressionV184] = []
    if size == 1:
        rows.extend(("INPUT", index) for index in range(input_width))
        rows.extend(("CONST", value) for value in constants)
    else:
        rows.extend(
            (opcode, child)
            for opcode in _UNARY
            for child in _expressions_of_size(
                size - 1,
                input_width=input_width,
                constants=constants,
                cache=cache,
            )
        )
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            left_rows = _expressions_of_size(
                left_size,
                input_width=input_width,
                constants=constants,
                cache=cache,
            )
            right_rows = _expressions_of_size(
                right_size,
                input_width=input_width,
                constants=constants,
                cache=cache,
            )
            for opcode in _BINARY:
                for left, right in product(left_rows, right_rows):
                    if opcode in _COMMUTATIVE and _expression_key(left) > _expression_key(right):
                        continue
                    rows.append((opcode, left, right))
    result = tuple(sorted(set(rows), key=_expression_key))
    cache[size] = result
    return result


def enumerate_expressions_fairly_v184(
    *, input_width: int, constants: Sequence[int]
) -> Iterator[tuple[int, ExpressionV184]]:
    if (
        type(input_width) is not int
        or input_width < 1
        or type(constants) not in {tuple, list}
        or any(type(value) is not int or value < 0 for value in constants)
    ):
        _fail("V184 expression grammar inputs changed")
    frozen_constants = tuple(sorted({0, 1, *constants}))
    cache: dict[int, tuple[ExpressionV184, ...]] = {}
    size = 1
    while True:
        for expression in _expressions_of_size(
            size,
            input_width=input_width,
            constants=frozen_constants,
            cache=cache,
        ):
            yield size, expression
        size += 1


def _compile_expression(
    expression: ExpressionV184,
    *,
    input_width: int,
    register_count: int,
) -> ProgramV182 | None:
    instructions: list[tuple[int, ...]] = []

    def emit(node: ExpressionV184, target: int) -> bool:
        if target >= register_count:
            return False
        opcode = node[0]
        if opcode == "INPUT":
            if type(node[1]) is not int or not 0 <= node[1] < input_width:
                return False
            instructions.append((READ, target, node[1]))
            return True
        if opcode == "CONST":
            if type(node[1]) is not int or node[1] < 0:
                return False
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


def _read_dependencies(expression: ExpressionV184) -> tuple[int, ...]:
    result: set[int] = set()

    def visit(node: ExpressionV184) -> None:
        if node[0] == "INPUT":
            result.add(node[1])
        for value in node[1:]:
            if type(value) is tuple:
                visit(value)

    visit(expression)
    return tuple(sorted(result))


@dataclass(frozen=True, slots=True)
class FairRankedCandidateV184:
    program: ProgramV182
    expression: ExpressionV184 | None
    expression_size: int | None
    termination: RankedTerminationCertificateV183
    from_archive: bool


def enumerate_fair_ranked_candidates_v184(
    *,
    input_width: int,
    register_count: int,
    constants: Sequence[int],
    archive: Iterable[ProgramV182] = (),
) -> Iterator[FairRankedCandidateV184]:
    seen: set[ProgramV182] = set()
    for value in archive:
        program = tuple(value)
        certificate = certify_ranked_termination_v183(
            program,
            register_count=register_count,
            input_width=input_width,
        )
        if certificate is not None and program not in seen:
            seen.add(program)
            yield FairRankedCandidateV184(
                program,
                None,
                None,
                certificate,
                True,
            )
    for size, expression in enumerate_expressions_fairly_v184(
        input_width=input_width,
        constants=constants,
    ):
        program = _compile_expression(
            expression,
            input_width=input_width,
            register_count=register_count,
        )
        if program is None or program in seen:
            continue
        certificate = certify_ranked_termination_v183(
            program,
            register_count=register_count,
            input_width=input_width,
        )
        if certificate is None:
            raise AssertionError("V184 straight-line compiler produced an uncertified program")
        seen.add(program)
        yield FairRankedCandidateV184(
            program,
            expression,
            size,
            certificate,
            False,
        )


@dataclass(frozen=True, slots=True)
class FairRankedSynthesizedProgramV184:
    program: ProgramV182
    expression: ExpressionV184 | None
    expression_size: int | None
    termination: RankedTerminationCertificateV183
    residual_values: tuple[int, ...]
    read_dependencies: tuple[tuple[str, int], ...]
    enumeration_events: int
    archive_reference_used: bool
    program_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fair_ranked_synthesized_program.v184",
            "program": [list(row) for row in self.program],
            "expression": (
                _expression_document(self.expression)
                if self.expression is not None
                else None
            ),
            "expression_size": self.expression_size,
            "termination_certificate": self.termination.to_document(),
            "residual_values": list(self.residual_values),
            "read_dependencies": [list(row) for row in self.read_dependencies],
            "enumeration_events": self.enumeration_events,
            "archive_reference_used": self.archive_reference_used,
            "archive_candidate_revalidated_on_every_current_row": self.archive_reference_used,
            "finite_candidate_catalog_used": False,
            "candidate_language_countably_infinite": True,
            "fair_size_ordered_enumeration": True,
            "actual_search_prefix_finite": True,
            "resource_cap_exhaustion_is_not_infeasibility": True,
            "new_primitive_opcode_invented": False,
            "composed_subprogram_invented_from_raw_rows": self.expression is not None,
            "program_id": self.program_id,
        }


def _dependency_document(
    indices: Iterable[int], state_width: int
) -> tuple[tuple[str, int], ...]:
    return tuple(
        ("S", index) if index < state_width else ("A", index - state_width)
        for index in sorted(set(indices))
    )


def synthesize_fair_ranked_scalar_program_v184(
    rows: Sequence[MachineSynthesisRowV182],
    *,
    maximum_enumeration_events: int,
    resource_step_cap: int,
    register_count: int = 5,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> FairRankedSynthesizedProgramV184:
    if (
        type(rows) not in {tuple, list}
        or not rows
        or any(type(row) is not MachineSynthesisRowV182 for row in rows)
        or type(maximum_enumeration_events) is not int
        or maximum_enumeration_events <= 0
        or type(resource_step_cap) is not int
        or resource_step_cap <= 0
        or type(register_count) is not int
        or register_count < 2
        or type(maximum_residual_support) is not int
        or maximum_residual_support < 1
    ):
        _fail("V184 synthesis input or resource profile changed")
    state_width = len(rows[0].state)
    action_width = len(rows[0].action)
    if any(
        len(row.state) != state_width or len(row.action) != action_width
        for row in rows
    ):
        _fail("V184 synthesis rows cross opaque schemas")
    constants = tuple(
        sorted(
            {
                0,
                1,
                *(value for row in rows for value in (*row.state, *row.action, row.target)),
            }
        )
    )
    targets = tuple(row.target for row in rows)
    best: tuple[
        tuple[Any, ...],
        FairRankedCandidateV184,
        tuple[int, ...],
        tuple[int, ...],
        int,
    ] | None = None
    semantic_outputs: set[tuple[int, ...]] = set()
    events = 0
    for candidate in enumerate_fair_ranked_candidates_v184(
        input_width=state_width + action_width,
        register_count=register_count,
        constants=constants,
        archive=archive,
    ):
        events += 1
        if events > maximum_enumeration_events:
            break
        executions = tuple(
            execute_ranked_program_v183(
                candidate.program,
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
        if outputs in semantic_outputs:
            continue
        semantic_outputs.add(outputs)
        residuals = tuple(
            sorted(
                {
                    target - output
                    for target, output in zip(targets, outputs, strict=True)
                }
            )
        )
        exact = outputs == targets
        if exact:
            residuals = ()
        elif not 1 <= len(residuals) <= maximum_residual_support:
            continue
        dependencies = tuple(
            sorted(
                {
                    index
                    for execution in executions
                    for index in execution.read_dependencies
                }
            )
        )
        rank = (
            int(not exact),
            len(candidate.program) + len(residuals),
            len(residuals),
            len(candidate.program),
            program_bytes_v182(candidate.program),
        )
        current = (rank, candidate, residuals, dependencies, events)
        if best is None or current[0] < best[0]:
            best = current
            if exact:
                break
    if best is None:
        raise FairSearchResourceExhaustedV184(
            "V184 finite search prefix found no supported ranked-total program"
        )
    _, candidate, residuals, dependencies, used_events = best
    payload = {
        "schema": "acfqp.fair_ranked_synthesized_program.v184",
        "program": [list(row) for row in candidate.program],
        "expression": (
            _expression_document(candidate.expression)
            if candidate.expression is not None
            else None
        ),
        "expression_size": candidate.expression_size,
        "termination_certificate": candidate.termination.to_document(),
        "residual_values": list(residuals),
        "read_dependencies": [
            list(row) for row in _dependency_document(dependencies, state_width)
        ],
        "enumeration_events": used_events,
        "archive_reference_used": candidate.from_archive,
        "archive_candidate_revalidated_on_every_current_row": candidate.from_archive,
        "finite_candidate_catalog_used": False,
        "candidate_language_countably_infinite": True,
        "fair_size_ordered_enumeration": True,
        "actual_search_prefix_finite": True,
        "resource_cap_exhaustion_is_not_infeasibility": True,
        "new_primitive_opcode_invented": False,
        "composed_subprogram_invented_from_raw_rows": candidate.expression is not None,
    }
    program_id = domains.extension_content_id_v184(
        domains.CONSTRUCTION_K7_SYNTHESIZED_PROGRAM_V184_DOMAIN,
        payload,
    )
    return FairRankedSynthesizedProgramV184(
        candidate.program,
        candidate.expression,
        candidate.expression_size,
        candidate.termination,
        residuals,
        _dependency_document(dependencies, state_width),
        used_events,
        candidate.from_archive,
        program_id,
    )


@dataclass(frozen=True, slots=True)
class FairRankedCompiledWorldModelV184:
    state_width: int
    action_width: int
    legal_actions: tuple[tuple[int, ...], ...]
    register_count: int
    resource_step_cap: int
    coordinates: tuple[FairRankedSynthesizedProgramV184, ...]
    terminal_synthesis: FairRankedSynthesizedProgramV184
    source_observation_ids: tuple[str, ...]
    factor_boundaries: tuple[tuple[int, ...], ...]
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
            _fail("V184 compiled model crossed its execution resource cap")
        return result.output

    def terminal(self, state: Sequence[int]) -> bool:
        if len(state) != self.state_width:
            _fail("V184 terminal input crossed its opaque width")
        result = self._run(
            self.terminal_synthesis.program,
            state,
            (0,) * self.action_width,
        )
        if result not in {0, 1}:
            _fail("V184 terminal program is not boolean")
        return bool(result)

    def predict_support(
        self, state: Sequence[int], action: Sequence[int]
    ) -> tuple[tuple[int, ...], ...]:
        if (
            len(state) != self.state_width
            or len(action) != self.action_width
            or tuple(action) not in self.legal_actions
        ):
            _fail("V184 prediction crossed its opaque schema")
        supports = []
        for synthesis in self.coordinates:
            base = self._run(synthesis.program, state, action)
            residuals = synthesis.residual_values or (0,)
            values = tuple(
                sorted({base + residual for residual in residuals if base + residual >= 0})
            )
            if not values:
                _fail("V184 synthesized stochastic support is empty")
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
                    *(row.program for row in self.coordinates),
                    self.terminal_synthesis.program,
                ]
            )
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fair_ranked_compiled_world_model.v184",
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
            "layout_supplied": False,
            "domain_family_supplied": False,
            "whole_program_templates_supplied": False,
            "finite_candidate_catalog_used": False,
            "candidate_language_countably_infinite": True,
            "actual_search_prefix_finite": True,
            "base_typed_opcode_set_finite": True,
            "new_primitive_opcode_invented": False,
            "arbitrary_domain_transfer_claimed": False,
            "compiled_model_id": self.compiled_model_id,
        }


def _factor_boundaries(
    rows: Sequence[FairRankedSynthesizedProgramV184],
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


def compile_fair_ranked_world_model_v184(
    observations: Sequence[RawMachineTransitionV182],
    *,
    maximum_enumeration_events_per_scalar: int,
    resource_step_cap: int,
    register_count: int = 5,
    maximum_residual_support: int = 3,
    archive: Iterable[ProgramV182] = (),
) -> FairRankedCompiledWorldModelV184:
    if (
        type(observations) not in {tuple, list}
        or len(observations) < 8
        or any(type(row) is not RawMachineTransitionV182 for row in observations)
    ):
        _fail("V184 compilation requires at least eight raw transitions")
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
        _fail("V184 observations are duplicated or cross opaque schemas")
    frozen_archive = tuple(archive)
    coordinates = tuple(
        synthesize_fair_ranked_scalar_program_v184(
            tuple(
                MachineSynthesisRowV182(row.state, row.action, row.successor[index])
                for row in observations
            ),
            maximum_enumeration_events=maximum_enumeration_events_per_scalar,
            resource_step_cap=resource_step_cap,
            register_count=register_count,
            maximum_residual_support=maximum_residual_support,
            archive=frozen_archive,
        )
        for index in range(state_width)
    )
    terminal = synthesize_fair_ranked_scalar_program_v184(
        tuple(
            MachineSynthesisRowV182(
                row.successor,
                (0,) * action_width,
                int(row.terminal),
            )
            for row in observations
        ),
        maximum_enumeration_events=maximum_enumeration_events_per_scalar,
        resource_step_cap=resource_step_cap,
        register_count=register_count,
        maximum_residual_support=1,
        archive=frozen_archive,
    )
    if terminal.residual_values:
        _fail("V184 terminal program cannot retain a residual support")
    legal_actions = tuple(sorted({row.action for row in observations}))
    boundaries = _factor_boundaries(coordinates)
    payload = {
        "schema": "acfqp.fair_ranked_compiled_world_model.v184",
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
        "layout_supplied": False,
        "domain_family_supplied": False,
        "whole_program_templates_supplied": False,
        "finite_candidate_catalog_used": False,
        "candidate_language_countably_infinite": True,
        "actual_search_prefix_finite": True,
        "base_typed_opcode_set_finite": True,
        "new_primitive_opcode_invented": False,
        "arbitrary_domain_transfer_claimed": False,
    }
    model_id = domains.extension_content_id_v184(
        domains.CONSTRUCTION_K7_COMPILED_MODEL_V184_DOMAIN,
        payload,
    )
    return FairRankedCompiledWorldModelV184(
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


@dataclass(frozen=True, slots=True)
class FairRankedPlanCertificateV184:
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
            "schema": "acfqp.fair_ranked_plan_certificate.v184",
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
                and self.selected_successor_rank_upper_bound < self.terminal_distance_rank
            ),
            "failure_reason": self.failure_reason,
            "planning_compute_events": self.planning_compute_events,
            "persistent_cache_hit_count": self.persistent_cache_hit_count,
            "ground_transition_argument_present": False,
            "local_ground_distinction_permitted": (
                not self.certified and self.failure_reason == "NO_HORIZON_CERTIFICATE"
            ),
            "compute_cap_failure_is_not_a_ground_label_request": (
                self.failure_reason == "MODEL_EXECUTION_RESOURCE_CAP"
            ),
            "certificate_id": self.certificate_id,
        }


class FairRankedPlannerSessionV184:
    def __init__(
        self, model: FairRankedCompiledWorldModelV184, *, horizon: int
    ) -> None:
        if (
            type(model) is not FairRankedCompiledWorldModelV184
            or type(horizon) is not int
            or horizon <= 2
        ):
            _fail("V184 planner requires one fair-ranked model and H>2")
        self._model = model
        self._horizon = horizon
        self._memo: dict[
            tuple[tuple[int, ...], int],
            tuple[int | None, tuple[int, ...] | None, int | None],
        ] = {}

    def certify(self, state: Sequence[int]) -> FairRankedPlanCertificateV184:
        frozen_state = tuple(state)
        events = 0
        cache_hits = 0
        resource_failure = False

        def minimum_rank(
            current: tuple[int, ...], limit: int
        ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
            nonlocal events, cache_hits, resource_failure
            events += 1
            try:
                if self._model.terminal(current):
                    return 0, None, None
            except OpenWorldRankedMachineV183Error:
                resource_failure = True
                return None, None, None
            if limit == 0:
                return None, None, None
            key = (current, limit)
            if key in self._memo:
                cache_hits += 1
                return self._memo[key]
            candidates: list[tuple[int, tuple[int, ...], int]] = []
            for action in self._model.legal_actions:
                try:
                    support = self._model.predict_support(current, action)
                except OpenWorldRankedMachineV183Error:
                    resource_failure = True
                    continue
                ranks = [minimum_rank(successor, limit - 1)[0] for successor in support]
                if any(rank is None for rank in ranks):
                    continue
                upper = max(int(rank) for rank in ranks)
                candidates.append((upper + 1, action, upper))
            self._memo[key] = min(candidates) if candidates else (None, None, None)
            return self._memo[key]

        rank, action, upper = minimum_rank(frozen_state, self._horizon)
        certified = rank is not None and rank > 0 and action is not None
        reason = None
        if not certified:
            reason = (
                "MODEL_EXECUTION_RESOURCE_CAP"
                if resource_failure
                else "NO_HORIZON_CERTIFICATE"
            )
        payload = {
            "schema": "acfqp.fair_ranked_plan_certificate.v184",
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
            "local_ground_distinction_permitted": (
                not certified and reason == "NO_HORIZON_CERTIFICATE"
            ),
            "compute_cap_failure_is_not_a_ground_label_request": (
                reason == "MODEL_EXECUTION_RESOURCE_CAP"
            ),
        }
        return FairRankedPlanCertificateV184(
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
            domains.extension_content_id_v184(
                domains.CONSTRUCTION_K7_PLAN_CERTIFICATE_V184_DOMAIN,
                payload,
            ),
        )


__all__ = (
    "FairRankedCompiledWorldModelV184",
    "FairRankedPlannerSessionV184",
    "FairSearchResourceExhaustedV184",
    "compile_fair_ranked_world_model_v184",
    "enumerate_expressions_fairly_v184",
    "enumerate_fair_ranked_candidates_v184",
    "synthesize_fair_ranked_scalar_program_v184",
)
