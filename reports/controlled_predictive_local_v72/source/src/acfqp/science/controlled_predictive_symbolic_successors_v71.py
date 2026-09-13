"""Push the learned one-cell spawn law directly onto terminal contracts.

For the frozen pack/equal-merge program a nonempty board with a vacancy can
move. A full board can move exactly when an orthogonal pair has equal ranks.
The compiler uses these consequences without generating terminal boards or
calling a board dynamics kernel. Active successors retain concrete boards.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from time import perf_counter


_ADJACENT = tuple((cell, cell + offset)
                  for cell in range(16)
                  for offset in (1, 4)
                  if (offset == 1 and cell % 4 < 3) or
                     (offset == 4 and cell < 12))
_NEIGHBORS = tuple(tuple(b if a == cell else a for a, b in _ADJACENT
                         if a == cell or b == cell) for cell in range(16))


@dataclass(frozen=True)
class CompiledSuccessors:
    spawn_distribution: tuple[tuple[int, Fraction], ...]
    goal_rank: int
    compile_counts: dict
    elapsed_seconds: float

    def successors(self, moved, score, remaining_h, work=None):
        """Return (probability, status, active_board_or_None, reward) tuples.

        Terminal mass appears at that status's first original spawn position.
        ACTIVE entries retain the learned cell-major, rank-minor order; this
        also preserves depth-first contract IDs in the existing builder.
        """
        moved = tuple(moved)
        empty = tuple(cell for cell, rank in enumerate(moved) if rank == 0)
        if not empty:
            raise ValueError("a legal learned rewrite must leave a spawn vacancy")
        reward = Fraction(score, 2048)
        if work is None:
            work = Counter()
        work["symbolic_predicate_calls"] += 1
        # Vacancy scan and max each inspect the 16 input cells. Adjacency
        # predicates below are counted separately, not as total memory reads.
        work["symbolic_input_scan_cells"] += 32
        support_size = len(empty) * len(self.spawn_distribution)
        work["potential_spawn_outcomes"] += support_size

        won = max(moved) >= self.goal_rank
        existing_pair = False
        neighbors = ()
        if len(empty) == 1 and not won:
            for left, right in _ADJACENT:
                work["symbolic_adjacency_tests"] += 1
                if moved[left] and moved[left] == moved[right]:
                    existing_pair = True
                    break
            if not existing_pair:
                neighbors = tuple(moved[cell] for cell in _NEIGHBORS[empty[0]])

        classified, terminal_mass = [], {}
        for rank, probability in self.spawn_distribution:
            work["symbolic_spawn_rank_classifications"] += 1
            if won or rank >= self.goal_rank:
                status = "WON"
            elif len(empty) > 1 or existing_pair or rank in neighbors:
                status = "ACTIVE" if remaining_h > 0 else "CUTOFF"
            else:
                status = "LOST"
            classified.append((rank, probability, status))
            if status != "ACTIVE":
                terminal_mass[status] = terminal_mass.get(status, Fraction()) + probability
                work["symbolic_terminal_boards_avoided"] += len(empty)

        if all(status != "ACTIVE" for _, _, status in classified):
            result = tuple((p, status, None, reward) for status, p in terminal_mass.items())
        else:
            output, emitted = [], set()
            for cell in empty:
                for rank, probability, status in classified:
                    if status == "ACTIVE":
                        child = list(moved)
                        child[cell] = rank
                        output.append((probability / len(empty), status, tuple(child), reward))
                        work["symbolic_board_materializations"] += 1
                    elif status not in emitted:
                        output.append((terminal_mass[status], status, None, reward))
                        emitted.add(status)
            result = tuple(output)
        work["symbolic_terminal_mass_items"] += len(terminal_mass)
        work["symbolic_successor_entries"] += len(result)
        return result


def compile_rule(rule):
    """Compile the V69-selected program; no new observations or rule fitting."""
    started = perf_counter()
    program = rule.program
    selected = (program.pack, program.merge_relation, program.rank_increment,
                program.consumption, program.reward_rule, rule.spawn_location)
    if selected != (True, "equal", 1, "once", "output_value", "uniform"):
        raise ValueError("V71 symbolic terminal compiler requires the frozen V69 program")
    return CompiledSuccessors(tuple(rule.spawn_distribution), rule.goal_rank,
        dict(compiled_programs=1, compiled_spawn_ranks=len(rule.spawn_distribution),
             topology_edges=len(_ADJACENT)), perf_counter() - started)
