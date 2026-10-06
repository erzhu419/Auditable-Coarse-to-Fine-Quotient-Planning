"""V140 root samples followed directly by the unchanged maximizing H1 leaf."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_guarded_fragments_v138 import _validate_rule
from .controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from .controlled_predictive_paired_ntuple_v130 import _delta, _same_query
from .controlled_predictive_program_planning_v140 import COUNT_NAMES, encode_programs

SCHEMA = 'acfqp.shallow_sampling.v141'
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V141 build_dir must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'shallow_sampling_v141_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=2)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd, cu = ctypes.c_int, ctypes.c_double, ctypes.c_uint64
        library.shallow_choose_v141.argtypes = [ip, ip, ci, dp, ip, lp, ip, ip, ci,
            cd, cd, cd, cd, cd, cd, ci, cu, ip, lp, dp, dp, ip, ip, up]
        library.shallow_choose_v141.restype = ci
        library.shallow_first_spawn_v141.argtypes = [ip, cd, cu, ci, ci, ip, up]
        library.shallow_first_spawn_v141.restype = None
        library.program_h1_v140.argtypes = [ip, ip, ci, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, ci, up]
        library.program_h1_v140.restype = cd
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class ShallowSamplingPlanner:
    def __init__(self, model, factored_payload, build_dir=None):
        started = perf_counter()
        if model.weights.flags.writeable:
            raise ValueError('the V141 leaf model must already be frozen')
        if type(model.model) is not NtupleValue:
            raise ValueError('V141 uses the existing SINGLE QueryTD leaf')
        _validate_rule(model.rule)
        self.model, self.rule, self.radix = model, model.rule, model.radix
        self.source_query, self.target_query = model.source_query, model.target_query
        self.counts, self.setup_counts = Counter(), Counter()
        self.programs = encode_programs(factored_payload)
        self.library = _backend(build_dir, self.setup_counts)
        distribution = dict(model.rule.spawn_distribution)
        self.spawn_probabilities = tuple(float(distribution[rank]) for rank in (1, 2))
        self.convert = int(model.kind == 'PRIOR' and not _same_query(self.source_query, self.target_query))
        raw_query = self.source_query if model.kind == 'PRIOR' else self.target_query
        self.source_goal = float(raw_query.get('goal_bonus', 0.))
        self.goal = float(self.target_query.get('goal_bonus', 0.))
        self.failure = float(self.target_query.get('failure_penalty', 0.))
        self.setup_counts.update(copied_local_programs=len(self.programs),
            copied_program_integer_cells=self.programs.size, copied_program_bytes=self.programs.nbytes)
        self.setup_seconds = perf_counter()-started

    @property
    def weights(self):
        return self.model.weights

    @property
    def updates(self):
        return self.model.updates

    def freeze(self):
        self.model.freeze()

    def _charge(self, counts):
        self.counts.update({key: int(value) for key, value in zip(COUNT_NAMES, counts) if value})

    def _first_spawn(self, afterstate, action, replica, simulation_seed):
        """Finite probe of the same first-spawn helper used by choose."""
        board = self.model.model._board(afterstate, terminal_allowed=True)
        output, counts = np.empty(16, dtype=np.int32), np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        self.library.shallow_first_spawn_v141(board, self.spawn_probabilities[0],
            int(simulation_seed), ACTIONS.index(action), int(replica), output, counts)
        self._charge(counts)
        return output.tolist()

    def _h1(self, board):
        native = self.model.model
        board = native._board(board, terminal_allowed=True)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        value = self.library.program_h1_v140(board, native.patterns, self.radix, self.weights,
            native.table, native.scores, native.cells, self.source_goal, self.goal, self.failure,
            self.model.failure_shift, self.model.success_shift, self.convert, counts)
        self._charge(counts)
        return float(value)

    def choose(self, board, query=None, *, simulation_seed=0, previous_action='DOWN'):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the frozen planner target query is fixed')
        native = self.model.model
        board = native._board(board, terminal_allowed=True)
        before = self.counts.copy(); self.counts['choose_calls'] += 1
        moved, scores = np.empty((4, 16), dtype=np.int32), np.zeros(4, dtype=np.int64)
        tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
        stats, counts = np.zeros((4, 3), dtype=np.int32), np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        best = self.library.shallow_choose_v141(board, native.patterns, self.radix, self.weights,
            native.table, native.scores, native.cells, self.programs, len(self.programs),
            self.source_goal, self.goal, self.failure, self.model.failure_shift, self.model.success_shift,
            self.spawn_probabilities[0], self.convert, int(simulation_seed), moved, scores,
            tails, values, legal, stats, counts)
        self._charge(counts)
        if best == -3:
            raise ValueError('V139 local program coverage is incomplete; no transition fallback was used')
        work = _delta(self.counts, before)
        if best < 0:
            status, value = ('WON', self.goal) if best == -2 else ('LOST', -self.failure)
            return dict(action=None, afterstate=board.tolist(), score=0, value=value,
                tail_value=value, action_values={}, status=status, counts=work, value_kind='estimated_return')
        action_values = {action: dict(afterstate=moved[index].tolist(), score=int(scores[index]),
            tail_value=float(tails[index]), value=float(values[index]), budget=int(stats[index, 0]),
            used=int(stats[index, 1]), rollouts=int(stats[index, 2]))
            for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=work, value_kind='estimated_return')
