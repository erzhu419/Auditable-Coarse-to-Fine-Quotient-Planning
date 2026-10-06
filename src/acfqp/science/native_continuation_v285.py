"""Compact full-game continuations under a frozen H2 policy and supplied law."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as PLANNING_COUNTS
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .controlled_predictive_paired_ntuple_v130 import _same_query

ENVIRONMENT_COUNTS = ('sampled_transitions', 'environment_random_draws',
    'ground_explicit_swipe_calls', 'ground_swipe_calls', 'ground_state_status_calls',
    'ground_status_internal_swipe_calls')
ROLLOUT_COUNTS = ('completed_rollouts', 'rng_streams_started', 'continuation_choose_calls')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V285 builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'native_continuation_v285_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.native_continuation_v285.argtypes = [ip, ip, ci, up, ci, ci, ip, ip,
            ci, ci, dp, ip, lp, ip, cd, cd, cd, cd, cd, cd, cd, ci, lp, ip, up, up, up]
        library.native_continuation_v285.restype = ci
        library.native_common_draws_v285.argtypes = [ctypes.c_uint64, ci, dp]
        library.native_common_draws_v285.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class NativeContinuation:
    """Each action shares a replica's std::mt19937_64 cell/rank stream.

    These are new diagnostic streams, independent of V281's Python RNG. The
    caller supplies distinct replica seeds for its two independent batches.
    """
    def __init__(self, leaf, build_dir):
        if leaf.weights.flags.writeable:
            raise ValueError('V285 requires the unchanged frozen value leaf')
        started = perf_counter()
        self.leaf, self.setup_counts = leaf, Counter()
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'rollout')}
        self.library = _backend(build_dir, self.setup_counts)
        self.extra = getattr(leaf.model, 'extra_cells', np.zeros((4, 8), dtype=np.int32))
        self.mode = getattr(leaf.model, 'mode', -1)
        self.convert = int(leaf.kind == 'PRIOR' and not _same_query(leaf.source_query, leaf.target_query))
        self.setup_seconds = perf_counter()-started

    def common_draws(self, seed, n_steps):
        """Reproduce a compact receipt's stream without executing an environment."""
        draws = np.empty((n_steps, 2), dtype=np.float64)
        self.library.native_common_draws_v285(int(seed), n_steps, draws)
        return draws

    def evaluate(self, board, actions, p_four, replica_seeds, max_steps=8192,
                 environment_p_four=None):
        """Use p_four for planning; generate tiles with environment_p_four.

        Omitting the environment probability keeps the existing known-law call.
        """
        started, cpu_started = perf_counter(), process_time()
        environment_p_four=p_four if environment_p_four is None else environment_p_four
        leaf, native = self.leaf, self.leaf.model
        board = native._board(board, terminal_allowed=False)
        actions, seeds = list(actions), np.asarray(replica_seeds, dtype=np.uint64)
        encoded = np.asarray([ACTIONS.index(action) for action in actions], dtype=np.int32)
        n = len(actions)*len(seeds)
        metrics, final = np.empty((n, 4), dtype=np.int64), np.empty((n, 16), dtype=np.int32)
        environment = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64)
        planning = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
        rollout = np.zeros(len(ROLLOUT_COUNTS), dtype=np.uint64)
        raw_query = leaf.source_query if leaf.kind == 'PRIOR' else leaf.target_query
        goal, failure = (float(leaf.target_query.get(key, 0.)) for key in ('goal_bonus', 'failure_penalty'))
        status = self.library.native_continuation_v285(board, encoded, len(actions), seeds,
            len(seeds), max_steps, native.patterns, self.extra, leaf.radix, self.mode,
            leaf.weights, native.table, native.scores, native.cells,
            float(raw_query.get('goal_bonus', 0.)), goal, failure,
            leaf.failure_shift, leaf.success_shift, p_four, environment_p_four, self.convert,
            metrics, final, environment, planning, rollout)
        if status:
            raise ValueError('forced or continuation action is illegal in the actual standard environment')
        work = {kind: {name: int(value) for name, value in zip(names, values) if value}
            for kind, names, values in (('environment', ENVIRONMENT_COUNTS, environment),
                ('planning', PLANNING_COUNTS, planning), ('rollout', ROLLOUT_COUNTS, rollout))}
        work['rollout'].update(evaluate_calls=1, replica_streams=len(seeds))
        for kind, counts in work.items():
            self.counts[kind].update(counts)
        rows = []
        for index, row in enumerate(metrics):
            action, replica = divmod(index, len(seeds))
            first_score, total_score, steps, terminal = map(int, row)
            bonus = goal if terminal == 1 else -failure if terminal == -1 else 0.
            rows.append(dict(action=actions[action], replica_index=replica, seed=int(seeds[replica]),
                first_score=first_score, total_score=total_score,
                suffix_utility=(total_score-first_score)/2048.+bonus,
                total_utility=total_score/2048.+bonus,
                status='WON' if terminal == 1 else 'LOST' if terminal == -1 else 'CUTOFF',
                steps=steps, final_board=final[index].tolist()))
        return dict(rollouts=rows, counts=work, seconds=perf_counter()-started,
            cpu_seconds=process_time()-cpu_started)
