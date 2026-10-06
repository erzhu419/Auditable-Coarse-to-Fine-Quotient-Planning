"""Active two-table linear reward/WIN regression with the fixed H2 planner."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as PLANNING_COUNTS
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .native_retained_critic_v287 import _arrays, _work
from .native_value_stream_v286 import ENVIRONMENT_COUNTS

QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
METHOD = 'LINEAR_WIN2'
LEARNING_COUNTS = ('td_updates', 'value_predictions', 'table_lookups', 'table_updates',
    'table_update_occurrences', 'reward_predictions', 'win_predictions',
    'reward_table_lookups', 'win_table_lookups', 'reward_table_updates', 'win_parameter_updates')
TARGET_COUNTS = ('terminal_game_labels', 'win_label_assignments',
    'reward_suffix_target_assignments', 'reward_suffix_additions', 'goal_checks',
    'skipped_winning_afterstates', 'utility_suffix_target_assignments', 'utility_suffix_reward_additions')
NORMALIZATION_COUNTS = ('games_processed', 'feature_extractions', 'feature_occurrences',
    'feature_digit_reads', 'feature_address_multiply_adds', 'sort_calls', 'sort_items',
    'sort_comparisons', 'denominator_occurrence_visits', 'game_unique_addresses',
    'reward_gradient_products', 'reward_gradient_accumulations',
    'win_gradient_products', 'win_gradient_accumulations', 'normalization_divisions',
    'parameter_update_multiplications', 'game_parameter_commits', 'reward_game_commits',
    'win_game_commits', 'reward_parameter_writes', 'win_parameter_writes',
    'address_denominator_searches', 'address_denominator_search_comparisons', 'native_buffer_bytes_peak')
REPRESENTATION_COUNTS = ('linear_win_table_lookups', 'combined_value_additions', 'combined_value_multiplications')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V311 native builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = build_dir/f'native_linear_win_v311_{os.getpid()}.so'
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
        ci, cd = ctypes.c_int, ctypes.c_double
        library.linear_predict_v311.argtypes = [ip, ip, ci, dp, dp, dp, up]
        library.linear_predict_v311.restype = None
        library.linear_choose_v311.argtypes = [ip, ip, ci, dp, dp, ip, lp, ip,
            cd, ip, lp, dp, dp, ip, up, up]
        library.linear_choose_v311.restype = ci
        library.fit_linear_v311.argtypes = [ip, dp, lp, ip, ci, ip, ci, dp, dp,
            cd, up, up, up, up, lp, dp]
        library.fit_linear_v311.restype = None
        library.score_linear_v311.argtypes = [ip, dp, lp, ip, ci, ci, ip, ci, dp, dp,
            dp, dp, up, up, up]
        library.score_linear_v311.restype = None
        library.evaluate_linear_v311.argtypes = [up, ci, ip, ci, dp, dp, ip, lp,
            ip, cd, cd, ci, lp, ip, up, up, up]
        library.evaluate_linear_v311.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _parameters(leaf):
    return [leaf.model.patterns, leaf.radix, leaf.reward_weights, leaf.win_weights]


def _representation_array():
    return np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)


class LinearWinLeaf:
    def __init__(self, template, build_dir):
        if template.source_query!=QUERY or template.target_query!=QUERY or template.offset!=0.:
            raise ValueError('V311 uses the fixed risk_goal query and no query offset')
        started, cpu_started = perf_counter(), process_time()
        self.kind, self.model = METHOD, template.model
        self.rule, self.radix = template.rule, template.radix
        self.source_query, self.target_query = dict(QUERY), dict(QUERY)
        self.source_updates = template.parent.updates
        self.failure_shift = self.success_shift = self.offset = 0.
        self.reward_weights = np.array(template.parent.source.weights, copy=True, order='C')
        self.win_weights = np.full_like(self.reward_weights, 1./64.)
        self.updates, self.counts = 0, Counter()
        self.setup_counts = Counter(source_parameters_copied=self.reward_weights.size,
            source_weight_bytes_copied=self.reward_weights.nbytes,
            allocated_weight_parameters=self.reward_weights.size+self.win_weights.size,
            allocated_weight_bytes=self.reward_weights.nbytes+self.win_weights.nbytes,
            initialized_half_win_parameters=self.win_weights.size)
        self.library = _backend(build_dir, self.setup_counts)
        self.setup_seconds = self.seconds = perf_counter()-started
        self.setup_cpu_seconds = self.cpu_seconds = process_time()-cpu_started

    @property
    def weights(self):
        return self.reward_weights

    def freeze(self):
        self.reward_weights.flags.writeable = False
        self.win_weights.flags.writeable = False

    def choose(self, board, model_p_four=.5):
        board = self.model._board(board, terminal_allowed=True)
        moved, scores = np.empty((4, 16), dtype=np.int32), np.zeros(4, dtype=np.int64)
        tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
        planning, representation = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64), _representation_array()
        best = self.library.linear_choose_v311(board, *_parameters(self), self.model.table,
            self.model.scores, self.model.cells, float(model_p_four), moved, scores,
            tails, values, legal, planning, representation)
        work = _work(PLANNING_COUNTS, planning); work['choose_calls'] = 1
        extra = _work(REPRESENTATION_COUNTS, representation)
        if best<0:
            status, value = ('WON', 4.) if best==-2 else ('LOST', -4.)
            return dict(action=None, afterstate=board.tolist(), score=0, value=value,
                tail_value=value, action_values={}, status=status, counts=work,
                representation_counts=extra)
        action_values = {action:dict(afterstate=moved[i].tolist(), score=int(scores[i]),
            tail_value=float(tails[i]), value=float(values[i])) for i, action in enumerate(ACTIONS) if legal[i]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=work, representation_counts=extra)


def predict_components(leaf, board):
    board = leaf.model._board(board)
    values, representation = np.empty(3), _representation_array()
    leaf.library.linear_predict_v311(board, *_parameters(leaf), values, representation)
    reward, win, utility = map(float, values)
    return dict(reward_prediction=reward, win_prediction=win, combined_prediction=utility,
        representation_counts=_work(REPRESENTATION_COUNTS, representation))


def fit_linear(leaf, dataset, build_dir, alpha=.0025):
    if not leaf.reward_weights.flags.writeable or not leaf.win_weights.flags.writeable:
        raise ValueError('both V311 heads must be writable while fitting')
    started, cpu_started = perf_counter(), process_time()
    setup = Counter(); library = _backend(build_dir, setup); arrays = _arrays(dataset)
    n_games, fit_end = int(dataset['fit_game_count']), int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0)!=fit_end:
        raise ValueError('V311 fits the frozen prefix of complete games')
    learning, targets = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64), np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    normalization, representation = np.zeros(len(NORMALIZATION_COUNTS), dtype=np.uint64), _representation_array()
    indices, values = np.empty((2, 2), dtype=np.int64), np.empty((2, 7))
    library.fit_linear_v311(*arrays, n_games, *_parameters(leaf), float(alpha),
        learning, targets, normalization, representation, indices, values)
    work = _work(LEARNING_COUNTS, learning)
    leaf.updates += work.get('td_updates', 0); leaf.counts.update(work)
    def example(index):
        if not work.get('td_updates', 0):
            return None
        game, step = map(int, indices[index])
        reward_target, win_target, reward, win, utility, reward_error, win_error = map(float, values[index])
        return dict(episode=game, step=step, reward_target=reward_target, win_target=win_target,
            reward_prediction=reward, win_prediction=win, combined_prediction=utility,
            reward_error=reward_error, win_error=win_error)
    return dict(method=METHOD, alpha=float(alpha), fitted_games=n_games, fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates', 0), learning_counts=work,
        reward_trained_afterstates=work.get('td_updates', 0), win_trained_afterstates=work.get('td_updates', 0),
        frozen_game_start_targets=True, target_counts=_work(TARGET_COUNTS, targets),
        normalization_counts=_work(NORMALIZATION_COUNTS, normalization),
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        first_sample=example(0), last_sample=example(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)


def score_linear(leaf, dataset, build_dir):
    started, cpu_started = perf_counter(), process_time()
    setup = Counter(); library = _backend(build_dir, setup); arrays = _arrays(dataset)
    first, n_games = int(dataset['fit_game_count']), len(arrays[2])
    output, components = np.empty((n_games-first, 6)), np.empty((n_games-first, 8))
    predictions, targets = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64), np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    representation = _representation_array()
    library.score_linear_v311(*arrays, first, n_games, *_parameters(leaf), output, components,
        predictions, targets, representation)
    rows, component_rows = [], []
    names = ('reward_bias', 'reward_mse', 'reward_mae', 'win_mse', 'win_bias', 'mean_win_prediction', 'win_label')
    for index, (row, component) in enumerate(zip(output, components), first):
        count, bias, mse, mae, prediction, target = map(float, row)
        identity = dict(episode=index, start=int(arrays[2][index-1]) if index else 0,
            end=int(arrays[2][index]), count=int(count))
        rows.append(dict(identity, bias=bias, mse=mse, mae=mae,
            mean_prediction=prediction, mean_factual_future_utility=target))
        component_rows.append(dict(identity, **{name:float(value) for name, value in zip(names, component[:7])}))
    return dict(game_metrics=rows, metrics={key:sum(row[key] for row in rows)/len(rows)
        for key in ('bias', 'mse', 'mae')}, component_game_metrics=component_rows,
        component_metrics={key:sum(row[key] for row in component_rows)/len(component_rows) for key in names[:-1]},
        prediction_counts=_work(LEARNING_COUNTS, predictions), target_counts=_work(TARGET_COUNTS, targets),
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        setup_counts=dict(setup), seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)


def evaluate_linear(leaf, model_p_four, environment_p_four, seeds, build_dir, max_steps=8192):
    started, cpu_started = perf_counter(), process_time()
    setup = Counter(); library = _backend(build_dir, setup)
    seeds = np.ascontiguousarray(seeds, dtype=np.uint64)
    results, final = np.empty((len(seeds), 3), dtype=np.int64), np.empty((len(seeds), 16), dtype=np.int32)
    environment, planning = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64), np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
    representation = _representation_array()
    code = library.evaluate_linear_v311(seeds, len(seeds), *_parameters(leaf), leaf.model.table,
        leaf.model.scores, leaf.model.cells, float(model_p_four), float(environment_p_four),
        int(max_steps), results, final, environment, planning, representation)
    if code:
        raise ValueError('V311 H2 selected an illegal standard-world action')
    rows = []
    for seed, row, board in zip(seeds, results, final):
        score, steps, status = map(int, row)
        rows.append(dict(seed=int(seed), score=score, steps=steps,
            status={1:'WON', -1:'LOST', 2:'CUTOFF'}[status], final_board=board.tolist(),
            utility=score/2048.+(4. if status==1 else -4. if status==-1 else 0.)))
    work = dict(environment=_work(ENVIRONMENT_COUNTS, environment), planning=_work(PLANNING_COUNTS, planning))
    work['planning']['choose_calls'] = sum(row['steps'] for row in rows)
    return dict(game_summaries=rows, counts=work, representation_counts=_work(REPRESENTATION_COUNTS, representation),
        setup_counts=dict(setup), seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
