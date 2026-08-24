"""Hidden black-box generator for fresh V183 ranked-machine domains."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class OpenWorldRankedMachineOracleV183Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldRankedMachineOracleV183Error(message)


def ranked_machine_manifest_commitment_v183(document: Mapping[str, Any]) -> str:
    if not isinstance(document, Mapping):
        _fail("V183 oracle manifest is not one mapping")
    raw = canonical_json_bytes(dict(document))
    return hashlib.sha256(b"acfqp:v183:ranked-oracle-manifest\x00" + raw).hexdigest()


class RankedMachineOracleV183:
    def __init__(self, manifest: Mapping[str, Any], commitment: str) -> None:
        required = {
            "schema",
            "manifest_index",
            "reveal_salt",
            "state_width",
            "action_width",
            "legal_actions",
            "horizon",
            "coordinate_0_multiplier",
            "coordinate_0_action_offset",
            "coordinate_0_stochastic_support",
            "coordinate_1_decrement",
            "terminal_coordinate",
            "iid_initial_seed_root",
        }
        document = loads_canonical_json(canonical_json_bytes(dict(manifest)))
        if type(document) is not dict or set(document) != required:
            _fail("V183 oracle manifest fields changed")
        legal_actions = tuple(tuple(row) for row in document["legal_actions"])
        if not (
            document["schema"] == "acfqp.opaque_ranked_machine_manifest.v183"
            and type(document["manifest_index"]) is int
            and document["manifest_index"] >= 0
            and type(document["reveal_salt"]) is str
            and len(document["reveal_salt"]) == 64
            and type(document["state_width"]) is int
            and document["state_width"] >= 2
            and type(document["action_width"]) is int
            and document["action_width"] >= 1
            and legal_actions
            and len(set(legal_actions)) == len(legal_actions)
            and all(
                len(row) == document["action_width"]
                and all(type(value) is int and value >= 0 for value in row)
                for row in legal_actions
            )
            and type(document["horizon"]) is int
            and document["horizon"] > 2
            and type(document["coordinate_0_multiplier"]) is int
            and document["coordinate_0_multiplier"] >= 1
            and type(document["coordinate_0_action_offset"]) is int
            and 0 <= document["coordinate_0_action_offset"] < document["action_width"]
            and type(document["coordinate_0_stochastic_support"]) is list
            and document["coordinate_0_stochastic_support"]
            and all(type(value) is int and value >= 0 for value in document["coordinate_0_stochastic_support"])
            and type(document["coordinate_1_decrement"]) is int
            and document["coordinate_1_decrement"] >= 1
            and document["terminal_coordinate"] == 1
            and type(document["iid_initial_seed_root"]) is str
            and len(document["iid_initial_seed_root"]) == 64
        ):
            _fail("V183 oracle manifest semantics changed")
        observed = ranked_machine_manifest_commitment_v183(document)
        if type(commitment) is not str or observed != commitment:
            _fail("V183 oracle manifest commitment changed")
        self._document = document
        self._commitment = commitment
        self._legal_actions = legal_actions

    @property
    def manifest_commitment(self) -> str:
        return self._commitment

    @property
    def state_width(self) -> int:
        return self._document["state_width"]

    @property
    def action_width(self) -> int:
        return self._document["action_width"]

    @property
    def horizon(self) -> int:
        return self._document["horizon"]

    @property
    def legal_actions(self) -> tuple[tuple[int, ...], ...]:
        return self._legal_actions

    def schema_signature(self) -> tuple[Any, ...]:
        return (self.state_width, self.action_width, self.legal_actions)

    def _noise(
        self,
        *,
        occurrence_index: int,
        query_index: int,
        state: Sequence[int],
        action: Sequence[int],
    ) -> int:
        support = tuple(self._document["coordinate_0_stochastic_support"])
        digest = hashlib.sha256(
            b"acfqp:v183:ranked-oracle-outcome\x00"
            + self._document["reveal_salt"].encode()
            + occurrence_index.to_bytes(8, "big")
            + query_index.to_bytes(8, "big")
            + canonical_json_bytes({"state": list(state), "action": list(action)})
        ).digest()
        return support[int.from_bytes(digest[:8], "big") % len(support)]

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
            or any(type(value) is not int or value < 0 for value in frozen_state)
            or frozen_action not in self.legal_actions
        ):
            _fail("V183 oracle query crossed its opaque schema")
        successor = list(frozen_state)
        successor[0] = (
            self._document["coordinate_0_multiplier"] * frozen_state[0]
            + frozen_action[self._document["coordinate_0_action_offset"]]
            + self._noise(
                occurrence_index=occurrence_index,
                query_index=query_index,
                state=frozen_state,
                action=frozen_action,
            )
        )
        successor[1] = max(
            0,
            frozen_state[1] - self._document["coordinate_1_decrement"],
        )
        for index in range(2, self.state_width):
            successor[index] = frozen_state[index]
        terminal = successor[self._document["terminal_coordinate"]] == 0
        return RawMachineTransitionV182.observe(
            occurrence_index=occurrence_index,
            query_index=query_index,
            state=frozen_state,
            action=frozen_action,
            successor=successor,
            terminal=terminal,
        )

    def initial_state(self, occurrence_index: int) -> tuple[int, ...]:
        if type(occurrence_index) is not int or occurrence_index < 0:
            _fail("V183 occurrence index changed")
        digest = hashlib.sha256(
            b"acfqp:v183:ranked-oracle-initial\x00"
            + self._document["iid_initial_seed_root"].encode()
            + occurrence_index.to_bytes(8, "big")
        ).digest()
        values = [1 + digest[0] % 3, 1 + digest[1] % (self.horizon + 1)]
        values.extend(1 + digest[2 + index] % 3 for index in range(self.state_width - 2))
        return tuple(values)

    def terminal(self, state: Sequence[int]) -> bool:
        frozen = tuple(state)
        if len(frozen) != self.state_width or any(type(value) is not int or value < 0 for value in frozen):
            _fail("V183 terminal query crossed its opaque schema")
        return frozen[self._document["terminal_coordinate"]] == 0


def reveal_ranked_machine_oracle_v183(
    *,
    manifest_bytes: bytes,
    expected_commitment: str,
) -> RankedMachineOracleV183:
    document = loads_canonical_json(manifest_bytes)
    if type(document) is not dict or canonical_json_bytes(document) != manifest_bytes:
        _fail("V183 oracle manifest is not canonical")
    return RankedMachineOracleV183(document, expected_commitment)


__all__ = (
    "OpenWorldRankedMachineOracleV183Error",
    "RankedMachineOracleV183",
    "ranked_machine_manifest_commitment_v183",
    "reveal_ranked_machine_oracle_v183",
)
