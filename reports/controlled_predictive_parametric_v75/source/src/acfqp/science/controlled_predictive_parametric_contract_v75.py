"""Guarded two-step templates with independently bound merge rewards.

Root variables are cell indices; (cell, offset) preserves future rank + 1
relations, (-1, rank) denotes a spawn constant, and None is an empty cell.
Compilation traces the frozen rewrite and records its observed comparisons.
Reuse validates those comparisons before binding the stored reward expressions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction


ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT")
PAIRS = tuple((cell, cell + delta) for cell in range(16) for delta in (1, 4)
              if (delta == 1 and cell % 4 < 3) or (delta == 4 and cell < 12))
NEIGHBORS = tuple(tuple(b if a == cell else a for a, b in PAIRS if a == cell or b == cell)
                  for cell in range(16))


def _cells(action, line):
    if action == "UP":
        return tuple(4 * row + line for row in range(4))
    if action == "DOWN":
        return tuple(4 * row + line for row in range(3, -1, -1))
    if action == "LEFT":
        return tuple(4 * line + column for column in range(4))
    return tuple(4 * line + column for column in range(3, -1, -1))


ACTION_CELLS = {action: tuple(_cells(action, line) for line in range(4)) for action in ACTION_ORDER}


def _value(expression, binding):
    variable, offset = expression
    return offset if variable < 0 else binding[variable] + offset


@dataclass(frozen=True)
class GuardedTemplate:
    zero_mask: int
    guards: tuple
    trace: tuple


class _Trace:
    def __init__(self, rule, binding, work):
        self.rule, self.binding, self.work = rule, binding, work
        self.guards, self.seen_guards = [], set()

    def _record(self, guard):
        self.work["compile_guard_requests"] += 1
        if guard not in self.seen_guards:
            self.seen_guards.add(guard)
            self.guards.append(guard)
            self.work["compiled_guards"] += 1

    def equal(self, left, right):
        self.work["compile_equality_tests"] += 1
        if left[0] == right[0]:
            return left[1] == right[1]
        result = _value(left, self.binding) == _value(right, self.binding)
        first, second = sorted((left, right))
        self._record(("EQ", first, second, result))
        return result

    def won(self, board):
        for expression in board:
            if expression is None:
                continue
            self.work["compile_goal_tests"] += 1
            result = _value(expression, self.binding) >= self.rule.goal_rank
            if expression[0] >= 0:
                self._record(("GE", expression, self.rule.goal_rank, result))
            if result:
                return True
        return False

    def adjacent(self, board):
        for left, right in PAIRS:
            self.work["compile_adjacency_tests"] += 1
            if board[left] is not None and board[right] is not None and self.equal(board[left], board[right]):
                return True
        return False

    def status(self, board):
        self.work["compile_status_calls"] += 1
        if self.won(board):
            return "WON"
        if not any(expression is not None for expression in board):
            return "LOST"
        if any(expression is None for expression in board) or self.adjacent(board):
            return "ACTIVE"
        return "LOST"

    def swipe(self, board, action):
        self.work["compile_symbolic_swipes"] += 1
        result, rewards, changed = list(board), [], False
        for cells in ACTION_CELLS[action]:
            self.work["compile_symbolic_line_rewrites"] += 1
            original = tuple(board[cell] for cell in cells)
            packed = tuple(expression for expression in original if expression is not None)
            output, position, merges = [], 0, 0
            while position < len(packed):
                expression = packed[position]
                if position + 1 < len(packed) and self.equal(expression, packed[position + 1]):
                    expression = expression[0], expression[1] + 1
                    rewards.append(expression)
                    merges += 1
                    position += 2
                else:
                    position += 1
                output.append(expression)
            output.extend([None] * (4 - len(output)))
            # Merging reduces occupied count; otherwise only packing can
            # change this line. Both facts depend solely on this traced path.
            changed |= bool(merges) or tuple(x is None for x in original) != tuple(x is None for x in output)
            for cell, expression in zip(cells, output):
                result[cell] = expression
        self.work["compile_symbolic_action_boards"] += 1
        return tuple(result), tuple(rewards), changed

    def terminal_mass(self, after):
        self.work["compile_terminal_mass_calls"] += 1
        holes = tuple(cell for cell, expression in enumerate(after) if expression is None)
        won = self.won(after)
        existing_pair = self.adjacent(after) if len(holes) == 1 and not won else False
        mass = {}
        for rank, probability in self.rule.spawn_distribution:
            if won or rank >= self.rule.goal_rank:
                status = "WON"
            elif len(holes) > 1 or existing_pair:
                status = "CUTOFF"
            elif any(self.equal((-1, rank), after[cell]) for cell in NEIGHBORS[holes[0]]):
                status = "CUTOFF"
            else:
                status = "LOST"
            mass[status] = mass.get(status, Fraction()) + probability
            self.work["compile_terminal_probability_combinations"] += 1
        return tuple(mass.items())

    def h1(self, board):
        self.work["compile_h1_descriptions"] += 1
        result = []
        for action in ACTION_ORDER:
            after, rewards, changed = self.swipe(board, action)
            if changed:
                result.append((action, rewards, self.terminal_mass(after)))
        return tuple(result)

    def compile(self, board):
        if self.status(board) != "ACTIVE":
            return ()
        result = []
        for action in ACTION_ORDER:
            after, rewards, changed = self.swipe(board, action)
            if not changed:
                continue
            holes = tuple(cell for cell, expression in enumerate(after) if expression is None)
            outcomes = []
            for cell in holes:
                for rank, probability in self.rule.spawn_distribution:
                    child = list(after)
                    child[cell] = (-1, rank)
                    child = tuple(child)
                    self.work["compile_h1_symbolic_boards"] += 1
                    self.work["compile_spawn_candidates"] += 1
                    status = self.status(child)
                    description = self.h1(child) if status == "ACTIVE" else None
                    outcomes.append((probability / len(holes), status, description))
            result.append((action, rewards, tuple(outcomes)))
        return tuple(result)


class ParametricCompiler:
    def __init__(self, rule, reuse=True):
        p = rule.program
        if (p.pack, p.merge_relation, p.rank_increment, p.consumption,
                p.reward_rule, rule.spawn_location) != (True, "equal", 1, "once", "output_value", "uniform"):
            raise ValueError("V75 guarded contracts require the frozen V69 rule")
        self.rule = rule
        self.reuse = reuse
        self.templates = {}
        self.work = Counter(compiled_programs=1, compile_h0_symbolic_boards=0)

    def _matches(self, template, binding):
        self.work["template_guard_trials"] += 1
        for kind, left, right, expected in template.guards:
            self.work["guard_checks"] += 1
            if kind == "EQ":
                actual = _value(left, binding) == _value(right, binding)
                self.work["guard_rank_reads"] += int(left[0] >= 0) + int(right[0] >= 0)
            else:
                actual = _value(left, binding) >= right
                self.work["guard_rank_reads"] += int(left[0] >= 0)
            if actual != expected:
                self.work["template_guard_rejections"] += 1
                return False
        return True

    def _score(self, expressions, binding):
        score = 0
        for expression in expressions:
            score += 1 << _value(expression, binding)
            self.work["bound_reward_terms"] += 1
        return score

    def _bind(self, template, binding):
        self.work["template_bind_calls"] += 1
        result = []
        for action, reward_terms, outcomes in template.trace:
            bound = []
            for probability, status, description in outcomes:
                if description is not None:
                    description = tuple((child_action, self._score(child_rewards, binding), terms)
                        for child_action, child_rewards, terms in description)
                    self.work["bound_h1_descriptions"] += 1
                bound.append((probability, status, description))
                self.work["bound_spawn_entries"] += 1
            result.append((action, self._score(reward_terms, binding), tuple(bound)))
        return tuple(result)

    def contract(self, board):
        binding = tuple(board)
        self.work["contract_calls"] += 1
        self.work["zero_mask_rank_reads"] += 16
        zero_mask = sum(1 << cell for cell, rank in enumerate(binding) if not rank)
        if self.reuse:
            bank = self.templates.setdefault(zero_mask, [])
            for template in bank:
                if self._matches(template, binding):
                    self.work["template_hits"] += 1
                    return self._bind(template, binding)
            self.work["template_misses"] += 1
        symbolic = tuple((cell, 0) if rank else None for cell, rank in enumerate(binding))
        trace = _Trace(self.rule, binding, self.work)
        description = trace.compile(symbolic)
        template = GuardedTemplate(zero_mask, tuple(trace.guards), description)
        if self.reuse:
            bank.append(template)
        self.work["template_compilations"] += 1
        return self._bind(template, binding)
