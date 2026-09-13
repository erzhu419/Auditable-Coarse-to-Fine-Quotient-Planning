"""Evaluate an H1 action contract from a single-cell spawn patch.

Only the affected four-rank line is rewritten for each action. Unaffected
lines and learned rewrites are shared; no sixteen-rank child or action-result
board is assembled. This still evaluates every requested spawn candidate.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction


ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT")


def _cells(action, line):
    if action == "UP":
        return tuple(4 * row + line for row in range(4))
    if action == "DOWN":
        return tuple(4 * row + line for row in range(3, -1, -1))
    if action == "LEFT":
        return tuple(4 * line + column for column in range(4))
    return tuple(4 * line + column for column in range(3, -1, -1))


_ACTION_CELLS = tuple(tuple(_cells(action, line) for line in range(4))
                      for action in ACTION_ORDER)
_PATCH_POSITION = tuple(tuple(next((line, position)
    for line, cells in enumerate(action_cells)
    for position, candidate in enumerate(cells) if candidate == cell)
    for cell in range(16)) for action_cells in _ACTION_CELLS)


@dataclass(frozen=True)
class LineSummary:
    output: tuple[int, ...]
    score: int
    changed: bool
    maximum: int
    zeros: tuple[int, ...]
    equal_adjacent: bool


@dataclass(frozen=True)
class Context:
    base: tuple[int, ...]
    inputs: tuple[tuple[tuple[int, ...], ...], ...]
    summaries: tuple[tuple[LineSummary, ...], ...]
    maximum: int
    empty_cells: tuple[int, ...]
    existing_pair: bool
    hole_neighbors: tuple[int, ...]


class LocalCompiler:
    def __init__(self, rule):
        program = rule.program
        selected = (program.pack, program.merge_relation, program.rank_increment,
                    program.consumption, program.reward_rule, rule.spawn_location)
        if selected != (True, "equal", 1, "once", "output_value", "uniform"):
            raise ValueError("V72 requires the frozen V69 learned program")
        self.rule = rule
        self.work = Counter(compiled_programs=1, full_board_materializations=0)
        self.line_cache = {}

    def _line(self, inputs):
        self.work["line_lookups"] += 1
        if inputs in self.line_cache:
            self.work["line_cache_hits"] += 1
            return self.line_cache[inputs]
        output, score = self.rule.program.line(inputs)
        self.work["line_evaluations"] += 1
        equal_adjacent = False
        for position in range(3):
            self.work["line_summary_adjacent_tests"] += 1
            if output[position] > 0 and output[position] == output[position + 1]:
                equal_adjacent = True
                break
        summary = LineSummary(output, score, output != inputs, max(output),
            tuple(position for position, rank in enumerate(output) if not rank),
            equal_adjacent)
        self.line_cache[inputs] = summary
        return summary

    def prepare(self, base):
        """Prepare a supplied afterstate; cache contains four-rank lines only."""
        self.work["prepare_calls"] += 1
        base = tuple(base)
        inputs = tuple(tuple(tuple(base[cell] for cell in cells)
                             for cells in action_cells) for action_cells in _ACTION_CELLS)
        summaries = tuple(tuple(self._line(line) for line in action_inputs)
                          for action_inputs in inputs)
        empty_cells = tuple(cell for cell, rank in enumerate(base) if not rank)
        existing_pair, hole_neighbors = False, ()
        if len(empty_cells) == 1:
            for cell in range(16):
                for offset in (1, 4):
                    if (offset == 1 and cell % 4 == 3) or (offset == 4 and cell >= 12):
                        continue
                    self.work["base_adjacent_tests"] += 1
                    if base[cell] and base[cell] == base[cell + offset]:
                        existing_pair = True
                        break
                if existing_pair:
                    break
            if not existing_pair:
                hole = empty_cells[0]
                hole_neighbors = tuple(base[cell] for cell in
                    (hole - 4, hole + 4, hole - 1, hole + 1)
                    if 0 <= cell < 16 and
                       (abs(cell - hole) == 4 or cell // 4 == hole // 4))
                self.work["base_hole_neighbor_reads"] += len(hole_neighbors)
        return Context(base, inputs, summaries, max(base), empty_cells,
                       existing_pair, hole_neighbors)

    def patch_status(self, context, spawn_cell, spawn_rank):
        """Classify one supported spawn descriptor without assembling its board."""
        self.work["patch_status_evaluations"] += 1
        if max(context.maximum, spawn_rank) >= self.rule.goal_rank:
            return "WON"
        if len(context.empty_cells) > 1 or context.existing_pair or spawn_rank in context.hole_neighbors:
            return "ACTIVE"
        return "LOST"

    def _terminal_mass(self, summaries):
        self.work["terminal_contract_evaluations"] += 1
        won = max(line.maximum for line in summaries) >= self.rule.goal_rank
        empty_count = sum(len(line.zeros) for line in summaries)
        existing_pair, neighbors = False, ()
        if not won and empty_count == 1:
            existing_pair = any(line.equal_adjacent for line in summaries)
            if not existing_pair:
                for line in range(3):
                    for position in range(4):
                        self.work["cross_line_adjacent_tests"] += 1
                        rank = summaries[line].output[position]
                        if rank and rank == summaries[line + 1].output[position]:
                            existing_pair = True
                            break
                    if existing_pair:
                        break
            if not existing_pair:
                line, position = next((line, summary.zeros[0])
                    for line, summary in enumerate(summaries) if summary.zeros)
                neighbors = tuple(summaries[neighbor_line].output[neighbor_position]
                    for neighbor_line, neighbor_position in
                    ((line - 1, position), (line + 1, position),
                     (line, position - 1), (line, position + 1))
                    if 0 <= neighbor_line < 4 and 0 <= neighbor_position < 4)
                self.work["hole_neighbor_rank_reads"] += len(neighbors)
        mass = {}
        for rank, probability in self.rule.spawn_distribution:
            self.work["terminal_spawn_rank_classifications"] += 1
            if won or rank >= self.rule.goal_rank:
                status = "WON"
            elif empty_count > 1 or existing_pair or rank in neighbors:
                status = "CUTOFF"
            else:
                status = "LOST"
            mass[status] = mass.get(status, Fraction()) + probability
        return tuple(mass.items())

    def _actions(self, context, patch=None):
        if max(context.maximum, patch[1] if patch is not None else 0) >= self.rule.goal_rank:
            return ()
        result = []
        for action_index, action in enumerate(ACTION_ORDER):
            summaries = context.summaries[action_index]
            if patch is not None:
                line, position = _PATCH_POSITION[action_index][patch[0]]
                inputs = context.inputs[action_index][line]
                patched_inputs = inputs[:position] + (patch[1],) + inputs[position + 1:]
                replacement = self._line(patched_inputs)
                summaries = summaries[:line] + (replacement,) + summaries[line + 1:]
                self.work["patched_line_inputs"] += 1
                self.work["unaffected_line_summaries_reused"] += 3
            self.work["action_changed_tests"] += 1
            if not any(summary.changed for summary in summaries):
                continue
            self.work["action_contract_evaluations"] += 1
            result.append((action, sum(summary.score for summary in summaries),
                           self._terminal_mass(summaries)))
        return tuple(result)

    def contract(self, context, spawn_cell, spawn_rank):
        self.work["patched_contract_evaluations"] += 1
        return self._actions(context, (spawn_cell, spawn_rank))

    def observation_contract(self, board):
        self.work["direct_observation_evaluations"] += 1
        return self._actions(self.prepare(board))
