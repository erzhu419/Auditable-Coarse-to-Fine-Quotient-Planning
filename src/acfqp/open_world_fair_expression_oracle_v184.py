"""Opaque stochastic oracle for the fresh V184 multi-distribution campaign."""

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
    "noise_support",
    "noise_seed_root",
    "initial_seed_root",
    "ood_extra_coordinate_rule",
}


class OpenWorldFairExpressionOracleV184Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldFairExpressionOracleV184Error(message)


def fair_expression_manifest_commitment_v184(document: Mapping[str, Any]) -> str:
    if type(document) is not dict or set(document) != _MANIFEST_FIELDS:
        _fail("V184 manifest schema changed")
    return hashlib.sha256(
        b"acfqp:v184:opaque-fair-expression-manifest\x00"
        + canonical_json_bytes(dict(document))
    ).hexdigest()


@dataclass(slots=True)
class FairExpressionOracleV184:
    manifest_commitment: str
    manifest_index: int
    role: str
    state_width: int
    action_width: int
    legal_actions: tuple[tuple[int, ...], ...]
    horizon: int
    noise_support: tuple[int, ...]
    noise_seed_root: str = field(repr=False)
    initial_seed_root: str = field(repr=False)
    ood_extra_coordinate_rule: str | None
    query_count: int = 0

    def schema_signature(self) -> tuple[Any, ...]:
        return self.state_width, self.action_width, self.legal_actions

    def initial_state(self, occurrence_index: int) -> tuple[int, ...]:
        if type(occurrence_index) is not int or occurrence_index < 0:
            _fail("V184 initial occurrence index changed")
        digest = hashlib.sha256(
            bytes.fromhex(self.initial_seed_root)
            + occurrence_index.to_bytes(8, "big")
        ).digest()
        state = [digest[0] % 7, 1 + digest[1] % 5, digest[2] % 8]
        if self.state_width == 4:
            state.append(digest[3] % 9)
        return tuple(state)

    def terminal(self, state: Sequence[int]) -> bool:
        if (
            len(state) != self.state_width
            or any(type(value) is not int or value < 0 for value in state)
        ):
            _fail("V184 terminal input crossed its opaque schema")
        return state[1] == 0

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
            _fail("V184 query crossed its manifest schema")
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
        action_value = frozen_action[0]
        successor = [
            frozen_state[0] + action_value + noise,
            max(0, frozen_state[1] - 1),
            frozen_state[2] ^ action_value,
        ]
        if self.state_width == 4:
            if self.ood_extra_coordinate_rule != "INCREMENT_MOD_11":
                _fail("V184 OOD coordinate rule changed")
            successor.append((frozen_state[3] + 1) % 11)
        self.query_count += 1
        return RawMachineTransitionV182.observe(
            occurrence_index=occurrence_index,
            query_index=query_index,
            state=frozen_state,
            action=frozen_action,
            successor=tuple(successor),
            terminal=successor[1] == 0,
        )


def reveal_fair_expression_oracle_v184(
    *, manifest_bytes: bytes, expected_commitment: str
) -> FairExpressionOracleV184:
    document = loads_canonical_json(manifest_bytes)
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != manifest_bytes
        or fair_expression_manifest_commitment_v184(document) != expected_commitment
        or document["schema"] != "acfqp.opaque_fair_expression_manifest.v184"
        or type(document["manifest_index"]) is not int
        or document["manifest_index"] < 0
        or type(document["role"]) is not str
        or type(document["reveal_salt"]) is not str
        or len(document["reveal_salt"]) != 64
        or type(document["state_width"]) is not int
        or document["state_width"] not in {3, 4}
        or document["action_width"] != 1
        or document["legal_actions"] != [[0], [1]]
        or document["horizon"] != 3
        or document["noise_support"] != [0, 1]
        or any(
            type(document[key]) is not str or len(document[key]) != 64
            for key in ("noise_seed_root", "initial_seed_root")
        )
        or document["ood_extra_coordinate_rule"]
        != ("INCREMENT_MOD_11" if document["state_width"] == 4 else None)
    ):
        _fail("V184 manifest preimage changed")
    return FairExpressionOracleV184(
        expected_commitment,
        document["manifest_index"],
        document["role"],
        document["state_width"],
        document["action_width"],
        tuple(tuple(row) for row in document["legal_actions"]),
        document["horizon"],
        tuple(document["noise_support"]),
        document["noise_seed_root"],
        document["initial_seed_root"],
        document["ood_extra_coordinate_rule"],
    )


__all__ = (
    "FairExpressionOracleV184",
    "fair_expression_manifest_commitment_v184",
    "reveal_fair_expression_oracle_v184",
)
