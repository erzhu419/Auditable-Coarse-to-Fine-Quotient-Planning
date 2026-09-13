"""Group local H1 predicates before probability-contract materialization.

Four-row contexts retain complete geometry. They avoid flattened child boards,
but are not semantic state abstraction; candidate predicates are still evaluated
one by one. Only equal action/reward/terminal predicates share a contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys


def _local_module():
    name = "acfqp_v73_local_base"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name,
            Path(__file__).with_name("controlled_predictive_local_contract_v72.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


_local = _local_module()
ACTION_ORDER = _local.ACTION_ORDER


@dataclass(frozen=True)
class BlockContext:
    rows: tuple[tuple[int, ...], ...]
    inputs: tuple
    summaries: tuple
    maximum: int
    empty_cells: tuple[int, ...]
    existing_pair: bool
    hole_neighbors: tuple[int, ...]


class GroupedCompiler(_local.LocalCompiler):
    def __init__(self, rule):
        super().__init__(rule)
        self.contract_cache = {}
        self.work.update(factorized_contexts=0, candidate_predicate_evaluations=0,
                         contract_materializations=0)

    def _context(self, rows, inputs=None, summaries=None):
        if inputs is None:
            columns = tuple(tuple(rows[row][column] for row in range(4)) for column in range(4))
            inputs = (columns, tuple(line[::-1] for line in columns),
                      rows, tuple(line[::-1] for line in rows))
        if summaries is None:
            summaries = tuple(tuple(self._line(line) for line in action_inputs)
                              for action_inputs in inputs)
        maximum = max(max(row) for row in rows)
        empty = tuple(4 * row + column for row in range(4) for column in range(4)
                      if not rows[row][column])
        existing_pair, neighbors = False, ()
        if len(empty) <= 1 and maximum < self.rule.goal_rank:
            for row in range(4):
                for column in range(4):
                    for next_row, next_column in ((row, column + 1), (row + 1, column)):
                        if next_row == 4 or next_column == 4:
                            continue
                        self.work["base_adjacent_tests"] += 1
                        rank = rows[row][column]
                        if rank and rank == rows[next_row][next_column]:
                            existing_pair = True
                            break
                    if existing_pair:
                        break
                if existing_pair:
                    break
            if len(empty) == 1 and not existing_pair:
                row, column = divmod(empty[0], 4)
                neighbors = tuple(rows[r][c] for r, c in
                    ((row - 1, column), (row + 1, column),
                     (row, column - 1), (row, column + 1))
                    if 0 <= r < 4 and 0 <= c < 4)
                self.work["base_hole_neighbor_reads"] += len(neighbors)
        context = BlockContext(rows, inputs, summaries, maximum, empty, existing_pair, neighbors)
        self.work["factorized_contexts"] += 1
        return context

    def prepare(self, board):
        self.work["prepare_calls"] += 1
        return self._context(tuple(tuple(board[4 * row:4 * row + 4]) for row in range(4)))

    def status(self, context):
        self.work["context_status_evaluations"] += 1
        if context.maximum >= self.rule.goal_rank:
            return "WON"
        if context.empty_cells or context.existing_pair:
            return "ACTIVE"
        return "LOST"

    def _patched_views(self, context, cell, rank):
        inputs, summaries = [], []
        for action_index in range(4):
            line, position = _local._PATCH_POSITION[action_index][cell]
            old_input = context.inputs[action_index][line]
            patched_input = old_input[:position] + (rank,) + old_input[position + 1:]
            replacement = self._line(patched_input)
            action_inputs = context.inputs[action_index]
            action_summaries = context.summaries[action_index]
            inputs.append(action_inputs[:line] + (patched_input,) + action_inputs[line + 1:])
            summaries.append(action_summaries[:line] + (replacement,) + action_summaries[line + 1:])
            self.work["patched_line_inputs"] += 1
            self.work["unaffected_line_summaries_reused"] += 3
        return tuple(inputs), tuple(summaries)

    def patched_context(self, context, cell, rank):
        self.work["patched_context_requests"] += 1
        row, column = divmod(cell, 4)
        old = context.rows[row]
        changed = old[:column] + (rank,) + old[column + 1:]
        rows = context.rows[:row] + (changed,) + context.rows[row + 1:]
        inputs, summaries = self._patched_views(context, cell, rank)
        return self._context(rows, inputs, summaries)

    def actions(self, context):
        self.work["factorized_action_expansions"] += 1
        if context.maximum >= self.rule.goal_rank:
            return
        for action_index, action in enumerate(ACTION_ORDER):
            summaries = context.summaries[action_index]
            self.work["action_changed_tests"] += 1
            if not any(line.changed for line in summaries):
                continue
            output = tuple(line.output for line in summaries)
            if action == "UP":
                rows = tuple(tuple(output[column][row] for column in range(4)) for row in range(4))
            elif action == "DOWN":
                rows = tuple(tuple(output[column][3 - row] for column in range(4)) for row in range(4))
            elif action == "LEFT":
                rows = output
            else:
                rows = tuple(line[::-1] for line in output)
            self.work["factorized_action_afterstates"] += 1
            yield action, sum(line.score for line in summaries), self._context(rows)

    def _terminal_vector(self, summaries, guaranteed_vacancies=False):
        """Classify spawn ranks without creating Fraction probability masses."""
        self.work["terminal_predicate_evaluations"] += 1
        won = max(line.maximum for line in summaries) >= self.rule.goal_rank
        if guaranteed_vacancies:
            # Patching a base with >=3 vacancies leaves >=2. A legal pack /
            # equal-merge action cannot increase the number of occupied cells.
            empty_count = 2
            self.work["vacancy_family_shortcuts"] += 1
        else:
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
                neighbors = tuple(summaries[r].output[c] for r, c in
                    ((line - 1, position), (line + 1, position),
                     (line, position - 1), (line, position + 1))
                    if 0 <= r < 4 and 0 <= c < 4)
                self.work["hole_neighbor_rank_reads"] += len(neighbors)
        vector = []
        for rank, _ in self.rule.spawn_distribution:
            self.work["terminal_spawn_rank_classifications"] += 1
            if won or rank >= self.rule.goal_rank:
                vector.append("WON")
            elif empty_count > 1 or existing_pair or rank in neighbors:
                vector.append("CUTOFF")
            else:
                vector.append("LOST")
        return tuple(vector)

    def _predicate_key(self, summaries, guaranteed_vacancies=False):
        self.work["predicate_calls"] += 1
        result = []
        for action, lines in zip(ACTION_ORDER, summaries):
            self.work["candidate_action_changed_tests"] += 1
            if any(line.changed for line in lines):
                self.work["candidate_action_predicate_evaluations"] += 1
                result.append((action, sum(line.score for line in lines),
                               self._terminal_vector(lines, guaranteed_vacancies)))
        self.work["predicate_materializations"] += 1
        return tuple(result)

    def _materialize(self, key, use_cache=True):
        if use_cache:
            self.work["contract_cache_lookups"] += 1
        if use_cache and key in self.contract_cache:
            self.work["contract_cache_hits"] += 1
            return self.contract_cache[key]
        result = []
        for action, score, vector in key:
            mass = {}
            for status, (_, probability) in zip(vector, self.rule.spawn_distribution):
                mass[status] = mass.get(status, Fraction()) + probability
                self.work["contract_fraction_accumulations"] += 1
                self.work["terminal_probability_combinations"] += 1
            result.append((action, score, tuple(mass.items())))
        contract = tuple(result)
        if use_cache:
            self.contract_cache[key] = contract
        self.work["contract_materializations"] += 1
        return contract

    def spawn_groups(self, context, grouping=True):
        """Return first-occurrence ordered masses and H1 contracts.

        Each tuple is (mass, status, contract_or_None, first_descriptor, count).
        All descriptors are evaluated before equal predicates share a contract.
        """
        self.work["spawn_group_requests"] += 1
        groups, individual = {}, []
        for cell in context.empty_cells:
            for rank, probability in self.rule.spawn_distribution:
                self.work["spawn_candidates"] += 1
                status = self.patch_status(context, cell, rank)
                if status == "ACTIVE":
                    self.work["candidate_predicate_evaluations"] += 1
                    _, summaries = self._patched_views(context, cell, rank)
                    predicate = self._predicate_key(summaries, len(context.empty_cells) >= 3)
                else:
                    predicate = None
                incoming_mass = probability / len(context.empty_cells)
                self.work["incoming_probability_evaluations"] += 1
                if not grouping:
                    contract = self._materialize(predicate, use_cache=False) if status == "ACTIVE" else None
                    individual.append((incoming_mass, status, contract, (cell, rank), 1))
                    continue
                key = status, predicate
                if key not in groups:
                    groups[key] = [Fraction(), (cell, rank), 0]
                groups[key][0] += incoming_mass
                self.work["incoming_group_probability_additions"] += 1
                groups[key][2] += 1
        if not grouping:
            self.work["spawn_groups"] += len(individual)
            return tuple(individual)
        result = tuple((mass, status, self._materialize(key) if status == "ACTIVE" else None,
                        representative, count)
                       for (status, key), (mass, representative, count) in groups.items())
        self.work["spawn_groups"] += len(result)
        return result

    def context_contract(self, context):
        self.work["context_contract_evaluations"] += 1
        if context.maximum >= self.rule.goal_rank:
            return ()
        return self._materialize(self._predicate_key(context.summaries))

    def observation_contract(self, board):
        self.work["direct_observation_evaluations"] += 1
        return self.context_contract(self.prepare(board))
