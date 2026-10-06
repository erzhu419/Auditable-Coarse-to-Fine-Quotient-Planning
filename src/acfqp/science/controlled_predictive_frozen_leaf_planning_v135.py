"""One learned-model expectimax step around a frozen, unchanged TD leaf."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_contextual_ntuple_v134 import COUNT_NAMES as LEAF_COUNT_NAMES
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .controlled_predictive_paired_ntuple_v130 import _delta, _same_query

SCHEMA = 'acfqp.frozen_leaf_planning.v135'
COUNT_NAMES = LEAF_COUNT_NAMES+('root_swipe_calls', 'root_legal_actions', 'root_goal_actions',
    'leaf_choose_calls', 'second_ply_swipe_calls', 'generated_spawn_outcomes',
    'spawn_rank1_outcomes', 'spawn_rank2_outcomes', 'expanded_postspawn_states',
    'leaf_terminal_loss_states', 'leaf_terminal_goal_states',
    'expectimax_probability_products', 'expectimax_probability_sums')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V135 build_dir must be inside the research worktree')
    key = (str(build_dir), os.getpid())
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'frozen_leaf_planning_v135_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=3)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.frozen_leaf_choose_v135.argtypes = [ip, ip, ip, ci, ci, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, cd, cd, ci, ip, lp, dp, dp, ip, up]
        library.frozen_leaf_choose_v135.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class FrozenLeafPlanner:
    def __init__(self, model, depth=2, build_dir=None):
        if depth not in (1, 2):
            raise ValueError('V135 compares DIRECT depth 1 and H2 depth 2')
        if model.weights.flags.writeable:
            raise ValueError('the V135 leaf model must already be frozen')
        distribution = dict(model.rule.spawn_distribution)
        if model.rule.spawn_location != 'uniform' or set(distribution) != {1, 2}:
            raise ValueError('V135 uses the frozen uniform-cell rank-one/rank-two spawn law')
        started = perf_counter()
        self.model, self.depth = model, depth
        self.rule, self.radix = model.rule, model.radix
        self.target_query, self.source_query = model.target_query, model.source_query
        self.spawn_probabilities = tuple(float(distribution[rank]) for rank in (1, 2))
        self.counts, self.setup_counts = Counter(), Counter()
        self.library = _backend(build_dir, self.setup_counts) if depth == 2 else None
        self.extra_cells = getattr(model.model, 'extra_cells', np.zeros((4, 8), dtype=np.int32))
        self.mode = getattr(model.model, 'mode', -1)
        self.convert = int(model.kind == 'PRIOR' and not _same_query(model.source_query, model.target_query))
        self.setup_seconds = perf_counter()-started

    @property
    def weights(self):
        return self.model.weights

    @property
    def updates(self):
        return self.model.updates

    def freeze(self):
        self.model.freeze()

    def choose(self, board, query=None):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the frozen planner target query is fixed')
        before = self.counts.copy()
        self.counts['choose_calls'] += 1
        if self.depth == 1:
            model_before = self.model.counts.copy()
            choice = self.model.choose(board, query)
            work = _delta(self.model.counts, model_before)
            self.counts.update({key: work.get(f'inner_{key}', 0)
                for key in LEAF_COUNT_NAMES if work.get(f'inner_{key}', 0)})
            self.counts.update(root_swipe_calls=work.get('inner_learned_swipe_calls', 0),
                root_legal_actions=len(choice['action_values']),
                root_goal_actions=sum(max(row['afterstate']) >= self.radix
                    for row in choice['action_values'].values()))
            return choice
        board = self.model.model._board(board, terminal_allowed=True)
        moved = np.empty((4, 16), dtype=np.int32)
        scores = np.zeros(4, dtype=np.int64)
        tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        raw_query = self.source_query if self.model.kind == 'PRIOR' else self.target_query
        goal, failure = (float(self.target_query.get(key, 0.)) for key in ('goal_bonus', 'failure_penalty'))
        native = self.model.model
        best = self.library.frozen_leaf_choose_v135(board, native.patterns, self.extra_cells,
            self.radix, self.mode, self.weights, native.table, native.scores, native.cells,
            float(raw_query.get('goal_bonus', 0.)), goal, failure, self.model.failure_shift,
            self.model.success_shift, *self.spawn_probabilities, self.convert,
            moved, scores, tails, values, legal, counts)
        self.counts.update({key: int(value) for key, value in zip(COUNT_NAMES, counts) if value})
        if best < 0:
            status, value = ('WON', goal) if best == -2 else ('LOST', -failure)
            return dict(action=None, afterstate=board.tolist(), score=0, value=value,
                tail_value=value, action_values={}, status=status, counts=_delta(self.counts, before))
        action_values = {action: dict(afterstate=moved[index].tolist(), score=int(scores[index]),
            tail_value=float(tails[index]), value=float(values[index]))
            for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=_delta(self.counts, before))
