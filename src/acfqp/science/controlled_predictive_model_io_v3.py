"""Portable JSON for the development model's finite cells and action dynamics."""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_quotient_v1 import Cell, CompiledModel, Outcome


def compiled_to_payload(model: CompiledModel) -> dict[str, Any]:
    """Store dynamics and the covered-state lookup, without query answers."""
    return {
        "cells": {cell: asdict(value) for cell, value in model.cells.items()},
        "rows": [[cell, action, [asdict(outcome) for outcome in row]]
                 for (cell, action), row in sorted(model.rows.items())],
        "roots": list(model.roots),
        "state_to_cell": model.state_to_cell,
        "diameters": model.diameters,
    }


def load_compiled(path: Path) -> CompiledModel:
    """Read the current development writer's JSON into the ordinary planner API."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CompiledModel(
        cells={int(cell): Cell(value["layer"], value["terminal"], tuple(value["members"]))
               for cell, value in payload["cells"].items()},
        rows={(cell, action): tuple(Outcome(**outcome) for outcome in row)
              for cell, action, row in payload["rows"]},
        roots=tuple(payload["roots"]),
        state_to_cell={int(state): cell for state, cell in payload["state_to_cell"].items()},
        diameters={int(cell): value for cell, value in payload["diameters"].items()},
    )
