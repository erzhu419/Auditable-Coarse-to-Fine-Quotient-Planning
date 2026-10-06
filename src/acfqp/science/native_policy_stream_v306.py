"""Actual frozen LOCAL reward/risk H2 trajectories with exact raw-tile budgets."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as PLANNING_COUNTS
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .native_split_risk_v301 import REPRESENTATION_COUNTS
from .native_value_stream_v286 import ENVIRONMENT_COUNTS, _work

_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V306 native builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = build_dir/f'native_policy_stream_v306_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(output)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(output))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd, cp = ctypes.c_int, ctypes.c_double, ctypes.c_void_p
        library.native_policy_create_v306.argtypes = [ctypes.c_uint64]
        library.native_policy_create_v306.restype = cp
        library.native_policy_delete_v306.argtypes = [cp]
        library.native_policy_delete_v306.restype = None
        library.native_policy_state_v306.argtypes = [cp, ip, ip, lp]
        library.native_policy_state_v306.restype = None
        library.native_policy_advance_v306.argtypes = [cp, ip, ci, dp, dp, ip, lp, ip,
            cd, cd, ci, ci, lp, lp, dp, lp, ip, up, up, up, up]
        library.native_policy_advance_v306.restype = ci
        library.native_common_draws_v285.argtypes = [ctypes.c_uint64, ci, dp]
        library.native_common_draws_v285.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class NativePolicyStream:
    def __init__(self, leaf, seed, build_dir, max_steps=8192):
        if leaf.kind != 'LOCAL_RISK':
            raise ValueError('V306 collects the local reward/risk policy')
        if leaf.reward_weights.flags.writeable or leaf.risk_weights.flags.writeable:
            raise ValueError('V306 acquisition requires both actor heads frozen')
        started, cpu_started = perf_counter(), process_time()
        self.leaf, self.max_steps, self.setup_counts = leaf, max_steps, Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.handle = self.library.native_policy_create_v306(int(seed))
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.representation_counts = Counter()
        self.setup_seconds, self.setup_cpu_seconds = perf_counter()-started, process_time()-cpu_started

    def close(self):
        if self.handle:
            self.library.native_policy_delete_v306(self.handle)
            self.handle = None

    def __del__(self):
        if getattr(self, 'handle', None):
            self.close()

    def state(self):
        board, pending = np.empty(16, dtype=np.int32), np.empty(16, dtype=np.int32)
        info = np.empty(11, dtype=np.int64)
        self.library.native_policy_state_v306(self.handle, board, pending, info)
        episode, step, score, status, initial, has_pending, bank, raw, posts, start, seed = map(int, info)
        return dict(board=board.tolist(), pending_afterstate=pending.tolist() if has_pending else None,
            pending_bank_id=bank if has_pending else None, episode=episode, step=step,
            return_score=score, status={4:'NOT_STARTED', 3:'INITIALIZING', 0:'ACTIVE',
                1:'WON', -1:'LOST', 2:'CUTOFF'}[status], initial_count=initial,
            raw_tiles=raw, post_action_spawns=posts, game_start_raw=start,
            stream_seed=seed, random_draw_position=2*raw)

    def common_draws(self, seed, n_tiles):
        draws = np.empty((n_tiles, 2), dtype=np.float64)
        self.library.native_common_draws_v285(int(seed), n_tiles, draws)
        return draws

    def advance(self, model_p_four, environment_p_four, tile_budget):
        started, cpu_started = perf_counter(), process_time()
        before = self.state()
        raw = np.empty((tile_budget, 4), dtype=np.int64)
        actions = np.empty((tile_budget, 5), dtype=np.int64)
        values = np.empty(tile_budget, dtype=np.float64)
        games, lengths = np.empty((tile_budget+1, 6), dtype=np.int64), np.zeros(3, dtype=np.int32)
        environment = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64)
        planning = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
        representation = np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)
        stream_work = np.zeros(7, dtype=np.uint64)
        leaf = self.leaf
        code = self.library.native_policy_advance_v306(self.handle, leaf.model.patterns,
            leaf.radix, leaf.reward_weights, leaf.risk_weights, leaf.model.table,
            leaf.model.scores, leaf.model.cells, float(model_p_four), float(environment_p_four),
            int(tile_budget), int(self.max_steps), raw, actions, values, games, lengths,
            environment, planning, representation, stream_work)
        if code:
            raise ValueError('V306 full split H2 selected an illegal actual standard-world action')
        work = dict(environment=_work(ENVIRONMENT_COUNTS, environment),
            planning=_work(PLANNING_COUNTS, planning), learning={})
        for name, index in (('episodes_started',1), ('episodes_completed',2), ('won_games',3),
                ('lost_games',4), ('cutoff_games',5)):
            if stream_work[index]:
                work['environment'][name] = int(stream_work[index])
        if stream_work[0]:
            work['planning']['choose_calls'] = int(stream_work[0])
        for kind, counts in work.items():
            self.counts[kind].update(counts)
        representation_work = _work(REPRESENTATION_COUNTS, representation)
        self.representation_counts.update(representation_work)
        n_raw, n_actions, n_games = map(int, lengths)
        completed = [dict(episode=int(g[0]), stream_seed=before['stream_seed'],
            start_raw=int(g[1]), end_raw=int(g[2]), steps=int(g[3]), score=int(g[4]),
            status={1:'WON', -1:'LOST', 2:'CUTOFF'}[int(g[5])]) for g in games[:n_games]]
        return dict(start=before, end=self.state(),
            raw_spawns=[dict(episode=int(r[0]), kind='INITIAL' if r[1]==0 else 'POST_ACTION',
                cell=int(r[2]), rank=int(r[3])) for r in raw[:n_raw]],
            actions=[ACTIONS[int(a[2])] for a in actions[:n_actions]],
            scores=[int(a[3]) for a in actions[:n_actions]],
            action_records=[dict(episode=int(a[0]), step=int(a[1]), raw_index=int(a[4]),
                h2_value=float(v), next_afterstate_tail=None) for a,v in zip(actions[:n_actions],values[:n_actions])],
            updates=[], bank_learning={'0':{}}, completed_games=completed, counts=work,
            representation_counts=representation_work, seconds=perf_counter()-started,
            cpu_seconds=process_time()-cpu_started)
