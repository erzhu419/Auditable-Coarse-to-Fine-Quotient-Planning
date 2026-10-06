"""Frozen actual LOCAL and LINEAR_WIN H2 batches and same-head DIRECT evaluation."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import resource
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as PLANNING_COUNTS
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .native_split_risk_v301 import REPRESENTATION_COUNTS as LOCAL_REPRESENTATION_COUNTS
from .native_linear_win_v311 import REPRESENTATION_COUNTS as LINEAR_REPRESENTATION_COUNTS
from .native_value_stream_v286 import ENVIRONMENT_COUNTS, _work

_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V313 native builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = build_dir/f'native_policy_stream_v313_{os.getpid()}.so'
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
        library.native_stream_create_v286.argtypes = [ctypes.c_uint64]
        library.native_stream_create_v286.restype = cp
        library.native_stream_delete_v286.argtypes = [cp]
        library.native_stream_delete_v286.restype = None
        library.native_stream_state_v286.argtypes = [cp, ip, ip, lp]
        library.native_stream_state_v286.restype = None
        library.native_policy_advance_v313.argtypes = [cp, cp, ci, ip, ci, dp, dp, ip, lp, ip,
            cd, cd, ci, ci, lp, lp, dp, ip, dp, ip, lp, ip, up, up, up, up]
        library.native_policy_advance_v313.restype = ci
        library.direct_choose_v313.argtypes = [cp, ci, ip, ip, ci, dp, dp, ip, lp, ip,
            ip, lp, dp, dp, ip, up, up]
        library.direct_choose_v313.restype = ci
        library.evaluate_direct_v313.argtypes = [up, ci, cp, ci, ip, ci, dp, dp, ip, lp, ip,
            cd, ci, lp, ip, up, up, up]
        library.evaluate_direct_v313.restype = ci
        library.native_common_draws_v285.argtypes = [ctypes.c_uint64, ci, dp]
        library.native_common_draws_v285.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _head(leaf):
    if leaf.kind == 'LOCAL_RISK':
        return (0, leaf.risk_weights, ctypes.cast(leaf.library.split_choose_v301, ctypes.c_void_p),
            ctypes.cast(leaf.library.split_predict_v301, ctypes.c_void_p), LOCAL_REPRESENTATION_COUNTS)
    if leaf.kind == 'LINEAR_WIN2':
        return (1, leaf.win_weights, ctypes.cast(leaf.library.linear_choose_v311, ctypes.c_void_p),
            ctypes.cast(leaf.library.linear_predict_v311, ctypes.c_void_p), LINEAR_REPRESENTATION_COUNTS)
    raise ValueError('V313 collects exactly LOCAL_RISK or LINEAR_WIN2 heads')


def _frozen(leaf, second):
    if leaf.reward_weights.flags.writeable or second.flags.writeable:
        raise ValueError('V313 acquisition/evaluation requires both actor heads frozen')


def _child_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


class NativePolicyStream:
    def __init__(self, leaf, seed, build_dir, max_steps=8192):
        self.kind, self.second_weights, self.choose_callback, self.predict_callback, self.representation_names = _head(leaf)
        _frozen(leaf, self.second_weights)
        self.actor_updates = leaf.updates
        started, cpu_started = perf_counter(), process_time()
        compiler_started = _child_cpu()
        self.leaf, self.max_steps, self.setup_counts = leaf, max_steps, Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.handle = self.library.native_stream_create_v286(int(seed))
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.representation_counts = Counter()
        self.setup_seconds, self.setup_cpu_seconds = perf_counter()-started, process_time()-cpu_started
        self.compiler_cpu_seconds = _child_cpu()-compiler_started

    def close(self):
        if self.handle:
            self.library.native_stream_delete_v286(self.handle)
            self.handle = None

    def __del__(self):
        if getattr(self, 'handle', None):
            self.close()

    def state(self):
        board, pending = np.empty(16, dtype=np.int32), np.empty(16, dtype=np.int32)
        info = np.empty(11, dtype=np.int64)
        self.library.native_stream_state_v286(self.handle, board, pending, info)
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
        _frozen(self.leaf, self.second_weights)
        if self.leaf.updates != self.actor_updates:
            raise ValueError('V313 actor changed between frozen batch chunks')
        before = self.state()
        raw = np.empty((tile_budget, 4), dtype=np.int64)
        actions = np.empty((tile_budget, 5), dtype=np.int64)
        values = np.empty(tile_budget, dtype=np.float64)
        preboards = np.empty((tile_budget, 16), dtype=np.int32)
        action_values = np.empty((tile_budget, 4), dtype=np.float64)
        action_legal = np.zeros((tile_budget, 4), dtype=np.int32)
        games, lengths = np.empty((tile_budget+1, 6), dtype=np.int64), np.zeros(3, dtype=np.int32)
        environment = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64)
        planning = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
        representation = np.zeros(len(self.representation_names), dtype=np.uint64)
        stream_work = np.zeros(7, dtype=np.uint64)
        leaf = self.leaf
        code = self.library.native_policy_advance_v313(self.handle, self.choose_callback, self.kind, leaf.model.patterns,
            leaf.radix, leaf.reward_weights, self.second_weights, leaf.model.table,
            leaf.model.scores, leaf.model.cells, float(model_p_four), float(environment_p_four),
            int(tile_budget), int(self.max_steps), raw, actions, values, preboards,
            action_values, action_legal, games, lengths,
            environment, planning, representation, stream_work)
        if code:
            raise ValueError('V313 full split H2 selected an illegal actual standard-world action')
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
        representation_work = _work(self.representation_names, representation)
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
                h2_value=float(values[i]), next_afterstate_tail=None, preboard=preboards[i].tolist(),
                action_values={name:float(action_values[i,j]) for j,name in enumerate(ACTIONS) if action_legal[i,j]})
                for i,a in enumerate(actions[:n_actions])],
            updates=[], bank_learning={'0':{}}, completed_games=completed, counts=work,
            representation_counts=representation_work, seconds=perf_counter()-started,
            cpu_seconds=process_time()-cpu_started)


def choose_direct(leaf, board, build_dir):
    """Ordered immediate reward plus this actual head's combined afterstate value."""
    kind, second, _, predict, names = _head(leaf)
    _frozen(leaf, second)
    setup = Counter()
    library = _backend(build_dir, setup)
    board = leaf.model._board(board, terminal_allowed=True)
    moved, legal = np.empty((4, 16), dtype=np.int32), np.zeros(4, dtype=np.int32)
    scores, tails, values = np.zeros(4, dtype=np.int64), np.zeros(4), np.zeros(4)
    planning, representation = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64), np.zeros(len(names), dtype=np.uint64)
    best = library.direct_choose_v313(predict, kind, board, leaf.model.patterns,
        leaf.radix, leaf.reward_weights, second, leaf.model.table, leaf.model.scores,
        leaf.model.cells, moved, scores, tails, values, legal, planning, representation)
    work = _work(PLANNING_COUNTS, planning)
    work['choose_calls'] = 1
    if best < 0:
        status, value = ('WON', 4.) if best == -2 else ('LOST', -4.)
        return dict(action=None, afterstate=board.tolist(), score=0, value=value,
            tail_value=value, action_values={}, status=status, counts=work,
            representation_counts=_work(names, representation))
    action_values = {action:dict(afterstate=moved[i].tolist(), score=int(scores[i]),
        tail_value=float(tails[i]), value=float(values[i])) for i, action in enumerate(ACTIONS) if legal[i]}
    return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
        status='ACTIVE', counts=work, representation_counts=_work(names, representation))


def evaluate_direct(leaf, model_p_four, environment_p_four, seeds, build_dir, max_steps=8192):
    """Natural games from a frozen head, with DIRECT afterstate action values."""
    started, cpu_started, compiler_started = perf_counter(), process_time(), _child_cpu()
    kind, second, _, predict, names = _head(leaf)
    _frozen(leaf, second)
    setup = Counter()
    library = _backend(build_dir, setup)
    seeds = np.ascontiguousarray(seeds, dtype=np.uint64)
    results, final = np.empty((len(seeds), 3), dtype=np.int64), np.empty((len(seeds), 16), dtype=np.int32)
    environment, planning = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64), np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
    representation = np.zeros(len(names), dtype=np.uint64)
    code = library.evaluate_direct_v313(seeds, len(seeds), predict, kind,
        leaf.model.patterns, leaf.radix, leaf.reward_weights, second, leaf.model.table,
        leaf.model.scores, leaf.model.cells, float(environment_p_four), int(max_steps),
        results, final, environment, planning, representation)
    if code:
        raise ValueError('V313 DIRECT selected an illegal actual standard-world action')
    rows = []
    for seed, row, board in zip(seeds, results, final):
        score, steps, status = map(int, row)
        rows.append(dict(seed=int(seed), score=score, steps=steps,
            status={1:'WON', -1:'LOST', 2:'CUTOFF'}[status], final_board=board.tolist(),
            utility=score/2048.+(4. if status==1 else -4. if status==-1 else 0.)))
    work = dict(environment=_work(ENVIRONMENT_COUNTS, environment), planning=_work(PLANNING_COUNTS, planning))
    work['planning']['choose_calls'] = sum(row['steps'] for row in rows)
    return dict(game_summaries=rows, counts=work, representation_counts=_work(names, representation),
        setup_counts=dict(setup), seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started,
        compiler_cpu_seconds=_child_cpu()-compiler_started, policy='DIRECT', model_p_four=float(model_p_four))
