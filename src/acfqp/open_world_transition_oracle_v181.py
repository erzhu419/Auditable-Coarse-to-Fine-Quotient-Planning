"""Opaque raw-transition oracle for salted V181 manifest reveals.

The oracle verifies a preregistered commitment and exposes only schema widths,
legal opaque action vectors, deterministic IID initial states, and sampled raw
state/action/successor/terminal observations.  Synthesizer code is never given
the revealed transition or terminal programs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import product
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MANIFEST_COMMITMENT_PREFIX = b"acfqp:v181:manifest-commitment\x00"


class OpenWorldTransitionOracleV181Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldTransitionOracleV181Error(message)


def manifest_commitment_v181(document: Mapping[str, Any]) -> str:
    if not isinstance(document, Mapping):
        _fail("manifest commitment requires one mapping")
    return hashlib.sha256(
        MANIFEST_COMMITMENT_PREFIX + canonical_json_bytes(dict(document))
    ).hexdigest()


def _expression(value: Any) -> tuple[Any, ...]:
    if type(value) is not list or not value or type(value[0]) is not str:
        _fail("revealed program is not one prefix expression")
    return tuple(
        _expression(item) if type(item) is list else item for item in value
    )


def _evaluate(
    expression: tuple[Any, ...],
    state: Sequence[int],
    action: Sequence[int],
    support: Sequence[int],
) -> int | bool:
    opcode = expression[0]
    if opcode in {"S", "A", "W", "K"}:
        if len(expression) != 2 or type(expression[1]) is not int:
            _fail("revealed atomic expression changed")
        if opcode == "K":
            return expression[1]
        source = state if opcode == "S" else action if opcode == "A" else support
        if not 0 <= expression[1] < len(source):
            _fail("revealed input coordinate is outside its vector")
        return source[expression[1]]
    arity = {
        "ADD": 2,
        "SUB": 2,
        "MOD": 2,
        "MIN": 2,
        "MAX": 2,
        "XOR": 2,
        "EQ": 2,
        "LT": 2,
        "AND": 2,
        "SELECT": 3,
    }
    if opcode not in arity or len(expression) != arity[opcode] + 1:
        _fail("revealed opcode or arity is outside the protocol")
    values = [_evaluate(item, state, action, support) for item in expression[1:]]
    if opcode == "ADD":
        return int(values[0]) + int(values[1])
    if opcode == "SUB":
        return int(values[0]) - int(values[1])
    if opcode == "MOD":
        if type(values[1]) is not int or values[1] <= 0:
            _fail("revealed modulus changed")
        return int(values[0]) % values[1]
    if opcode == "MIN":
        return min(int(values[0]), int(values[1]))
    if opcode == "MAX":
        return max(int(values[0]), int(values[1]))
    if opcode == "XOR":
        return int(values[0]) ^ int(values[1])
    if opcode == "EQ":
        return int(values[0]) == int(values[1])
    if opcode == "LT":
        return int(values[0]) < int(values[1])
    if opcode == "AND":
        return bool(values[0]) and bool(values[1])
    return int(values[1]) if bool(values[0]) else int(values[2])


@dataclass(frozen=True, slots=True)
class RawTransitionObservationV181:
    occurrence_index: int
    query_index: int
    state: tuple[int, ...]
    action: tuple[int, ...]
    successor: tuple[int, ...]
    terminal: bool
    observation_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_raw_transition_observation.v181",
            "occurrence_index": self.occurrence_index,
            "query_index": self.query_index,
            "state": list(self.state),
            "action": list(self.action),
            "successor": list(self.successor),
            "terminal": self.terminal,
            "observation_id": self.observation_id,
        }


@dataclass(frozen=True, slots=True)
class OpaqueTransitionOracleV181:
    _manifest_bytes: bytes = field(repr=False, compare=False)
    manifest_commitment: str
    state_width: int
    action_width: int
    horizon: int
    moduli: tuple[int, ...]
    _transition_programs: tuple[tuple[Any, ...], ...] = field(
        repr=False, compare=False
    )
    _terminal_program: tuple[Any, ...] = field(repr=False, compare=False)
    _support: tuple[tuple[int, ...], ...] = field(repr=False, compare=False)

    def legal_actions(self) -> tuple[tuple[int, ...], ...]:
        return tuple(product(range(3), repeat=self.action_width))

    def initial_state(self, occurrence_index: int) -> tuple[int, ...]:
        if type(occurrence_index) is not int or occurrence_index < 0:
            _fail("occurrence index is invalid")
        digest = hashlib.sha256(
            self.manifest_commitment.encode()
            + b"\x00initial\x00"
            + str(occurrence_index).encode()
        ).digest()
        values = [digest[index] % modulus for index, modulus in enumerate(self.moduli)]
        values[3] = min(values[3], self.horizon - 2)
        return tuple(values)

    def query(
        self,
        *,
        occurrence_index: int,
        query_index: int,
        state: Sequence[int],
        action: Sequence[int],
    ) -> RawTransitionObservationV181:
        if (
            type(occurrence_index) is not int
            or occurrence_index < 0
            or type(query_index) is not int
            or query_index < 0
            or len(state) != self.state_width
            or len(action) != self.action_width
            or any(type(value) is not int for value in (*state, *action))
            or tuple(action) not in self.legal_actions()
        ):
            _fail("raw transition query crosses the opaque oracle schema")
        choice_digest = hashlib.sha256(
            self.manifest_commitment.encode()
            + b"\x00sample\x00"
            + canonical_json_bytes(
                {
                    "occurrence_index": occurrence_index,
                    "query_index": query_index,
                    "state": list(state),
                    "action": list(action),
                }
            )
        ).digest()
        support = self._support[int.from_bytes(choice_digest[:8], "big") % len(self._support)]
        successor = tuple(
            int(_evaluate(program, state, action, support))
            for program in self._transition_programs
        )
        if len(successor) != self.state_width:
            _fail("revealed transition program width changed")
        terminal = _evaluate(
            self._terminal_program,
            successor,
            (0,) * self.action_width,
            support,
        )
        if type(terminal) is not bool:
            _fail("revealed terminal program is not boolean")
        payload = {
            "schema": "acfqp.open_world_raw_transition_observation.v181",
            "manifest_commitment": self.manifest_commitment,
            "occurrence_index": occurrence_index,
            "query_index": query_index,
            "state": list(state),
            "action": list(action),
            "successor": list(successor),
            "terminal": terminal,
        }
        return RawTransitionObservationV181(
            occurrence_index,
            query_index,
            tuple(state),
            tuple(action),
            successor,
            terminal,
            hashlib.sha256(
                b"acfqp:v181:raw-transition\x00" + canonical_json_bytes(payload)
            ).hexdigest(),
        )


def reveal_opaque_transition_oracle_v181(
    *, manifest_bytes: bytes, expected_commitment: str
) -> OpaqueTransitionOracleV181:
    if type(manifest_bytes) is not bytes or not manifest_bytes:
        _fail("manifest reveal bytes are missing")
    try:
        document = loads_canonical_json(manifest_bytes)
    except (TypeError, ValueError) as error:
        raise OpenWorldTransitionOracleV181Error(
            "manifest reveal bytes are noncanonical"
        ) from error
    keys = {
        "schema",
        "manifest_index",
        "reveal_salt",
        "state_width",
        "action_width",
        "horizon",
        "moduli",
        "transition_programs",
        "terminal_program",
        "support",
        "iid_initial_seed_root",
    }
    if (
        type(document) is not dict
        or set(document) != keys
        or canonical_json_bytes(document) != manifest_bytes
        or document["schema"] != "acfqp.opaque_transition_manifest.v181"
        or type(expected_commitment) is not str
        or len(expected_commitment) != 64
        or manifest_commitment_v181(document) != expected_commitment
        or type(document["reveal_salt"]) is not str
        or len(document["reveal_salt"]) != 64
        or type(document["state_width"]) is not int
        or not 4 <= document["state_width"] <= 16
        or type(document["action_width"]) is not int
        or not 1 <= document["action_width"] <= 4
        or type(document["horizon"]) is not int
        or document["horizon"] < 5
        or type(document["moduli"]) is not list
        or len(document["moduli"]) != document["state_width"]
        or any(type(value) is not int or value < 2 for value in document["moduli"])
        or type(document["transition_programs"]) is not list
        or len(document["transition_programs"]) != document["state_width"]
        or type(document["support"]) is not list
        or len(document["support"]) < 2
        or any(type(row) is not list or not row for row in document["support"])
    ):
        _fail("manifest reveal schema or commitment changed")
    transitions = tuple(_expression(row) for row in document["transition_programs"])
    terminal = _expression(document["terminal_program"])
    support = tuple(tuple(row) for row in document["support"])
    if len({len(row) for row in support}) != 1 or any(
        any(type(value) is not int for value in row) for row in support
    ):
        _fail("manifest support vectors changed")
    return OpaqueTransitionOracleV181(
        manifest_bytes,
        expected_commitment,
        document["state_width"],
        document["action_width"],
        document["horizon"],
        tuple(document["moduli"]),
        transitions,
        terminal,
        support,
    )


__all__ = (
    "OpaqueTransitionOracleV181",
    "OpenWorldTransitionOracleV181Error",
    "RawTransitionObservationV181",
    "manifest_commitment_v181",
    "reveal_opaque_transition_oracle_v181",
)
