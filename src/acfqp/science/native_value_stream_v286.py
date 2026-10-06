"""Causal H2-policy SARSA over an uninterrupted actual raw-spawn stream."""
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
    'ground_status_internal_swipe_calls', 'raw_tile_productions', 'initial_spawns', 'post_action_spawns')
LEARNING_COUNTS = ('td_updates', 'value_predictions', 'table_lookups',
                   'table_updates', 'table_update_occurrences')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V286 builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'native_value_stream_v286_{os.getpid()}.so'
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
        ci, cd, cp, cl = ctypes.c_int, ctypes.c_double, ctypes.c_void_p, ctypes.c_int64
        library.native_stream_create_v286.argtypes = [ctypes.c_uint64]
        library.native_stream_create_v286.restype = cp
        library.native_stream_delete_v286.argtypes = [cp]
        library.native_stream_delete_v286.restype = None
        library.native_stream_state_v286.argtypes = [cp, ip, ip, lp]
        library.native_stream_state_v286.restype = None
        library.native_stream_advance_v286.argtypes = [cp, ip, ip, ci, ci, dp, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, ci, cl, ci, ci, cd, cd, ci, ci, ci, ci, ci,
            lp, lp, dp, lp, dp, lp, ip, up, up, up, up, up]
        library.native_stream_advance_v286.restype = ci
        library.native_stream_evaluate_v286.argtypes = [up, ci, ip, ip, ci, ci, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, ci, cd, cd, ci, ci, lp, ip, up, up]
        library.native_stream_evaluate_v286.restype = ci
        library.native_common_draws_v285.argtypes = [ctypes.c_uint64, ci, dp]
        library.native_common_draws_v285.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _work(names, values):
    return {name: int(value) for name, value in zip(names, values) if value}


def _parameters(leaf):
    native = leaf.model
    raw = leaf.source_query if leaf.kind == 'PRIOR' else leaf.target_query
    return [native.patterns, getattr(native, 'extra_cells', np.zeros((4, 8), dtype=np.int32)),
        leaf.radix, getattr(native, 'mode', -1), leaf.weights, native.table, native.scores,
        native.cells, float(raw.get('goal_bonus', 0.)), float(leaf.target_query.get('goal_bonus', 0.)),
        float(leaf.target_query.get('failure_penalty', 0.)), leaf.failure_shift, leaf.success_shift,
        int(leaf.kind == 'PRIOR' and not _same_query(leaf.source_query, leaf.target_query))]


def _charge_bank(leaf, work):
    leaf.model.counts.update(work)
    leaf.model.updates += work.get('td_updates', 0)
    leaf.counts.update({f'inner_{name}': value for name, value in work.items()})
    leaf.counts['td_updates'] += work.get('td_updates', 0)


class NativeValueStream:
    def __init__(self, template_leaf, seed_base, build_dir, max_steps=8192):
        started = perf_counter()
        self.template, self.max_steps, self.setup_counts = template_leaf, max_steps, Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.handle = self.library.native_stream_create_v286(int(seed_base))
        self.counts = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.setup_seconds = perf_counter()-started

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

    def advance(self, active_leaf, active_bank_id, pending_leaf, model_p_four,
                environment_p_four, tile_budget, max_postaction=64, depth=2, stop_on_game_end=False):
        started, cpu_started = perf_counter(), process_time()
        before = self.state()
        if before['pending_bank_id'] not in (None, active_bank_id) and pending_leaf is None:
            raise ValueError('the saved previous-bank leaf is required for its pending TD update')
        previous = pending_leaf if pending_leaf is not None else active_leaf
        p = _parameters(active_leaf)
        cap = min(tile_budget, max_postaction)
        raw = np.empty((tile_budget, 4), dtype=np.int64)
        actions, predictions = np.empty((cap, 5), dtype=np.int64), np.empty((cap, 2))
        events, event_values = np.empty((2*cap, 5), dtype=np.int64), np.empty((2*cap, 3))
        games, lengths = np.empty((cap+1, 6), dtype=np.int64), np.zeros(4, dtype=np.int32)
        environment, planning = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64), np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
        active, old, stream_work = np.zeros(5, dtype=np.uint64), np.zeros(5, dtype=np.uint64), np.zeros(7, dtype=np.uint64)
        code = self.library.native_stream_advance_v286(self.handle, *p[:4], p[4], previous.weights,
            *p[5:13], p[13], int(active_bank_id), int(active_leaf.weights.flags.writeable),
            int(previous.weights.flags.writeable), model_p_four, environment_p_four,
            tile_budget, max_postaction, self.max_steps, depth, int(stop_on_game_end), raw, actions, predictions, events,
            event_values, games, lengths, environment, planning, active, old, stream_work)
        if code:
            raise ValueError('H2 selected an illegal actual standard-world action')
        active_work, previous_work = _work(LEARNING_COUNTS, active), _work(LEARNING_COUNTS, old)
        _charge_bank(active_leaf, active_work)
        if previous_work:
            _charge_bank(previous, previous_work)
        bank_work = {str(active_bank_id): active_work}
        if previous_work:
            bank_work[str(before['pending_bank_id'])] = previous_work
        work = dict(environment=_work(ENVIRONMENT_COUNTS, environment),
            planning=_work(PLANNING_COUNTS, planning), learning=dict(Counter(active_work)+Counter(previous_work)))
        for name, index in (('episodes_started',1), ('episodes_completed',2), ('won_games',3), ('lost_games',4), ('cutoff_games',5)):
            if stream_work[index]:
                work['environment'][name] = int(stream_work[index])
        if stream_work[0]:
            work['planning']['choose_calls'] = int(stream_work[0])
        if stream_work[6]:
            work['learning']['censored_pending_updates'] = int(stream_work[6])
        for kind, values in work.items():
            self.counts[kind].update(values)
        n_raw, n_actions, n_events, n_games = map(int, lengths)
        updates = [dict(raw_tiles_before_update=int(e[0]), episode=int(e[1]), step=int(e[2]),
            bank_id=int(e[3]), kind='PREVIOUS_PENDING' if e[4]==0 else 'TERMINAL_LOSS',
            target=float(v[0]), raw_target=float(v[1]), error=float(v[2]))
            for e,v in zip(events[:n_events],event_values[:n_events])]
        completed = [dict(episode=int(g[0]), stream_seed=before['stream_seed'], start_raw=int(g[1]), end_raw=int(g[2]),
            steps=int(g[3]), score=int(g[4]), status={1:'WON',-1:'LOST',2:'CUTOFF'}[int(g[5])]) for g in games[:n_games]]
        fitted_actions = {(u['episode'],u['step']) for u in updates if u['kind']=='PREVIOUS_PENDING'}
        return dict(start=before, end=self.state(),
            raw_spawns=[dict(episode=int(r[0]), kind='INITIAL' if r[1]==0 else 'POST_ACTION',
                cell=int(r[2]), rank=int(r[3])) for r in raw[:n_raw]],
            actions=[ACTIONS[int(a[2])] for a in actions[:n_actions]],
            scores=[int(a[3]) for a in actions[:n_actions]],
            action_records=[dict(episode=int(a[0]), step=int(a[1]), raw_index=int(a[4]),
                h2_value=float(v[0]), next_afterstate_tail=float(v[1]) if (int(a[0]),int(a[1])) in fitted_actions else None)
                for a,v in zip(actions[:n_actions],predictions[:n_actions])],
            updates=updates, bank_learning=bank_work, completed_games=completed, counts=work,
            seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)

    def evaluate_games(self, leaf, model_p_four, environment_p_four, seeds, depth=2, max_steps=8192):
        """Read a synchronous mutable-weight snapshot without changing training."""
        started, cpu_started = perf_counter(), process_time()
        seeds = np.asarray(seeds, dtype=np.uint64)
        results, final = np.empty((len(seeds), 3), dtype=np.int64), np.empty((len(seeds), 16), dtype=np.int32)
        environment, planning = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64), np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
        code = self.library.native_stream_evaluate_v286(seeds, len(seeds), *_parameters(leaf),
            model_p_four, environment_p_four, depth, max_steps, results, final, environment, planning)
        if code:
            raise ValueError('snapshot policy selected an illegal actual standard-world action')
        goal, failure = (float(leaf.target_query.get(key, 0.)) for key in ('goal_bonus','failure_penalty'))
        rows = []
        for seed, row, board in zip(seeds,results,final):
            score, steps, status = map(int,row)
            rows.append(dict(seed=int(seed), score=score, steps=steps,
                status={1:'WON',-1:'LOST',2:'CUTOFF'}[status], final_board=board.tolist(),
                utility=score/2048.+(goal if status==1 else -failure if status==-1 else 0.)))
        work = dict(environment=_work(ENVIRONMENT_COUNTS, environment), planning=_work(PLANNING_COUNTS, planning))
        work['planning']['choose_calls'] = sum(r['steps'] for r in rows)
        return dict(game_summaries=rows, counts=work, seconds=perf_counter()-started,
                    cpu_seconds=process_time()-cpu_started)
