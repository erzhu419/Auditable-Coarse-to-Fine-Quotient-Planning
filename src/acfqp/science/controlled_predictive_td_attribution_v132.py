"""Replay recorded V131 TD updates and attribute changed action preferences.

There is no simulator sampling or policy training here. A private copy of a
retained checkpoint follows the already recorded operations. Attribution uses
actual floating point parameter changes, with signed feature multiplicities.
"""
from collections import Counter
import ctypes
import math
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_ntuple_td_v120 import ACTIONS, ALPHA

SCHEMA = 'acfqp.td_attribution.v132'
CATEGORIES = ('LOSS', 'WIN_BOUNDARY', 'BOOTSTRAP')
COUNT_NAMES = ('replayed_transitions', 'greedy_action_checks', 'chosen_value_checks',
    'replayed_updates', 'raw_target_checks', 'td_error_checks', 'update_feature_occurrences',
    'unique_address_updates', 'attributed_address_updates', 'reverse_posting_visits',
    'exact_board_probe_update_visits', 'learned_swipe_calls', 'line_table_lookups',
    'choose_value_predictions', 'choose_table_lookups', 'recorded_spawns')
STAT_NAMES = ('error_sum', 'absolute_error_sum', 'absolute_actual_weight_change', 'max_absolute_error')
_LIBRARIES = {}


def _backend(build_dir, counts):
    directory = Path(build_dir).resolve()
    if not directory.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V132 build directory must be inside the research worktree')
    key = (str(directory), os.getpid())
    if key not in _LIBRARIES:
        directory.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = directory/f'td_attribution_v132_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True,
            text=True, env=dict(os.environ, TMPDIR=str(directory)))
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ptr, ci = ctypes.c_void_p, ctypes.c_int
        library.td_attribution_create_v132.argtypes = [dp, ip, ci, ip, lp, ip, dp, ci, ip, ip, ci]
        library.td_attribution_create_v132.restype = ptr
        library.td_attribution_destroy_v132.argtypes = [ptr]
        library.td_attribution_error_v132.argtypes = [ptr]
        library.td_attribution_error_v132.restype = ctypes.c_char_p
        library.td_attribution_segment_v132.argtypes = [ptr, ci, ip, ip, ci, ip, lp, ip, ip,
            dp, dp, dp, dp, dp, ci, dp, ip]
        library.td_attribution_segment_v132.restype = ci
        library.td_attribution_counts_v132.argtypes = [ptr, up, up, dp]
        library.td_attribution_summary_v132.argtypes = [ptr, dp, dp, up, up, up, dp]
        _LIBRARIES[key] = library
        counts['cpp_compilations'] += 1
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def signed_features(model, old_afterstate, new_afterstate):
    """The integer feature difference; exact shared occurrences cancel."""
    result = Counter()
    for board, sign in ((old_afterstate, -1), (new_afterstate, 1)):
        if max(board) < model.radix:
            for address in model.feature_indices(board):
                result[int(address)] += sign
    return {address: result[address] for address in sorted(result) if result[address]}


class TDAttributionReplay:
    def __init__(self, mid_query_td, probes, build_dir):
        started = perf_counter()
        self.mid = mid_query_td
        self.model = mid_query_td.model
        self.weights = self.model.weights.copy()
        self.probes = list(probes)
        self.setup_counts = Counter(private_parameters_copied=self.weights.size,
            private_weight_bytes_copied=self.weights.nbytes)
        self.counts = Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self._old = np.asarray([p['old_afterstate'] for p in probes], dtype=np.int32).reshape(-1, 16)
        self._new = np.asarray([p['new_afterstate'] for p in probes], dtype=np.int32).reshape(-1, 16)
        self.features = [signed_features(self.model, a, b) for a, b in zip(self._old, self._new)]
        self.initial_tails = [self._tails(a, b) for a, b in zip(self._old, self._new)]
        self.setup_counts.update(probe_feature_occurrences=int(2*32*sum(
            max(board) < self.model.radix for board in list(self._old)+list(self._new))),
            probe_nonzero_signed_addresses=sum(map(len, self.features)),
            probe_union_addresses=len({i for row in self.features for i in row}))
        raw_query = self.mid.source_query if self.mid.kind == 'PRIOR' else self.mid.target_query
        query = np.asarray([raw_query.get('reward_weight', 1.),
            self.mid.target_query.get('goal_bonus', 0.), self.mid.target_query.get('failure_penalty', 0.),
            self.mid.failure_shift, self.mid.success_shift, self.mid.offset, ALPHA], dtype=np.float64)
        shifted = self.mid.kind == 'PRIOR' and self.mid.source_query != self.mid.target_query
        self._handle = self.library.td_attribution_create_v132(self.weights, self.model.patterns,
            self.model.radix, self.model.table, self.model.scores, self.model.cells,
            query, int(shifted), self._old, self._new, len(probes))
        self.updates = self.mid.updates
        self.previous = None
        self.failed = self.finished = False
        self.setup_seconds = perf_counter()-started

    def _tails(self, old, new):
        values = []
        for board in (old, new):
            if max(board) >= self.model.radix:
                values.append(0.)
            else:
                values.append(float(self.model.library.ntuple_value_v120(
                    np.ascontiguousarray(board, dtype=np.int32), self.model.patterns,
                    self.model.radix, self.weights)))
                self.counts['probe_value_predictions'] += 1
                self.counts['probe_table_lookups'] += 32
        return values

    def _native_counts(self):
        counts, categories, stats = np.zeros(16, dtype=np.uint64), np.zeros(3, dtype=np.uint64), np.zeros((3, 4))
        self.library.td_attribution_counts_v132(self._handle, counts, categories, stats)
        return counts, categories, stats

    def segment(self, row):
        """Replay one retained segment; checkpoints are ordinary pending boundaries."""
        if self.failed or self.finished:
            raise RuntimeError('replay is no longer open')
        try:
            return self._segment(row)
        except Exception:
            self.failed = True
            raise

    def _segment(self, row):
        if row['updates_before'] != self.updates:
            raise ValueError('segment update continuity mismatch')
        previous = self.previous
        if previous is not None:
            if row['episode'] == previous['episode']:
                if (previous['status'] != 'ACTIVE' or row['start_step'] != previous['end_step']
                        or row['start_board'] != previous['end_board']
                        or row['pending_before'] != previous['pending_after']):
                    raise ValueError('segment pending or board continuity mismatch')
            elif (row['episode'] != previous['episode']+1 or previous['status'] == 'ACTIVE'
                    or row['start_step'] != 0 or row['pending_before'] is not None):
                raise ValueError('episode continuity mismatch')
        if 'initial_spawns' in row:
            initial = [0]*16
            for spawn in row['initial_spawns']:
                if initial[spawn['cell']] or spawn['rank'] not in (1, 2):
                    raise ValueError('initial spawn mismatch')
                initial[spawn['cell']] = spawn['rank']
            if initial != row['start_board'] or len(row['initial_spawns']) != 2:
                raise ValueError('initial board mismatch')
            self.counts['recorded_initial_spawns'] += 2
        n = len(row['actions'])
        if row['end_step']-row['start_step'] != n:
            raise ValueError('segment transition count mismatch')
        columns = ('scores', 'spawned_cells', 'spawned_ranks', 'chosen_values', 'chosen_raw_values',
            'td_targets', 'raw_td_targets', 'td_errors')
        if any(len(row[key]) != n for key in columns):
            raise ValueError('retained transition columns differ in length')
        board = np.asarray(row['start_board'], dtype=np.int32)
        pending = np.asarray(row['pending_before'] or [0]*16, dtype=np.int32)
        actions = np.asarray([ACTIONS.index(a) for a in row['actions']], dtype=np.int32)
        arrays = [np.asarray(row[key], dtype=(np.int64 if key == 'scores' else
            np.int32 if key in ('spawned_cells', 'spawned_ranks') else np.float64)) for key in columns]
        terminal = row['terminal_update']
        terminal_values = np.asarray([terminal[key] for key in ('target', 'raw_target', 'error')]
            if terminal else [0., 0., 0.], dtype=np.float64)
        before, categories_before, _ = self._native_counts()
        out_pending = np.zeros(16, dtype=np.int32)
        has_pending = self.library.td_attribution_segment_v132(self._handle, n, board, pending,
            int(row['pending_before'] is not None), actions, *arrays, int(terminal is not None),
            terminal_values, out_pending)
        if has_pending < 0:
            raise ValueError(self.library.td_attribution_error_v132(self._handle).decode())
        if terminal is not None and (row['status'] != 'LOST' or terminal['afterstate'] != pending.tolist()):
            raise ValueError('terminal update afterstate or status mismatch')
        status_work = Counter()
        actual_status = _status(tuple(board.tolist()), status_work)
        self.counts.update(status_work)
        expected_status = 'ACTIVE' if row['status'] == 'CUTOFF' else row['status']
        if actual_status != expected_status:
            raise ValueError('retained terminal status mismatch')
        if row['status'] == 'CUTOFF':
            if row['end_step'] != 2000 or row['censored_last_update'] != bool(has_pending):
                raise ValueError('cutoff pending disposition mismatch')
            has_pending = 0
        actual_pending = out_pending.tolist() if has_pending else None
        if board.tolist() != row['end_board'] or actual_pending != row['pending_after']:
            raise ValueError('segment end board or pending mismatch')
        after, categories_after, _ = self._native_counts()
        self.updates += int(after[3]-before[3])
        if self.updates != row['updates_after']:
            raise ValueError('segment final update count mismatch')
        self.previous = {key: row[key] for key in ('episode', 'end_step', 'end_board', 'pending_after', 'status')}
        self.counts['retained_segments'] += 1
        return dict(transitions=n, updates=int(after[3]-before[3]),
            category_counts={key: int(value) for key, value in zip(CATEGORIES, categories_after-categories_before)})

    def finish(self, final_query_td):
        if self.failed or self.finished:
            raise RuntimeError('replay is no longer open')
        parameters_equal = np.array_equal(self.weights, final_query_td.weights)
        updates_equal = self.updates == final_query_td.updates
        self.counts['final_compared_parameters'] += self.weights.size
        if not parameters_equal or not updates_equal:
            self.failed = True
            raise ValueError('final checkpoint weights or update count mismatch')
        n = len(self.probes)
        contribution, exact = np.zeros((n, 3)), np.zeros((n, 3))
        overlap = np.zeros((n, 3), dtype=np.uint64)
        counts, categories, stats = np.zeros(16, dtype=np.uint64), np.zeros(3, dtype=np.uint64), np.zeros((3, 4))
        self.library.td_attribution_summary_v132(self._handle, contribution, exact, overlap, counts, categories, stats)
        flat, initial = self.weights.reshape(-1), self.mid.weights.reshape(-1)
        probes = []
        for index, probe in enumerate(self.probes):
            tails = self._tails(self._old[index], self._new[index])
            previous = self.initial_tails[index]
            observed = (tails[1]-tails[0])-(previous[1]-previous[0])
            linear = math.fsum(coefficient*(float(flat[address])-float(initial[address]))
                for address, coefficient in self.features[index].items())
            attributed = math.fsum(contribution[index])
            probes.append(dict(probe_id=probe['probe_id'], categories=dict(zip(CATEGORIES, contribution[index].tolist())),
                exact_board_categories=dict(zip(CATEGORIES, exact[index].tolist())),
                shared_feature_categories=dict(zip(CATEGORIES, (contribution[index]-exact[index]).tolist())),
                signed_overlap_update_counts=dict(zip(CATEGORIES, map(int, overlap[index]))),
                observed_gap_change=observed, observed_gap_arithmetic='(new_tail_final-old_tail_final)-(new_tail_mid-old_tail_mid), original 32-lookup order',
                linear_gap_change=linear, attributed_gap_change=attributed,
                rounding_residual=observed-attributed, linear_rounding_residual=linear-attributed,
                initial_tails=previous, final_tails=tails,
                nonzero_signed_addresses=len(self.features[index])))
        self.finished = True
        self.weights.flags.writeable = False
        result = dict(schema=SCHEMA, checks=dict(exact_final_weights=True, exact_final_updates=True,
            exact_recorded_predictions=True, exact_recorded_targets_errors=True,
            exact_retained_transitions_pending=True),
            counts=dict(Counter(dict(zip(COUNT_NAMES, map(int, counts))))+self.counts),
            category_counts=dict(zip(CATEGORIES, map(int, categories))),
            category_stats={category: dict(zip(STAT_NAMES, stats[index].tolist()))
                for index, category in enumerate(CATEGORIES)}, probes=probes,
            setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds,
            initial_updates=self.mid.updates, final_updates=self.updates,
            newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0)
        self.completed_counts = result['counts']
        self.close()
        return result

    def close(self):
        if getattr(self, '_handle', None):
            self.library.td_attribution_destroy_v132(self._handle)
            self._handle = None

    def __del__(self):
        self.close()
