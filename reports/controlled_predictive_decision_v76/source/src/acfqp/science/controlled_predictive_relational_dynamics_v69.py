"""Identify a compositional line-rewrite program from source observations.

The DSL supplies line topology, rank arithmetic, and one empty-cell spawn.
Source labels select the rewrite and reward parameters and the spawn law.
Inference uses only the selected program: no source-state dictionary or domain
kernel is retained, and unknown target combinations need no new class IDs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from itertools import product
from time import perf_counter


ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT")


def _cells(action, line):
    if action == "UP":
        return tuple(4 * r + line for r in range(4))
    if action == "DOWN":
        return tuple(4 * r + line for r in range(3, -1, -1))
    if action == "LEFT":
        return tuple(4 * line + c for c in range(4))
    if action == "RIGHT":
        return tuple(4 * line + c for c in range(3, -1, -1))
    raise ValueError(f"unknown action {action}")


@dataclass(frozen=True)
class RewriteProgram:
    pack: bool
    merge_relation: str
    rank_increment: int
    consumption: str
    reward_rule: str

    def _merges(self, left, right):
        return (left > 0 and right > 0 and
                (self.merge_relation == "any" or
                 (self.merge_relation == "equal" and left == right)))

    def _merge(self, left, right):
        rank = max(left, right) + self.rank_increment
        reward = {"zero": 0, "count": 1, "left_value": 1 << left,
                  "output_value": 1 << rank}[self.reward_rule]
        return rank, reward

    def line(self, line):
        values = [r for r in line if r] if self.pack else list(line)
        output, score = [], 0
        if self.consumption == "once":
            index = 0
            while index < len(values):
                rank = values[index]
                if index + 1 < len(values) and self._merges(rank, values[index + 1]):
                    rank, reward = self._merge(rank, values[index + 1])
                    score += reward
                    index += 2
                else:
                    index += 1
                output.append(rank)
        else:
            for rank in values:
                while output and self._merges(output[-1], rank):
                    rank, reward = self._merge(output.pop(), rank)
                    score += reward
                output.append(rank)
        return tuple(output + [0] * (4 - len(output))), score

    def swipe(self, board, action, work=None):
        if work is not None:
            work["learned_swipe_calls"] += 1
            work["learned_line_rewrites"] += 4
        result, score = list(board), 0
        for line in range(4):
            cells = _cells(action, line)
            rewritten, gained = self.line(tuple(board[cell] for cell in cells))
            score += gained
            for cell, rank in zip(cells, rewritten):
                result[cell] = rank
        moved = tuple(result)
        return moved, score, moved != tuple(board)


@dataclass(frozen=True)
class LearnedDynamics:
    program: RewriteProgram
    spawn_distribution: tuple[tuple[int, Fraction], ...]
    spawn_location: str
    goal_rank: int = 11
    fit_counts: dict = field(default_factory=dict)
    fit_seconds: float = 0.0

    def swipe(self, board, action, work=None):
        return self.program.swipe(tuple(board), action, work)

    def classify(self, board, work=None):
        if work is not None:
            work["learned_terminal_checks"] += 1
        if max(board) >= self.goal_rank:
            return "WON", ()
        moves = []
        for action in ACTION_ORDER:
            moved, score, changed = self.swipe(board, action, work)
            if changed:
                moves.append((action, moved, score))
        return ("ACTIVE", tuple(moves)) if moves else ("LOST", ())

    def successors_from_afterstate(self, moved, score, work=None):
        empties = [cell for cell, rank in enumerate(moved) if rank == 0]
        if not empties:
            raise ValueError("a legal observed rewrite must leave a spawn vacancy")
        if self.spawn_location == "first":
            cells = empties[:1]
        elif self.spawn_location == "last":
            cells = empties[-1:]
        else:
            cells = empties
        reward = Fraction(score, 2048)
        outcomes = []
        for cell in cells:
            for rank, probability in self.spawn_distribution:
                successor = list(moved)
                successor[cell] = rank
                outcomes.append((probability / len(cells), tuple(successor), reward))
                if work is not None:
                    work["learned_spawn_outcomes"] += 1
        return tuple(outcomes)

    def to_payload(self):
        return dict(schema="controlled_predictive_relational_dynamics_v69",
                    program=asdict(self.program), spawn_location=self.spawn_location,
                    spawn_distribution=[[rank, p.numerator, p.denominator]
                                        for rank, p in self.spawn_distribution],
                    goal_rank=self.goal_rank, fit_counts=self.fit_counts,
                    fit_seconds=self.fit_seconds)

    @classmethod
    def from_payload(cls, payload):
        return cls(RewriteProgram(**payload["program"]),
                   tuple((rank, Fraction(n, d))
                         for rank, n, d in payload["spawn_distribution"]),
                   payload["spawn_location"], payload["goal_rank"],
                   payload.get("fit_counts", {}), payload.get("fit_seconds", 0.0))


class RuleIdentificationError(ValueError):
    def __init__(self, message, counts, survivors=()):
        super().__init__(message)
        self.counts = dict(counts)
        self.survivors = tuple(survivors)


def fit_rules(records):
    """Select the unique source-consistent program from the declared finite DSL.

    Probability labels are exact teacher support, not empirical sample counts.
    A failed or ambiguous fit raises RuleIdentificationError without consulting
    target states. All candidates are tested; none is privileged by ordering.
    """
    started = perf_counter()
    records = tuple(records)
    work = Counter(source_records=len(records))
    survivors = []
    for parameters in product((False, True), ("none", "equal", "any"),
                              (0, 1, 2), ("once", "cascade"),
                              ("zero", "count", "left_value", "output_value")):
        candidate = RewriteProgram(*parameters)
        work["rewrite_candidates"] += 1
        for row in records:
            work["candidate_observation_checks"] += 1
            predicted = candidate.swipe(row["board"], row["action"], work)
            observed = (tuple(row["afterstate"]), row["score"], row["changed"])
            if predicted != observed:
                break
        else:
            survivors.append(candidate)
    work["consistent_rewrite_candidates"] = len(survivors)
    if len(survivors) != 1:
        raise RuleIdentificationError(
            f"rewrite fit has {len(survivors)} consistent programs", work,
            tuple(asdict(program) for program in survivors))

    spawn_distribution = None
    spawn_rows = []
    for row in records:
        outcomes = row["outcomes"]
        if not row["changed"]:
            if outcomes:
                raise RuleIdentificationError("unchanged action has spawn outcomes", work)
            continue
        work["source_spawn_rows"] += 1
        moved = tuple(row["afterstate"])
        empty = tuple(cell for cell, rank in enumerate(moved) if rank == 0)
        joint, rank_mass = defaultdict(Fraction), defaultdict(Fraction)
        for item in outcomes:
            work["source_spawn_outcomes"] += 1
            cell, rank = item["spawned_cell"], item["spawned_rank"]
            p = Fraction(*item["probability"])
            successor = list(moved)
            if cell not in empty or rank <= 0 or p <= 0:
                raise RuleIdentificationError("source spawn outside the declared grammar", work)
            successor[cell] = rank
            if tuple(successor) != tuple(item["board"]) or item["score"] != row["score"]:
                raise RuleIdentificationError("source spawn changes more than one empty cell", work)
            joint[cell, rank] += p
            rank_mass[rank] += p
        if sum(rank_mass.values(), Fraction()) != 1:
            raise RuleIdentificationError("source spawn row is not a complete probability law", work)
        current = tuple(sorted(rank_mass.items()))
        if spawn_distribution is None:
            spawn_distribution = current
        elif current != spawn_distribution:
            raise RuleIdentificationError("spawn rank law depends on the source state", work)
        spawn_rows.append((empty, dict(joint)))
    if not spawn_rows:
        raise RuleIdentificationError("source observations do not identify spawning", work)

    locations = []
    for mode in ("uniform", "first", "last"):
        work["spawn_location_candidates"] += 1
        for empty, actual in spawn_rows:
            work["spawn_location_observation_checks"] += 1
            cells = empty if mode == "uniform" else empty[:1] if mode == "first" else empty[-1:]
            expected = {(cell, rank): p / len(cells)
                        for cell in cells for rank, p in spawn_distribution}
            if expected != actual:
                break
        else:
            locations.append(mode)
    work["consistent_spawn_location_candidates"] = len(locations)
    if len(locations) != 1:
        raise RuleIdentificationError(f"spawn fit has {len(locations)} consistent locations", work,
                                      locations)
    return LearnedDynamics(survivors[0], spawn_distribution, locations[0],
                           fit_counts=dict(work), fit_seconds=perf_counter() - started)
