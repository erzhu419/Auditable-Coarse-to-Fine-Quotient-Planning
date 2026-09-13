"""Portable symbolic dynamics; loading and planning need no ground environment."""
from __future__ import annotations

from .controlled_predictive_quotient_v1 import Cell, CompiledModel, Outcome


def model_payload(build, compiled):
    return dict(schema='acfqp.causal_symbolic_model.v66',
        rule=dict(horizon=build.rule.horizon, forgotten_ranks=list(build.rule.forgotten_ranks),
                  certified=build.rule.certified),
        cells=[[cell, row.layer, row.terminal] for cell, row in sorted(compiled.cells.items())],
        rows=[[cell, action, [[o.probability, o.next_state, o.reward] for o in outcomes]]
              for (cell, action), outcomes in sorted(compiled.rows.items())],
        roots=list(compiled.roots),
        symbolic_boards=[[compiled.state_to_cell[state], list(board)] for state, board in sorted(build.boards.items())])


def load_model(payload):
    if payload['schema'] != 'acfqp.causal_symbolic_model.v66':
        raise ValueError('expected V66 symbolic dynamics')
    cells = {cell: Cell(layer, status, ()) for cell, layer, status in payload['cells']}
    rows = {(cell, action): tuple(Outcome(probability, target, reward)
             for probability, target, reward in outcomes) for cell, action, outcomes in payload['rows']}
    return CompiledModel(cells, rows, tuple(payload['roots']), {}, {})
