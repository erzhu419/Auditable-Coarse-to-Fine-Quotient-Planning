"""Opaque queue/buffer stochastic oracle for the fresh V185 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


_MANIFEST_FIELDS = {
    "schema",
    "manifest_index",
    "role",
    "reveal_salt",
    "state_width",
    "action_width",
    "legal_actions",
    "horizon",
    "state_permutation",
    "action_permutation",
    "noise_support",
    "noise_seed_root",
    "initial_seed_root",
    "ood_rule",
}
_CANONICAL_STATE_WIDTH = 8
_CANONICAL_ACTION_WIDTH = 2
_LOAD_COORDINATES = (0, 2, 3, 4, 5, 6)
_HORIZON_COORDINATE = 1
_PARITY_COORDINATE = 7


class OpenWorldCompositeMacroOracleV185Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCompositeMacroOracleV185Error(message)


def composite_macro_manifest_commitment_v185(document: Mapping[str, Any]) -> str:
    if type(document) is not dict or set(document) != _MANIFEST_FIELDS:
        _fail("V185 manifest schema changed")
    return hashlib.sha256(
        b"acfqp:v185:opaque-composite-macro-manifest\x00"
        + canonical_json_bytes(dict(document))
    ).hexdigest()


def _permute(values: Sequence[int], permutation: Sequence[int]) -> tuple[int, ...]:
    result = [0] * len(permutation)
    for canonical_index, observed_index in enumerate(permutation):
        result[observed_index] = values[canonical_index]
    return tuple(result)


def _unpermute(values: Sequence[int], permutation: Sequence[int]) -> tuple[int, ...]:
    return tuple(values[observed_index] for observed_index in permutation)


@dataclass(slots=True)
class CompositeMacroOracleV185:
    manifest_commitment: str
    manifest_index: int
    role: str
    state_width: int
    action_width: int
    legal_actions: tuple[tuple[int, ...], ...]
    horizon: int
    state_permutation: tuple[int, ...]
    action_permutation: tuple[int, ...]
    noise_support: tuple[int, ...]
    noise_seed_root: str = field(repr=False)
    initial_seed_root: str = field(repr=False)
    ood_rule: str | None
    query_count: int = 0

    def schema_signature(self) -> tuple[Any, ...]:
        return self.state_width, self.action_width, self.legal_actions

    def initial_state(self, occurrence_index: int) -> tuple[int, ...]:
        if type(occurrence_index) is not int or occurrence_index < 0:
            _fail("V185 initial occurrence index changed")
        digest = hashlib.sha256(
            bytes.fromhex(self.initial_seed_root)
            + occurrence_index.to_bytes(8, "big")
        ).digest()
        canonical = [
            digest[0] % 5,
            1 + digest[1] % self.horizon,
            digest[2] % 5,
            digest[3] % 5,
            digest[4] % 5,
            digest[5] % 5,
            digest[6] % 5,
            digest[7] % 2,
        ]
        observed = list(_permute(canonical, self.state_permutation))
        if self.state_width == _CANONICAL_STATE_WIDTH + 1:
            observed.append(digest[8] % 13)
        return tuple(observed)

    def terminal(self, state: Sequence[int]) -> bool:
        if (
            len(state) != self.state_width
            or any(type(value) is not int or value < 0 for value in state)
        ):
            _fail("V185 terminal input crossed its opaque schema")
        canonical = _unpermute(
            state[:_CANONICAL_STATE_WIDTH], self.state_permutation
        )
        return canonical[_HORIZON_COORDINATE] == 0

    def query(
        self,
        *,
        occurrence_index: int,
        query_index: int,
        state: Sequence[int],
        action: Sequence[int],
    ) -> RawMachineTransitionV182:
        frozen_state = tuple(state)
        frozen_action = tuple(action)
        if (
            type(occurrence_index) is not int
            or occurrence_index < 0
            or type(query_index) is not int
            or query_index < 0
            or len(frozen_state) != self.state_width
            or frozen_action not in self.legal_actions
            or any(
                type(value) is not int or value < 0
                for value in (*frozen_state, *frozen_action)
            )
        ):
            _fail("V185 query crossed its manifest schema")
        canonical_state = _unpermute(
            frozen_state[:_CANONICAL_STATE_WIDTH], self.state_permutation
        )
        canonical_action = _unpermute(frozen_action, self.action_permutation)
        arrival, service = canonical_action
        digest = hashlib.sha256(
            bytes.fromhex(self.noise_seed_root)
            + occurrence_index.to_bytes(8, "big")
            + query_index.to_bytes(8, "big")
            + canonical_json_bytes(
                {"state": list(frozen_state), "action": list(frozen_action)}
            )
        ).digest()
        noise = self.noise_support[
            int.from_bytes(digest[:8], "big") % len(self.noise_support)
        ]
        successor = list(canonical_state)
        for coordinate in _LOAD_COORDINATES:
            successor[coordinate] = max(
                canonical_state[coordinate] + arrival - service,
                0,
            )
        successor[_LOAD_COORDINATES[0]] += noise
        successor[_HORIZON_COORDINATE] = max(
            canonical_state[_HORIZON_COORDINATE] - 1,
            0,
        )
        successor[_PARITY_COORDINATE] = (
            canonical_state[_PARITY_COORDINATE] ^ arrival
        )
        observed_successor = list(_permute(successor, self.state_permutation))
        if self.state_width == _CANONICAL_STATE_WIDTH + 1:
            if self.ood_rule != "OPAQUE_COUNTER_INCREMENT_MOD_13":
                _fail("V185 OOD rule changed")
            observed_successor.append((frozen_state[-1] + 1) % 13)
        self.query_count += 1
        return RawMachineTransitionV182.observe(
            occurrence_index=occurrence_index,
            query_index=query_index,
            state=frozen_state,
            action=frozen_action,
            successor=tuple(observed_successor),
            terminal=successor[_HORIZON_COORDINATE] == 0,
        )


def reveal_composite_macro_oracle_v185(
    *, manifest_bytes: bytes, expected_commitment: str
) -> CompositeMacroOracleV185:
    document = loads_canonical_json(manifest_bytes)
    state_width = document.get("state_width") if type(document) is dict else None
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != manifest_bytes
        or composite_macro_manifest_commitment_v185(document) != expected_commitment
        or document["schema"] != "acfqp.opaque_composite_macro_manifest.v185"
        or type(document["manifest_index"]) is not int
        or document["manifest_index"] < 0
        or type(document["role"]) is not str
        or type(document["reveal_salt"]) is not str
        or len(document["reveal_salt"]) != 64
        or state_width not in {_CANONICAL_STATE_WIDTH, _CANONICAL_STATE_WIDTH + 1}
        or document["action_width"] != _CANONICAL_ACTION_WIDTH
        or document["legal_actions"]
        != [[0, 0], [0, 1], [1, 0], [1, 1]]
        or document["horizon"] != 4
        or sorted(document["state_permutation"])
        != list(range(_CANONICAL_STATE_WIDTH))
        or sorted(document["action_permutation"])
        != list(range(_CANONICAL_ACTION_WIDTH))
        or document["noise_support"] != [0, 1]
        or any(
            type(document[key]) is not str or len(document[key]) != 64
            for key in ("noise_seed_root", "initial_seed_root")
        )
        or document["ood_rule"]
        != (
            "OPAQUE_COUNTER_INCREMENT_MOD_13"
            if state_width == _CANONICAL_STATE_WIDTH + 1
            else None
        )
    ):
        _fail("V185 manifest preimage changed")
    return CompositeMacroOracleV185(
        expected_commitment,
        document["manifest_index"],
        document["role"],
        document["state_width"],
        document["action_width"],
        tuple(tuple(row) for row in document["legal_actions"]),
        document["horizon"],
        tuple(document["state_permutation"]),
        tuple(document["action_permutation"]),
        tuple(document["noise_support"]),
        document["noise_seed_root"],
        document["initial_seed_root"],
        document["ood_rule"],
    )


__all__ = (
    "CompositeMacroOracleV185",
    "composite_macro_manifest_commitment_v185",
    "reveal_composite_macro_oracle_v185",
)
