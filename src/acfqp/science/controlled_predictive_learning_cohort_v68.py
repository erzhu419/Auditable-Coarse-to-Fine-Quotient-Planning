"""Input-only V68 source/target declaration; no outcome-based board selection."""
from dataclasses import asdict
import random

from .controlled_predictive_cohort_v7 import cases_v7


def new_cases(split, count, seed_start):
    result = []
    edges = [(r * 4 + c, r * 4 + c + 1) for r in range(4) for c in range(3)]
    edges += [(r * 4 + c, (r + 1) * 4 + c) for r in range(3) for c in range(4)]
    for index in range(count):
        seed = seed_start + index
        rng = random.Random(seed)
        board = [rng.randint(1, 10) for _ in range(16)]
        left, right = edges[index % len(edges)]
        board[left] = board[right] = 1 + index % 10
        vacancies = index % 3
        for cell in rng.sample([i for i in range(16) if i not in (left, right)], vacancies):
            board[cell] = 0
        result.append(dict(name=f'v68_{split}_{index:02d}', board=board, horizon=3,
                           split=split, seed=seed, vacancies=vacancies,
                           forced_pair=[left, right], origin='declared_dense_generator'))
    return result


def roster():
    source = [dict(name=c.name, board=list(c.board), horizon=c.horizon,
                   split='source', origin='previously_exposed_v67') for c in cases_v7()]
    source += new_cases('source', 32, 680100)
    target = new_cases('target', 24, 680200)
    return dict(source=source, target=target)
