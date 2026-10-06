"""Immutable-source residual critics with factual or expected-control targets."""
from collections import Counter
import ctypes
import math
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .controlled_predictive_online_query_td_v131 import QueryTD

TARGET_KINDS = ('MC', 'EXPECTED_CONTROL')
COUNT_NAMES = (
    'value_predictions', 'source_table_lookups', 'residual_table_lookups',
    'source_value_additions', 'residual_multiplications', 'residual_value_additions',
    'query_shift_additions', 'analytic_winning_values', 'context_basis_calls',
    'context_basis_squared_terms', 'context_basis_square_roots', 'context_basis_divisions',
    'model_swipe_calls', 'model_line_table_lookups', 'model_legal_actions',
    'model_winning_actions', 'model_terminal_loss_states', 'model_terminal_goal_states',
    'expected_spawn_outcomes', 'spawn_probability_products', 'spawn_probability_sums',
    'root_swipe_calls', 'second_ply_swipe_calls', 'expected_control_targets',
    'suffix_target_assignments', 'suffix_reward_additions', 'skipped_winning_afterstates',
    'feature_extractions', 'feature_occurrences', 'feature_digit_reads',
    'feature_address_multiply_adds', 'game_sort_items', 'game_sort_comparisons',
    'address_occurrence_count_visits', 'game_unique_addresses',
    'weighted_residual_accumulations', 'normalization_divisions',
    'parameter_update_multiplications', 'parameter_write_events', 'game_parameter_commits',
    'td_updates', 'table_update_occurrences', 'residual_error_subtractions',
    'native_buffer_bytes_peak', 'address_denominator_search_comparisons',
    'context_basis_additions')
PREDICTION_NAMES = COUNT_NAMES[:12]
TARGET_NAMES = COUNT_NAMES[12:27]
CONSOLIDATION_NAMES = COUNT_NAMES[27:40] + COUNT_NAMES[42:]
_LIBRARIES = {}


def _backend(runtime, setup):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V294 builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = runtime / f'native_conditional_bellman_v294_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(runtime)))
        setup.update(cpp_compilations=1, cpp_translation_units_compiled=1)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.predict_conditional_v294.argtypes = [ip, ci, dp, ip, ci, dp, dp, ci,
            cd, cd, cd, dp, up]
        library.fit_conditional_v294.argtypes = [ip, ci, dp, dp, ci, ip, ci, dp, dp, ci,
            ip, lp, ip, cd, cd, cd, cd, cd, ci, up, lp, dp]
        library.score_actions_conditional_v294.argtypes = [ip, ci, dp, ip, ci, dp, dp, ci,
            ip, lp, ip, cd, cd, cd, cd, ip, ip, lp, dp, dp, ip, up]
        for name in ('predict_conditional_v294', 'fit_conditional_v294',
                     'score_actions_conditional_v294'):
            getattr(library, name).restype = None
        _LIBRARIES[key] = library
    else:
        setup['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _work(native):
    return {key: int(value) for key, value in zip(COUNT_NAMES, native) if value}


def _subset(work, names):
    return {key: work[key] for key in names if key in work}


def _inputs(boards, probabilities):
    boards = np.ascontiguousarray(boards, dtype=np.int32)
    probabilities = np.ascontiguousarray(probabilities, dtype=np.float64)
    if boards.ndim != 2 or boards.shape[1] != 16 or probabilities.shape != (len(boards),):
        raise ValueError('V294 requires N by 16 boards and one observed p per board')
    if np.any(boards < 0) or np.any(~np.isfinite(probabilities)) or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError('V294 boards and observed spawn probabilities are invalid')
    return boards, probabilities


class ResidualHead:
    """Zero residuals over the shared immutable target-query SOURCE anchor."""
    def __init__(self, template, conditioned, runtime):
        if template.weights.flags.writeable:
            raise ValueError('V294 source anchor must be frozen')
        started = perf_counter()
        self.template, self.conditioned = template, bool(conditioned)
        self.banks = 2 if self.conditioned else 1
        self.residuals = np.zeros((self.banks, *template.weights.shape), dtype=np.float64)
        self.updates, self.counts, self.setup_counts = 0, Counter(), Counter()
        self.library = _backend(runtime, self.setup_counts)
        self.setup_counts.update(allocated_residual_parameters=self.residuals.size,
            allocated_residual_bytes=self.residuals.nbytes,
            zero_initialized_residual_parameters=self.residuals.size,
            source_parameters_shared=template.weights.size)
        self.setup_seconds = perf_counter()-started


def _parameters(head):
    leaf = head.template
    return [leaf.model.patterns, leaf.radix, leaf.weights, head.residuals, head.banks,
        leaf.model.table, leaf.model.scores, leaf.model.cells,
        float(leaf.target_query.get('goal_bonus', 0.)),
        float(leaf.target_query.get('failure_penalty', 0.)),
        leaf.failure_shift, leaf.success_shift]


def predict(head, boards, p_array, runtime):
    started, cpu = perf_counter(), process_time()
    setup = Counter(); library = _backend(runtime, setup)
    boards, probabilities = _inputs(boards, p_array)
    output = np.empty(len(boards), dtype=np.float64)
    native = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
    params = _parameters(head)
    library.predict_conditional_v294(boards, len(boards), probabilities, *params[:5],
        params[8], *params[10:], output, native)
    work = _work(native); head.counts.update(work)
    return dict(predictions=output, counts=work, setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def fit_episode(head, game, target_kind, runtime, alpha=.0025):
    if target_kind not in TARGET_KINDS or not head.residuals.flags.writeable:
        raise ValueError('V294 requires a frozen target definition and writable residuals')
    started, cpu = perf_counter(), process_time()
    setup = Counter(); library = _backend(runtime, setup)
    boards, probabilities = _inputs(game['afterstates'], game['model_p_four'])
    rewards = np.ascontiguousarray(game['rewards'], dtype=np.float64)
    terminal = int(game['terminal_code'])
    if rewards.shape != (len(boards),) or terminal not in (-1, 1):
        raise ValueError('V294 fits only a complete natural game with aligned rewards')
    native = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
    indices, examples = np.full(2, -1, dtype=np.int64), np.zeros((2, 4), dtype=np.float64)
    library.fit_conditional_v294(boards, len(boards), rewards, probabilities, terminal,
        *_parameters(head), float(alpha), int(target_kind == 'EXPECTED_CONTROL'),
        native, indices, examples)
    work = _work(native); trained = work.get('td_updates', 0)
    head.updates += trained
    for key, value in work.items():
        if key.endswith('_peak'):
            head.counts[key] = max(head.counts[key], value)
        else:
            head.counts[key] += value
    def sample(i):
        if indices[i] < 0:
            return None
        target, before, error, p = map(float, examples[i])
        return dict(step=int(indices[i]), target=target, prediction_before_update=before,
                    error=error, model_p_four=p)
    learning = dict(td_updates=trained, table_updates=work.get('parameter_write_events', 0),
        table_update_occurrences=work.get('table_update_occurrences', 0))
    return dict(target_kind=target_kind, conditioned=head.conditioned, alpha=float(alpha),
        fitted_games=1, fitted_steps=len(boards), trained_afterstates=trained,
        learning_counts=learning, target_counts=_subset(work, TARGET_NAMES),
        consolidation_counts=_subset(work, CONSOLIDATION_NAMES),
        prediction_counts=_subset(work, PREDICTION_NAMES), counts=work,
        first_sample=sample(0), last_sample=sample(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def materialize(head, p, runtime):
    """One immutable effective raw table for the unchanged V286 H2 evaluator."""
    started, cpu = perf_counter(), process_time()
    leaf = QueryTD(head.template.parent, 'PRIOR', runtime)
    left = 1.-float(p)
    if head.conditioned:
        norm = math.sqrt(left*left+float(p)*float(p))
        coefficients = (left/norm, float(p)/norm)
    else:
        coefficients = (1.,)
    # Each multiplication/addition matches the native composite prediction.
    leaf.weights[:] = head.template.weights
    scratch = np.empty_like(leaf.weights)
    for coefficient, residual in zip(coefficients, head.residuals):
        np.multiply(residual, coefficient, out=scratch)
        np.add(leaf.weights, scratch, out=leaf.weights)
    leaf.freeze()
    count = leaf.weights.size
    counts = dict(source_anchor_parameters_copied=count,
        source_anchor_bytes_copied=leaf.weights.nbytes,
        effective_table_parameters_scanned=count*head.banks,
        effective_table_multiplications=count*head.banks,
        effective_table_additions=count*head.banks,
        effective_table_parameter_writes=count*head.banks,
        allocated_blending_scratch_bytes=scratch.nbytes)
    return leaf, dict(model_p_four=float(p), conditioned=head.conditioned,
        origin_residual_updates=head.updates, setup_counts=dict(leaf.setup_counts),
        blending_counts=counts, private_weight_bytes=leaf.weights.nbytes,
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def score_actions(head, boards, p_array, runtime):
    """The same H2 scores as a fixed-p materialized head, without a dense copy."""
    started, cpu = perf_counter(), process_time()
    setup = Counter(); library = _backend(runtime, setup)
    boards, probabilities = _inputs(boards, p_array)
    n = len(boards)
    best = np.empty(n, dtype=np.int32)
    moved = np.zeros((n, 4, 16), dtype=np.int32)
    scores, tails, values = np.zeros((n, 4), dtype=np.int64), np.zeros((n, 4)), np.zeros((n, 4))
    legal, native = np.zeros((n, 4), dtype=np.int32), np.zeros(len(COUNT_NAMES), dtype=np.uint64)
    library.score_actions_conditional_v294(boards, n, probabilities, *_parameters(head),
        best, moved, scores, tails, values, legal, native)
    goal, failure = (float(head.template.target_query.get(k, 0.)) for k in ('goal_bonus', 'failure_penalty'))
    choices = []
    for row, action in enumerate(best):
        action_values = {name: dict(afterstate=moved[row, i].tolist(), score=int(scores[row, i]),
            tail_value=float(tails[row, i]), value=float(values[row, i]))
            for i, name in enumerate(ACTIONS) if legal[row, i]}
        if action < 0:
            v = goal if action == -2 else -failure
            choices.append(dict(action=None, afterstate=boards[row].tolist(), score=0,
                value=v, tail_value=v, action_values={}, status='WON' if action == -2 else 'LOST'))
        else:
            name = ACTIONS[int(action)]
            choices.append(dict(action=name, **action_values[name], action_values=action_values, status='ACTIVE'))
    work = _work(native); head.counts.update(work)
    return dict(choices=choices, counts=work, setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
