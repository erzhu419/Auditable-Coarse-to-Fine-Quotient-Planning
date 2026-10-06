"""Fixed-policy consequence estimates from the supplied learned dynamics only.

The implementation reproduces V77's afterstate target: an initial spawn, at
most horizon continuation actions, and terminal classification after every
spawn including the last. It neither trains nor queries the environment.
"""
from collections import Counter
import ctypes
from itertools import product
import os
from pathlib import Path
import random
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_lifelong_planner_v77 import POLICIES, SNAKE_CELLS
from .controlled_predictive_relational_dynamics_v69 import ACTION_ORDER, _cells

CALL_SEED_STRIDE = 1_000_000_000_000
_LIBRARIES, _TABLES = {}, {}
_COUNT_NAMES = ('model_spawn_samples', 'rollout_actions', 'learned_terminal_checks',
                'learned_swipe_calls', 'learned_line_rewrites', 'legal_swipes')


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    project = Path(__file__).resolve().parents[3]
    if not build_dir.is_relative_to(project):
        raise ValueError('V119 build_dir must be inside the research worktree')
    key = (str(build_dir), os.getpid())
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_name('controlled_predictive_rollout_kernel_v119.cpp')
        library_path = build_dir / f'rollout_kernel_v119_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC',
            '-ffp-contract=off', str(source), '-o', str(library_path)],
            check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts['cpp_compilations'] += 1
        library = ctypes.CDLL(str(library_path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci = ctypes.c_int
        library.rollout_v119.argtypes = [ip, ci, ci, ci, ci, ip, lp, ip,
            ip, dp, ci, ip, dp, ci, dp, dp, up]
        library.rollout_v119.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _tables(rule, counts):
    key = (rule.program, rule.goal_rank)
    if key not in _TABLES:
        rows = [rule.program.line(line) for line in product(range(rule.goal_rank), repeat=4)]
        counts['lookup_line_rewrites'] += len(rows)
        _TABLES[key] = (np.asarray([row[0] for row in rows], dtype=np.int32),
                       np.asarray([row[1] for row in rows], dtype=np.int64))
    else:
        counts['lookup_table_cache_hits'] += 1
    return _TABLES[key]


class RolloutKnowledge:
    """V77 knowledge contract, using common draws across leaves and policies."""

    def __init__(self, rule, replicas, seed, build_dir):
        if replicas <= 0:
            raise ValueError('replicas must be positive')
        self.rule, self.replicas, self.seed = rule, int(replicas), int(seed)
        self.counts, self.setup_counts = Counter(), Counter()
        self.call_index = 0
        started = perf_counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.table, self.scores = _tables(rule, self.setup_counts)
        self.cells = np.asarray([[_cells(action, line) for line in range(4)]
            for action in sorted(ACTION_ORDER)], dtype=np.int32)
        self.snake = np.asarray(SNAKE_CELLS, dtype=np.int32)
        self.weights = np.asarray([0.8 ** pos for pos in range(16)], dtype=np.float64)
        self.location = {'uniform': 0, 'first': 1, 'last': 2}[rule.spawn_location]
        self.spawn_ranks = np.asarray([rank for rank, _ in rule.spawn_distribution], dtype=np.int32)
        # The same float conversion and left-to-right accumulation as V77._spawn.
        cumulative, total = [], 0.0
        for _, probability in rule.spawn_distribution:
            total += float(probability)
            cumulative.append(total)
        self.cumulative = np.asarray(cumulative, dtype=np.float64)
        self.setup_seconds = perf_counter() - started

    def common_draws(self, horizon):
        """Next call's draws without advancing its index; MC budgets share prefixes."""
        rng = random.Random(self.seed + self.call_index * CALL_SEED_STRIDE)
        return np.asarray([rng.random() for _ in range(self.replicas * (horizon+1) * 2)],
            dtype=np.float64).reshape((self.replicas, horizon+1, 2))

    def predict_many(self, boards, horizon):
        boards = np.asarray(list(boards), dtype=np.int32).reshape((-1, 16))
        if horizon < 0 or np.any(boards < 0):
            raise ValueError('horizon and board ranks must be nonnegative')
        draws = self.common_draws(horizon)
        self.call_index += 1
        self.counts['predict_many_calls'] += 1
        self.counts['prediction_boards'] += len(boards)
        self.counts['policy_prediction_rows'] += len(boards) * len(POLICIES)
        self.counts['policy_vector_rollouts'] += len(boards) * len(POLICIES) * self.replicas
        self.counts['model_uniform_draws'] += draws.size
        output = np.empty((len(boards), len(POLICIES), 3), dtype=np.float64)
        counts = np.zeros(len(_COUNT_NAMES), dtype=np.uint64)
        status = self.library.rollout_v119(boards, len(boards), int(horizon), self.replicas,
            self.rule.goal_rank, self.table, self.scores, self.cells, self.snake, self.weights,
            self.location, self.spawn_ranks, self.cumulative, len(self.spawn_ranks),
            draws, output, counts)
        self.counts.update({name: int(value) for name, value in zip(_COUNT_NAMES, counts)})
        if status:
            raise ValueError('rollout afterstate has no spawn vacancy')
        return output
