"""Portable V7 rule encoder and finite cell dynamics without a state lookup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence, TYPE_CHECKING

from .controlled_predictive_quotient_v1 import Cell, CompiledModel, Outcome

if TYPE_CHECKING:
    from .controlled_predictive_encoder_v7 import RuleEncoder


Code = tuple[int, str, tuple[str, ...], int]


def _code_payload(code: Code) -> list[Any]:
    horizon, status, legal_actions, leaf = code
    return [horizon, status, list(legal_actions), leaf]


def _restore_code(code: Sequence[Any]) -> Code:
    return (int(code[0]), str(code[1]), tuple(code[2]), int(code[3]))


def freeze_artifact_payload(
    encoder: RuleEncoder,
    compiled: CompiledModel,
    code_to_cell: Mapping[Code, int],
    *,
    example_board: Sequence[int] | None = None,
    example_horizon: int | None = None,
) -> dict[str, Any]:
    """Store the trained rules and planning kernel, excluding training/audit maps."""
    payload: dict[str, Any] = {
        "schema": "controlled_predictive_encoder_artifact_v7",
        "encoder": encoder.to_payload(),
        "compiled_model": {
            "cells": [[cell, record.layer, record.terminal]
                      for cell, record in sorted(compiled.cells.items())],
            "rows": [[cell, action, [[outcome.probability, outcome.next_state, outcome.reward]
                                    for outcome in row]]
                     for (cell, action), row in sorted(compiled.rows.items())],
            "roots": list(compiled.roots),
        },
        "code_to_cell": [[_code_payload(code), cell]
                         for code, cell in sorted(code_to_cell.items())],
    }
    if example_board is not None:
        if len(example_board) != 16 or example_horizon is None:
            raise ValueError("example input needs a 16-rank board and remaining horizon")
        payload["example_input"] = {"board": list(example_board), "remaining_horizon": example_horizon}
    return payload


def restore_artifact_payload(payload: Mapping[str, Any]) -> tuple[RuleEncoder, CompiledModel, dict[Code, int]]:
    from .controlled_predictive_encoder_v7 import RuleEncoder

    if payload["schema"] != "controlled_predictive_encoder_artifact_v7":
        raise ValueError("expected V7 executable encoder artifact")
    encoder = RuleEncoder.from_payload(payload["encoder"])
    source = payload["compiled_model"]
    compiled = CompiledModel(
        cells={cell: Cell(layer, status, ()) for cell, layer, status in source["cells"]},
        rows={(cell, action): tuple(Outcome(*outcome) for outcome in row)
              for cell, action, row in source["rows"]},
        roots=tuple(source["roots"]), state_to_cell={}, diameters={},
    )
    return encoder, compiled, {_restore_code(code): cell for code, cell in payload["code_to_cell"]}


def _json_bytes(payload: Any) -> int:
    return len(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def artifact_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Report separate compact-JSON costs, including the enclosing artifact."""
    return {
        "storage_measurement": "compact_utf8_json_bytes",
        "encoder_bytes": _json_bytes(payload["encoder"]),
        "minimal_compiled_model_bytes": _json_bytes(payload["compiled_model"]),
        "code_to_cell_bytes": _json_bytes(payload["code_to_cell"]),
        "example_input_bytes": _json_bytes(payload["example_input"]) if "example_input" in payload else 0,
        "artifact_total_bytes": _json_bytes(payload),
    }


def write_encoder_artifact(path: str | Path, payload: Mapping[str, Any]) -> None:
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), allow_nan=False)


def load_encoder_artifact(path: str | Path) -> tuple[RuleEncoder, CompiledModel, dict[Code, int]]:
    return restore_artifact_payload(json.loads(Path(path).read_text(encoding="utf-8")))
