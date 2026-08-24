"""Commitment-bound opaque transition oracle for V182 machine programs."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import product
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_universal_machine_v182 import (
    ProgramV182,
    execute_program_v182,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_PREFIX = b"acfqp:v182:opaque-machine-manifest\x00"


class OpenWorldMachineOracleV182Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldMachineOracleV182Error(message)


def machine_manifest_commitment_v182(document: Mapping[str, Any]) -> str:
    if not isinstance(document, Mapping):
        _fail("V182 machine manifest must be one mapping")
    return hashlib.sha256(
        MANIFEST_PREFIX + canonical_json_bytes(dict(document))
    ).hexdigest()


def _program(value: Any) -> ProgramV182:
    if type(value) is not list or not value:
        _fail("V182 manifest program is empty")
    program = tuple(
        tuple(instruction) if type(instruction) is list else ()
        for instruction in value
    )
    if any(not instruction for instruction in program):
        _fail("V182 manifest instruction changed")
    return program


@dataclass(frozen=True, slots=True)
class OpaqueMachineOracleV182:
    _manifest_bytes: bytes = field(repr=False, compare=False)
    manifest_commitment: str
    state_width: int
    action_width: int
    action_cardinality: int
    horizon: int
    initial_moduli: tuple[int, ...]
    register_count: int
    maximum_execution_steps: int
    _coordinate_programs: tuple[ProgramV182, ...] = field(
        repr=False, compare=False
    )
    _residual_supports: tuple[tuple[int, ...], ...] = field(
        repr=False, compare=False
    )
    _terminal_program: ProgramV182 = field(repr=False, compare=False)

    def schema_signature(self) -> tuple[int, int, int]:
        return self.state_width, self.action_width, self.action_cardinality

    def legal_actions(self) -> tuple[tuple[int, ...], ...]:
        return tuple(product(range(self.action_cardinality), repeat=self.action_width))

    def _run(
        self, program: ProgramV182, state: Sequence[int], action: Sequence[int]
    ) -> int:
        result = execute_program_v182(
            program,
            state=state,
            action=action,
            register_count=self.register_count,
            maximum_steps=self.maximum_execution_steps,
        )
        if not result.halted or result.output is None:
            _fail("hidden V182 machine program did not halt within its commitment")
        return result.output

    def terminal(self, state: Sequence[int]) -> bool:
        result = self._run(
            self._terminal_program,
            state,
            (0,) * self.action_width,
        )
        if result not in {0, 1}:
            _fail("hidden V182 terminal program is not boolean")
        return bool(result)

    def initial_state(self, occurrence_index: int) -> tuple[int, ...]:
        if type(occurrence_index) is not int or occurrence_index < 0:
            _fail("V182 initial occurrence index changed")
        for attempt in range(256):
            digest = hashlib.sha256(
                self.manifest_commitment.encode()
                + b"\x00initial\x00"
                + occurrence_index.to_bytes(8, "big")
                + attempt.to_bytes(2, "big")
            ).digest()
            state = tuple(
                digest[index] % modulus
                for index, modulus in enumerate(self.initial_moduli)
            )
            if not self.terminal(state):
                return state
        _fail("V182 manifest could not provide a nonterminal initial state")

    def query(
        self,
        *,
        occurrence_index: int,
        query_index: int,
        state: Sequence[int],
        action: Sequence[int],
    ) -> RawMachineTransitionV182:
        if (
            type(occurrence_index) is not int
            or occurrence_index < 0
            or type(query_index) is not int
            or query_index < 0
            or len(state) != self.state_width
            or tuple(action) not in self.legal_actions()
            or any(type(value) is not int or value < 0 for value in state)
        ):
            _fail("V182 query crossed its opaque schema")
        digest = hashlib.sha256(
            self.manifest_commitment.encode()
            + b"\x00support\x00"
            + canonical_json_bytes(
                {
                    "occurrence_index": occurrence_index,
                    "query_index": query_index,
                    "state": list(state),
                    "action": list(action),
                }
            )
        ).digest()
        successor = []
        for index, (program, support) in enumerate(
            zip(self._coordinate_programs, self._residual_supports, strict=True)
        ):
            base = self._run(program, state, action)
            residual = support[
                int.from_bytes(digest[index : index + 4], "big") % len(support)
            ]
            value = base + residual
            if value < 0:
                _fail("hidden V182 transition left the nonnegative carrier")
            successor.append(value)
        frozen_successor = tuple(successor)
        return RawMachineTransitionV182.observe(
            occurrence_index=occurrence_index,
            query_index=query_index,
            state=state,
            action=action,
            successor=frozen_successor,
            terminal=self.terminal(frozen_successor),
        )


def reveal_opaque_machine_oracle_v182(
    *, manifest_bytes: bytes, expected_commitment: str
) -> OpaqueMachineOracleV182:
    if type(manifest_bytes) is not bytes or not manifest_bytes:
        _fail("V182 manifest bytes are absent")
    document = loads_canonical_json(manifest_bytes)
    fields = {
        "schema",
        "manifest_index",
        "reveal_salt",
        "state_width",
        "action_width",
        "action_cardinality",
        "horizon",
        "initial_moduli",
        "register_count",
        "maximum_execution_steps",
        "coordinate_programs",
        "residual_supports",
        "terminal_program",
        "iid_initial_seed_root",
    }
    if (
        type(document) is not dict
        or set(document) != fields
        or canonical_json_bytes(document) != manifest_bytes
        or document["schema"] != "acfqp.opaque_machine_manifest.v182"
        or machine_manifest_commitment_v182(document) != expected_commitment
        or type(document["manifest_index"]) is not int
        or type(document["reveal_salt"]) is not str
        or len(document["reveal_salt"]) != 64
        or type(document["state_width"]) is not int
        or not 2 <= document["state_width"] <= 16
        or type(document["action_width"]) is not int
        or not 1 <= document["action_width"] <= 4
        or type(document["action_cardinality"]) is not int
        or not 2 <= document["action_cardinality"] <= 8
        or type(document["horizon"]) is not int
        or document["horizon"] < 2
        or type(document["initial_moduli"]) is not list
        or len(document["initial_moduli"]) != document["state_width"]
        or any(type(value) is not int or value < 2 for value in document["initial_moduli"])
        or type(document["register_count"]) is not int
        or not 2 <= document["register_count"] <= 8
        or type(document["maximum_execution_steps"]) is not int
        or document["maximum_execution_steps"] < 4
        or type(document["coordinate_programs"]) is not list
        or len(document["coordinate_programs"]) != document["state_width"]
        or type(document["residual_supports"]) is not list
        or len(document["residual_supports"]) != document["state_width"]
        or any(
            type(row) is not list
            or not row
            or any(type(value) is not int for value in row)
            for row in document["residual_supports"]
        )
        or type(document["iid_initial_seed_root"]) is not str
        or len(document["iid_initial_seed_root"]) != 64
    ):
        _fail("V182 manifest schema or commitment changed")
    programs = tuple(_program(row) for row in document["coordinate_programs"])
    terminal = _program(document["terminal_program"])
    supports = tuple(tuple(sorted(set(row))) for row in document["residual_supports"])
    oracle = OpaqueMachineOracleV182(
        manifest_bytes,
        expected_commitment,
        document["state_width"],
        document["action_width"],
        document["action_cardinality"],
        document["horizon"],
        tuple(document["initial_moduli"]),
        document["register_count"],
        document["maximum_execution_steps"],
        programs,
        supports,
        terminal,
    )
    for index, modulus in enumerate(oracle.initial_moduli):
        probe_state = tuple(0 for _ in oracle.initial_moduli)
        probe_action = tuple(0 for _ in range(oracle.action_width))
        if oracle._run(programs[index], probe_state, probe_action) >= 10 * modulus:
            _fail("V182 hidden program exceeds its public carrier probe")
    return oracle


__all__ = (
    "OpaqueMachineOracleV182",
    "OpenWorldMachineOracleV182Error",
    "machine_manifest_commitment_v182",
    "reveal_opaque_machine_oracle_v182",
)
